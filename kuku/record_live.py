"""Kuku otse-eetri salvestamise CLI tööriist."""

import argparse
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess

from kuku.live import get_ad_intervals, remove_ads
from kuku.releases import GitHubClient
from kuku.sync import DATA_DIR, tag_for, _entry, _read, _write
from kuku.api import Episode

STREAM_URL = "http://naba-live.babahhcdn.com/kuku/kuku.stream/playlist.m3u8"

def record_stream(url: str, output_path: str, duration_seconds: int):
    """Salvestab striimi ffmpeg abil."""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", url,
        "-t", str(duration_seconds),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(output_path)
    ], check=True)

def main():
    parser = argparse.ArgumentParser(description="Kuku otse-eetri salvestaja")
    parser.add_argument("--show-id", type=int, required=True, help="Saate ID")
    parser.add_argument("--show-name", type=str, required=True, help="Saate nimi")
    parser.add_argument("--duration", type=int, required=True, help="Pikkus minutites")
    parser.add_argument("--ad-times", type=str, default="", help="'auto' või komaga eraldatud min-max (nt '0-5,30-35')")
    parser.add_argument("--episode-title", type=str, required=True, help="Osa pealkiri")
    
    args = parser.parse_args()
    
    now = datetime.now(timezone.utc)
    episode_id = int(now.timestamp())
    
    ad_intervals = get_ad_intervals(args.ad_times)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_mp3 = Path(tmpdir) / "raw.mp3"
        clean_mp3 = Path(tmpdir) / f"{episode_id}.mp3"
        
        # 1. Salvesta
        print(f"Salvestan {args.duration} min striimi...")
        record_stream(STREAM_URL, str(raw_mp3), args.duration * 60)
        
        # 2. Reklaamide eemaldamine
        if ad_intervals:
            print("Eemaldan reklaamid...")
            remove_ads(str(raw_mp3), str(clean_mp3), ad_intervals)
        else:
            clean_mp3 = raw_mp3
            
        # 3. GitHubi üleslaadimine
        repo = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        
        if not repo or not token:
            print("Tokenid puuduvad, salvestan kohalikku 'recordings' kausta.")
            rec_dir = Path("recordings")
            rec_dir.mkdir(exist_ok=True)
            dest = rec_dir / clean_mp3.name
            if clean_mp3 != raw_mp3:
                clean_mp3.rename(dest)
            else:
                import shutil
                shutil.copy(clean_mp3, dest)
            return
            
        print("Laen faili GitHubi...")
        github = GitHubClient(repo, token)
        tag = tag_for(args.show_id)
        release = github.get_or_create_release(tag, args.show_name)
        
        asset = github.upload_asset(release, str(clean_mp3), f"{episode_id}.mp3", args.episode_title)
        
        ep = Episode(
            id=episode_id,
            title=args.episode_title,
            published_at=now,
            is_premium=False,
            is_playable=True,
            duration_seconds=args.duration * 60,
        )
        
        entry = _entry(ep, asset)
        library_path = DATA_DIR / "library.json"
        library = _read(library_path, {"shows": []})
        
        show_found = False
        for s in library.get("shows", []):
            if s["id"] == args.show_id:
                s["episodes"].insert(0, entry)
                show_found = True
                break
                
        if not show_found:
            library["shows"].append({
                "id": args.show_id,
                "name": args.show_name,
                "episodes": [entry]
            })
            
        _write(library_path, library)

if __name__ == "__main__":
    sys.exit(main())
