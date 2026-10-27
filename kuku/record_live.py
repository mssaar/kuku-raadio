"""Kuku otse-eetri salvestamise CLI tööriist."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from kuku.api import Episode
from kuku.live import get_ad_intervals, remove_ads
from kuku.releases import GitHubClient
from kuku.sync import DATA_DIR, _entry, _read, _write, tag_for

STREAM_URL = "https://router.euddn.net/8103046e16b71d15d692b57c187875c7/kuku.mp3"


def record_stream(url: str, output_path: str, duration_seconds: int):
    """Salvestab striimi ffmpeg abil, või puhta HTTP voona kui ffmpeg puudub."""
    if shutil.which("ffmpeg"):
        subprocess.run([
            "ffmpeg", "-y",
            "-i", url,
            "-t", str(duration_seconds),
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(output_path)
        ], check=True)
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        t0 = time.time()
        with open(output_path, "wb") as f:
            while time.time() - t0 < duration_seconds:
                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        while time.time() - t0 < duration_seconds:
                            chunk = resp.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                except Exception as e:
                    print(f"Hoiatus voo salvestamisel: {e}, proovin 2s pärast uuesti...")
                    time.sleep(2)


def update_library_with_episode(library_path: Path, show_id: int, show_name: str, entry: dict):
    """Tõmbab värskeima git seisu enne library.json lugemist ja kirjutamist, et vältida konflikte."""
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
    library = _read(library_path, {"shows": []})

    show_found = False
    for s in library.get("shows", []):
        if s["id"] == show_id:
            s["episodes"].insert(0, entry)
            show_found = True
            break

    if not show_found:
        library["shows"].append({
            "id": show_id,
            "name": show_name,
            "episodes": [entry]
        })

    _write(library_path, library)


def main():
    parser = argparse.ArgumentParser(description="Kuku otse-eetri salvestaja")
    parser.add_argument("--show-id", type=int, required=True, help="Saate ID")
    parser.add_argument("--show-name", type=str, required=True, help="Saate nimi")
    parser.add_argument("--duration", type=int, required=True, help="Pikkus minutites")
    parser.add_argument("--ad-times", type=str, default="", help="'auto' või komaga eraldatud min-max (nt '0-5,30-35')")
    parser.add_argument("--episode-title", type=str, required=True, help="Osa pealkiri")
    parser.add_argument(
        "--cut-start",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Lõika saate algusest uudised ja reklaamid maha (kui salvestus algas täistunnil)",
    )

    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    episode_id = int(now.timestamp())

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_mp3 = Path(tmpdir) / "raw.mp3"
        clean_mp3 = Path(tmpdir) / f"{episode_id}.mp3"

        # 1. Salvesta toorvoog
        print(f"Salvestan {args.duration} min striimi...")
        record_stream(STREAM_URL, str(raw_mp3), args.duration * 60)

        # 2. Reklaamide eemaldamine (kõllituvastusega toorfailist)
        ad_intervals = get_ad_intervals(args.ad_times, audio_path=raw_mp3, cut_start=args.cut_start)
        if ad_intervals:
            print(f"Eemaldan reklaamid ({len(ad_intervals)} intervalli: {ad_intervals})...")
            remove_ads(str(raw_mp3), str(clean_mp3), ad_intervals)
        else:
            clean_mp3 = raw_mp3

        # 3. GitHubi üleslaadimine või kohalikku kausta salvestamine
        repo = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")

        if not repo or not token:
            print("Tokenid puuduvad, salvestan kohalikku 'recordings' kausta.")
            rec_dir = Path("recordings")
            rec_dir.mkdir(exist_ok=True)
            dest = rec_dir / clean_mp3.name
            if clean_mp3 != raw_mp3:
                raw_dest = rec_dir / f"raw-{episode_id}.mp3"
                shutil.copy(raw_mp3, raw_dest)
                print(f"Salvestasin toorheli: {raw_dest}")
                clean_mp3.rename(dest)
            else:
                shutil.copy(clean_mp3, dest)
            print(f"Salvestasin saatefaili: {dest}")
            return

        print("Laen faili GitHubi...")
        github = GitHubClient(repo, token)
        tag = tag_for(args.show_id)
        release = github.get_or_create_release(tag, args.show_name)

        # Kui tehti reklaamilõiked, laeme toorheli varukoopiaks samuti üles,
        # et hiljem oleks võimalik osa teiste aegadega uuesti lõigata (recut).
        if clean_mp3 != raw_mp3:
            raw_asset_name = f"raw-{episode_id}.mp3"
            print(f"Laen toorfaili GitHubi ({raw_asset_name})...")
            github.upload_asset(release, str(raw_mp3), raw_asset_name, f"{args.episode_title} (Toorsalvestus)")

        asset = github.upload_asset(release, str(clean_mp3), f"{episode_id}.mp3", args.episode_title)

        actual_duration = int(round(clean_mp3.stat().st_size / 16000))
        ep = Episode(
            id=episode_id,
            title=args.episode_title,
            published_at=now,
            is_premium=False,
            is_playable=True,
            duration_seconds=actual_duration,
        )

        entry = _entry(ep, asset)
        library_path = DATA_DIR / "library.json"
        update_library_with_episode(library_path, args.show_id, args.show_name, entry)


if __name__ == "__main__":
    sys.exit(main())
