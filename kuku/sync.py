"""Sünkroniseeri valitud Kuku saated GitHub Releases'i ja kirjuta lehe andmed.

Käivitus: python -m kuku.sync   (vajab GITHUB_REPOSITORY ja GITHUB_TOKEN)
"""

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests

from kuku.api import KukuApiChanged, KukuClient
from kuku.logic import expires_at, is_expired
from kuku.releases import GitHubClient

DATA_DIR = Path(__file__).resolve().parent.parent / "site" / "data"
# Vana 10-min test-asset ja varasemad Kuku API-st tõmmatud Digitunni topeltosad
OBSOLETE_DIGITUND_IDS = {1792131850, 309887, 309884, 309878}


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


def _sync_show(show, github, now, old_entries):
    release = github.get_or_create_release(tag_for(show["id"]), show["name"])
    assets = github.list_assets(release)

    if show["id"] == 209:
        for obsolete_id in OBSOLETE_DIGITUND_IDS:
            asset_name = f"{obsolete_id}.mp3"
            if asset_name in assets:
                github.delete_asset(assets.pop(asset_name)["id"])
        old_entries = [e for e in old_entries if e.get("id") not in OBSOLETE_DIGITUND_IDS]

    # Releases on tõe allikas: kõik osad tulevad otse-eetri salvestusest,
    # Kuku järelkuulamise API-st enam faile alla ei laadita.
    known = {e["id"]: e for e in old_entries}
    entries = {}
    for name, asset in assets.items():
        try:
            episode_id = int(name.removesuffix(".mp3"))
        except ValueError:
            continue
        if episode_id in known:
            entries[episode_id] = {**known[episode_id], "url": asset["browser_download_url"]}
        else:
            entries[episode_id] = _orphan_entry(episode_id, asset)

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
            episodes = _sync_show(show, github, now, old.get(show["id"], []))
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
