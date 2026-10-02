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


def _entry(episode, asset):
    return {
        "id": episode.id,
        "title": episode.title,
        "published_at": _iso(episode.published_at),
        "expires_at": _iso(expires_at(episode.published_at)),
        "duration_seconds": episode.duration_seconds,
        "url": asset["browser_download_url"],
    }


def _orphan_entry(episode_id, asset):
    """Releases'is olev fail, mille kohta library.json ega Kuku midagi ei tea."""
    published = datetime.fromisoformat(asset.get("created_at") or "1970-01-01T00:00:00+00:00")
    return {
        "id": episode_id,
        "title": asset.get("label") or f"Osa {episode_id}",
        "published_at": _iso(published),
        "expires_at": _iso(expires_at(published)),
        "duration_seconds": 0,
        "url": asset["browser_download_url"],
    }


def _sync_show(show, kuku, github, download, now, old_entries, warnings):
    release = github.get_or_create_release(tag_for(show["id"]), show["name"])
    assets = github.list_assets(release)

    try:
        episodes = kuku.list_episodes(show["id"], cutoff(now))
    except ShowNotFound:
        warnings.append(f"Saadet „{show['name']}“ ({show['id']}) Kukus enam pole.")
        episodes = []
    except requests.RequestException as exc:
        warnings.append(f"Saate „{show['name']}“ osade nimekirja ei saanud kätte: {exc}")
        episodes = []

    # Releases on tõe allikas: iga fail saab kirje, ka siis kui library.json seda ei tunne
    known = {e["id"]: e for e in old_entries}
    from_kuku = {e.id: e for e in episodes}
    entries = {}
    for name, asset in assets.items():
        try:
            episode_id = int(name.removesuffix(".mp3"))
        except ValueError:
            continue
        if episode_id in known:
            entries[episode_id] = {**known[episode_id], "url": asset["browser_download_url"]}
        elif episode_id in from_kuku:
            entries[episode_id] = _entry(from_kuku[episode_id], asset)
        else:
            entries[episode_id] = _orphan_entry(episode_id, asset)

    for episode in select_new(episodes, set(entries), now):
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
            try:
                asset = github.upload_asset(release, dest, dest.name, episode.title)
            except (OSError, requests.RequestException) as exc:
                warnings.append(f"Osa {episode.id} („{episode.title}“) üleslaadimine ebaõnnestus: {exc}")
                continue
        assets[dest.name] = asset
        entries[episode.id] = _entry(episode, asset)

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

    selected_tags = {tag_for(s["id"]) for s in selected}
    for release in github.list_show_releases():
        if release["tag_name"] not in selected_tags:
            github.delete_release(release, release["tag_name"])

    return warnings


def run(data_dir, kuku, github, download, now):
    status = {"ok": True, "kind": "", "message": "", "checked_at": _iso(now)}
    code = 0
    try:
        warnings = sync(data_dir, kuku, github, download, now)
        status["message"] = " ".join(warnings)
        for w in warnings:
            print(f"::warning::{w}")
    except KukuApiChanged as exc:
        status = {"ok": False, "kind": "api", "message": str(exc), "checked_at": _iso(now)}
        print(f"::error::Kuku liides muutus: {exc}")
        try:
            github.report_api_change(str(exc))
        except Exception:
            traceback.print_exc()
        code = 1
    except Exception as exc:
        # ajutine viga (võrk, GitHub, Kuku maas) — järgmine käivitus proovib uuesti
        traceback.print_exc()
        status = {"ok": False, "kind": "error", "message": f"Sünkroniseerimine ebaõnnestus: {exc}",
                  "checked_at": _iso(now)}
        code = 1
    _write(data_dir / "status.json", status)
    return code


def http_download(url, dest):
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        written = 0
        with dest.open("wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
                written += len(chunk)
        expected = resp.headers.get("Content-Length")
        if expected and written != int(expected):
            raise OSError(f"allalaadimine jäi poolikuks ({written} / {expected} baiti)")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    return run(DATA_DIR, KukuClient(), GitHubClient(repo, token), http_download,
               datetime.now(timezone.utc))


if __name__ == "__main__":
    sys.exit(main())
