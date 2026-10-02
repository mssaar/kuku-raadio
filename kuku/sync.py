"""Sünkroniseeri valitud Kuku saated GitHub Releases'i ja kirjuta lehe andmed.

Käivitus: python -m kuku.sync   (vajab GITHUB_REPOSITORY ja GITHUB_TOKEN)
"""

import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests

from kuku.api import KukuApiChanged, KukuClient, ShowNotFound
from kuku.logic import cutoff, expires_at, is_expired, looks_like_full_mp3, select_new
from kuku.releases import GitHubClient

DATA_DIR = Path(__file__).resolve().parent.parent / "site" / "data"


def _read(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tag_for(show_id):
    return f"saade-{show_id}"


def _sync_show(show, kuku, github, download, now, old_entries, warnings):
    release = github.get_or_create_release(tag_for(show["id"]), show["name"])
    assets = github.list_assets(release)
    entries = {e["id"]: e for e in old_entries if f"{e['id']}.mp3" in assets}

    try:
        episodes = kuku.list_episodes(show["id"], cutoff(now))
    except ShowNotFound:
        warnings.append(f"Saadet „{show['name']}“ ({show['id']}) Kukus enam pole.")
        episodes = []

    stored_ids = {int(name.removesuffix(".mp3")) for name in assets if name.endswith(".mp3")}
    for episode in select_new(episodes, stored_ids, now):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / f"{episode.id}.mp3"
            try:
                download(kuku.episode_url(episode.id), dest)
            except (OSError, requests.RequestException) as exc:
                warnings.append(f"Osa {episode.id} („{episode.title}“) allalaadimine ebaõnnestus: {exc}")
                continue
            with dest.open("rb") as f:
                head = f.read(4)
            size = dest.stat().st_size
            if not looks_like_full_mp3(head, size, episode.duration_seconds):
                raise KukuApiChanged(
                    f"osa {episode.id} fail on liiga lühike või pole MP3 "
                    f"({size} baiti, oodati ~{int(episode.duration_seconds)} s) — "
                    "tõenäoliselt annab Kuku nüüd ainult teaserit")
            asset = github.upload_asset(release, dest, dest.name, episode.title)
        assets[dest.name] = asset
        entries[episode.id] = {
            "id": episode.id,
            "title": episode.title,
            "published_at": _iso(episode.published_at),
            "expires_at": _iso(expires_at(episode.published_at)),
            "duration_seconds": episode.duration_seconds,
            "url": asset["browser_download_url"],
        }

    for entry in list(entries.values()):
        if is_expired(datetime.fromisoformat(entry["published_at"]), now):
            github.delete_asset(assets[f"{entry['id']}.mp3"]["id"])
            del entries[entry["id"]]

    return sorted(entries.values(), key=lambda e: e["published_at"], reverse=True)


def sync(data_dir, kuku, github, download, now):
    warnings = []
    selected = _read(data_dir / "shows.json", [])
    library = _read(data_dir / "library.json", {"shows": []})
    old = {s["id"]: s["episodes"] for s in library.get("shows", [])}

    catalog = kuku.list_shows()
    _write(data_dir / "catalog.json", {
        "updated_at": _iso(now),
        "shows": [{"id": s.id, "name": s.name, "description": s.description, "image": s.image}
                  for s in sorted(catalog, key=lambda s: s.name.lower())],
    })

    shows_out = []
    try:
        for show in selected:
            episodes = _sync_show(show, kuku, github, download, now, old.get(show["id"], []), warnings)
            shows_out.append({"id": show["id"], "name": show["name"], "episodes": episodes})
    finally:
        # kirjuta ka vea korral, et juba üles laaditud osad jääks kirja
        selected_ids = {s["id"] for s in selected}
        done_ids = {s["id"] for s in shows_out}
        kept = [s for s in library.get("shows", [])
                if s["id"] in selected_ids and s["id"] not in done_ids]
        _write(data_dir / "library.json",
               {"shows": sorted(shows_out + kept, key=lambda s: s["name"].lower())})

    for show_id in set(old) - {s["id"] for s in selected}:
        release = github.find_release(tag_for(show_id))
        if release:
            github.delete_release(release, tag_for(show_id))

    return warnings


def run(data_dir, kuku, github, download, now):
    status = {"ok": True, "message": "", "checked_at": _iso(now)}
    code = 0
    try:
        warnings = sync(data_dir, kuku, github, download, now)
        status["message"] = " ".join(warnings)
        for w in warnings:
            print(f"::warning::{w}")
    except KukuApiChanged as exc:
        status = {"ok": False, "message": str(exc), "checked_at": _iso(now)}
        print(f"::error::Kuku liides muutus: {exc}")
        try:
            github.report_api_change(str(exc))
        except Exception:
            traceback.print_exc()
        code = 1
    _write(data_dir / "status.json", status)
    return code


def http_download(url, dest):
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    return run(DATA_DIR, KukuClient(), GitHubClient(repo, token), http_download,
               datetime.now(timezone.utc))


if __name__ == "__main__":
    sys.exit(main())
