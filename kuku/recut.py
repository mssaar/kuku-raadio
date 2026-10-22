"""Tööriist juba salvestatud saate osa reklaamide uuesti lõikamiseks."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Union

from kuku.live import get_ad_intervals, remove_ads
from kuku.releases import GitHubClient
from kuku.sync import DATA_DIR, tag_for, http_download, _read, _write


def get_mp3_duration(path: Path) -> int:
    """Arvutab 128 kbps CBR MP3 kestuse sekundites faili suuruse järgi."""
    size = path.stat().st_size
    # 128 kbps = 16000 baiti sekundis
    return int(round(size / 16000))


def recut_episode(
    github: GitHubClient,
    show_id: int,
    episode_id: int,
    ad_intervals: Union[list[tuple[int, int]], str],
    library_path: Path,
    download_func: Callable[[str, Path], None] = None,
    remove_ads_func: Callable[[str, str, list[tuple[int, int]]], None] = None,
) -> int:
    download = download_func or http_download
    do_remove_ads = remove_ads_func or remove_ads

    tag = tag_for(show_id)
    release = github.find_release(tag)
    if not release:
        raise ValueError(f"Release'i sildiga {tag} ei leitud.")

    assets = github.list_assets(release)
    asset_name = f"{episode_id}.mp3"
    raw_asset_name = f"raw-{episode_id}.mp3"

    # Eelistame toorsalvestust, et vältida juba kärbitud faili uuesti lõikamist
    source_asset_name = raw_asset_name if raw_asset_name in assets else asset_name
    if source_asset_name not in assets:
        raise ValueError(f"Faili {asset_name} ega {raw_asset_name} ei leitud release'ist {tag}.")

    source_asset = assets[source_asset_name]
    clean_asset = assets.get(asset_name, source_asset)
    label = clean_asset.get("label") or f"Osa {episode_id}"
    download_url = source_asset["browser_download_url"]

    with tempfile.TemporaryDirectory() as tmpdir:
        input_mp3 = Path(tmpdir) / "source.mp3"
        output_mp3 = Path(tmpdir) / asset_name

        print(f"Laen alla lähtefaili ({source_asset_name}): {download_url}...")
        download(download_url, input_mp3)

        intervals_to_use = ad_intervals
        if ad_intervals == "auto" or (isinstance(ad_intervals, list) and not ad_intervals):
            intervals_to_use = get_ad_intervals("auto", audio_path=input_mp3)

        print(f"Lõikan reklaamid vahemikega: {intervals_to_use}...")
        do_remove_ads(str(input_mp3), str(output_mp3), intervals_to_use)

        duration_sec = get_mp3_duration(output_mp3)
        print(f"Uus kestus: {duration_sec} sekundit ({duration_sec // 60}m {duration_sec % 60}s)")

        if asset_name in assets:
            print(f"Kustutan vana lõigatud asseti {assets[asset_name]['id']}...")
            github.delete_asset(assets[asset_name]["id"])

        print(f"Laen uue lõigatud faili release'i {tag} alla...")
        new_asset = github.upload_asset(release, str(output_mp3), asset_name, label)

    # Uuendame library.json failis kestuse ja lingi
    library = _read(library_path, {"shows": []})
    for s in library.get("shows", []):
        if s["id"] == show_id:
            for ep in s.get("episodes", []):
                if ep["id"] == episode_id:
                    ep["duration_seconds"] = duration_sec
                    if "browser_download_url" in new_asset:
                        ep["url"] = new_asset["browser_download_url"]
                    break

    _write(library_path, library)
    return duration_sec


def main():
    parser = argparse.ArgumentParser(description="Kuku osa uuesti lõikaja")
    parser.add_argument("--show-id", type=int, required=True, help="Saate ID (nt 514)")
    parser.add_argument("--episode-id", type=int, required=True, help="Osa ID (nt 1792141202)")
    parser.add_argument("--ad-times", type=str, required=True, help="Reklaamide vahemikud (nt 'auto' või '0-1:55, 11:10-13:20, 24:10-25:00, 35:50-37:50')")

    args = parser.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("Viga: GITHUB_REPOSITORY ja GITHUB_TOKEN peavad olema keskkonnamuutujates.")
        sys.exit(1)

    gh = GitHubClient(repo, token)
    intervals = "auto" if args.ad_times.lower() == "auto" else get_ad_intervals(args.ad_times)
    library_path = DATA_DIR / "library.json"
    recut_episode(gh, args.show_id, args.episode_id, intervals, library_path)


if __name__ == "__main__":
    main()
