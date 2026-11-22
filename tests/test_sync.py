import json
from datetime import datetime, timedelta, timezone

import pytest

from kuku.api import Episode, KukuApiChanged, Show, ShowNotFound
from kuku.sync import run, sync

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
MP3 = b"ID3" + b"\0" * (100 * 8000)


def ep(id, days_ago, premium=False):
    return Episode(id, f"Osa {id}", NOW - timedelta(days=days_ago), premium, True, 100.0)


class FakeKuku:
    def __init__(self, episodes, shows=None, broken=False):
        self.episodes = episodes  # {show_id: [Episode] | ShowNotFound}
        self.shows = shows or [Show(209, "Digitund", "", "")]
        self.broken = broken

    def list_shows(self):
        if self.broken:
            raise KukuApiChanged("saadete nimekiri: puudub väli 'results'")
        return self.shows

    def list_episodes(self, show_id, since):
        raise AssertionError("sync ei tohi Kuku järelkuulamise API-st osi küsida")

    def episode_url(self, episode_id):
        raise AssertionError("sync ei tohi Kuku järelkuulamise API-st helifaile küsida")


class FakeGitHub:
    def __init__(self, fail_upload=False):
        self.releases = {}  # tag -> {"id", "name", "assets": {name: {...}}}
        self.reports = []
        self.fail_upload = fail_upload
        self._next = 1

    def find_release(self, tag):
        return self.releases.get(tag)

    def get_or_create_release(self, tag, name):
        if tag not in self.releases:
            self.releases[tag] = {"id": self._next, "name": name, "assets": {}}
            self._next += 1
        return self.releases[tag]

    def list_assets(self, release):
        return dict(release["assets"])

    def list_show_releases(self):
        return [{"id": r["id"], "tag_name": tag} for tag, r in self.releases.items()]

    def upload_asset(self, release, path, name, label):
        if self.fail_upload:
            raise OSError("üleslaadimine katkes")
        asset = {"id": self._next, "browser_download_url": f"https://gh/{name}",
                 "label": label, "created_at": "2026-10-02T12:00:00Z"}
        self._next += 1
        release["assets"][name] = asset
        return asset

    def delete_asset(self, asset_id):
        for rel in self.releases.values():
            rel["assets"] = {n: a for n, a in rel["assets"].items() if a["id"] != asset_id}

    def delete_release(self, release, tag):
        self.releases.pop(tag, None)

    def report_api_change(self, message):
        self.reports.append(message)


def good_download(url, dest):
    dest.write_bytes(MP3)


@pytest.fixture
def data(tmp_path):
    (tmp_path / "shows.json").write_text(json.dumps([{"id": 209, "name": "Digitund"}]))
    (tmp_path / "library.json").write_text(json.dumps({"shows": []}))
    return tmp_path


def read(data, name):
    return json.loads((data / name).read_text(encoding="utf-8"))


def test_does_not_download_free_episodes_from_kuku_api(data):
    gh = FakeGitHub()
    calls = []
    kuku = FakeKuku({209: [ep(2, 1), ep(1, 8, premium=False)]})
    assert sync(data, kuku, gh, lambda u, d: calls.append(u), NOW) == []
    assert calls == []
    assert gh.releases["saade-209"]["assets"] == {}
    lib = read(data, "library.json")
    assert lib["shows"][0]["name"] == "Digitund"
    assert lib["shows"][0]["episodes"] == []
    assert read(data, "catalog.json")["shows"][0]["name"] == "Digitund"


def test_preserves_existing_release_assets_and_known_metadata(data):
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-209", "Digitund")
    rel["assets"]["1794214801.mp3"] = {
        "id": 50,
        "browser_download_url": "https://gh/1794214801.mp3",
        "label": "Digitund (09.11.2026)",
        "created_at": "2026-10-01T09:00:01Z",
    }
    (data / "library.json").write_text(json.dumps({
        "shows": [{
            "id": 209,
            "name": "Digitund",
            "episodes": [{
                "id": 1794214801,
                "title": "Digitund (09.11.2026)",
                "published_at": "2026-10-01T09:00:01Z",
                "expires_at": "2027-04-01T09:00:01Z",
                "duration_seconds": 2745,
                "url": "https://old/1794214801.mp3",
            }],
        }]
    }))
    sync(data, FakeKuku({209: []}), gh, good_download, NOW)
    entry = read(data, "library.json")["shows"][0]["episodes"][0]
    assert entry["id"] == 1794214801
    assert entry["url"] == "https://gh/1794214801.mp3"
    assert entry["duration_seconds"] == 2745


def test_expired_episodes_are_deleted(data):
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-209", "Digitund")
    rel["assets"]["2.mp3"] = {"id": 50, "browser_download_url": "https://gh/2.mp3",
                              "label": "Osa 2", "created_at": "2026-10-01T12:00:00Z"}
    sync(data, FakeKuku({209: []}), gh, good_download, NOW)
    later = NOW + timedelta(days=190)
    sync(data, FakeKuku({209: []}), gh, good_download, later)
    assert gh.releases["saade-209"]["assets"] == {}
    assert read(data, "library.json")["shows"][0]["episodes"] == []


def test_removed_show_release_is_deleted(data):
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-209", "Digitund")
    rel["assets"]["2.mp3"] = {"id": 50, "browser_download_url": "https://gh/2.mp3",
                              "label": "Osa 2", "created_at": "2026-10-01T12:00:00Z"}
    sync(data, FakeKuku({209: []}), gh, good_download, NOW)
    (data / "shows.json").write_text("[]")
    sync(data, FakeKuku({}), gh, good_download, NOW)
    assert "saade-209" not in gh.releases
    assert read(data, "library.json")["shows"] == []


def test_run_reports_api_change(data):
    gh = FakeGitHub()
    code = run(data, FakeKuku({209: []}, broken=True), gh, good_download, NOW)
    assert code == 1
    status = read(data, "status.json")
    assert status["ok"] is False and "results" in status["message"]
    assert gh.reports and "results" in gh.reports[0]


def test_run_ok_status(data):
    assert run(data, FakeKuku({209: []}), FakeGitHub(), good_download, NOW) == 0
    assert read(data, "status.json")["ok"] is True


def test_asset_without_library_entry_is_restored_as_orphan(data):
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-209", "Digitund")
    rel["assets"]["2.mp3"] = {"id": 50, "browser_download_url": "https://gh/2.mp3",
                              "label": "Osa 2", "created_at": "2026-10-01T13:00:00Z"}
    calls = []
    sync(data, FakeKuku({209: []}), gh, lambda u, d: calls.append(u), NOW)
    assert calls == []
    entry = read(data, "library.json")["shows"][0]["episodes"][0]
    assert entry["id"] == 2 and entry["url"] == "https://gh/2.mp3"
    assert entry["title"] == "Osa 2"
    assert entry["published_at"] == "2026-10-01T13:00:00Z"


def test_unknown_old_asset_is_expired_by_upload_time(data):
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-209", "Digitund")
    rel["assets"]["9.mp3"] = {"id": 51, "browser_download_url": "https://gh/9.mp3",
                              "label": "Vana osa", "created_at": "2026-01-01T00:00:00Z"}
    rel["assets"]["8.mp3"] = {"id": 52, "browser_download_url": "https://gh/8.mp3",
                              "label": "Uuem osa", "created_at": "2026-09-01T00:00:00Z"}
    sync(data, FakeKuku({209: []}), gh, good_download, NOW)
    assert list(rel["assets"]) == ["8.mp3"]
    entry = read(data, "library.json")["shows"][0]["episodes"][0]
    assert entry["id"] == 8 and entry["title"] == "Uuem osa"


def test_deletes_obsolete_duplicate_digitund_assets(data):
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-209", "Digitund")
    for ep_id in (1792131850, 309887, 309884, 309878, 1794214801):
        rel["assets"][f"{ep_id}.mp3"] = {
            "id": ep_id,
            "browser_download_url": f"https://gh/{ep_id}.mp3",
            "label": f"Osa {ep_id}",
            "created_at": "2026-10-01T12:00:00Z",
        }
    sync(data, FakeKuku({209: []}), gh, good_download, NOW)
    assert list(rel["assets"]) == ["1794214801.mp3"]
    entries = read(data, "library.json")["shows"][0]["episodes"]
    assert [e["id"] for e in entries] == [1794214801]


def test_release_of_show_unknown_to_library_is_deleted(data):
    gh = FakeGitHub()
    gh.get_or_create_release("saade-77", "Unustatud")
    sync(data, FakeKuku({209: []}), gh, good_download, NOW)
    assert "saade-77" not in gh.releases
    assert "saade-209" in gh.releases


def test_run_reports_other_failures_without_issue(data):
    import requests

    class Down(FakeKuku):
        def list_shows(self):
            raise requests.HTTPError("Kuku vastas HTTP 503")

    gh = FakeGitHub()
    assert run(data, Down({209: []}), gh, good_download, NOW) == 1
    status = read(data, "status.json")
    assert status["ok"] is False and status["kind"] == "error" and "503" in status["message"]
    assert gh.reports == []


def test_run_api_change_status_kind(data):
    run(data, FakeKuku({209: []}, broken=True), FakeGitHub(), good_download, NOW)
    assert read(data, "status.json")["kind"] == "api"


def test_http_download_rejects_truncated_body(tmp_path, monkeypatch):
    from kuku import sync as sync_mod

    class Resp:
        headers = {"Content-Length": "100"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, n):
            yield b"x" * 60

    monkeypatch.setattr(sync_mod.requests, "get", lambda *a, **k: Resp())
    with pytest.raises(OSError, match="poolik"):
        sync_mod.http_download("https://cdn/1.mp3", tmp_path / "1.mp3")


def test_sync_skips_kuku_api_for_live_only_show(data):
    (data / "shows.json").write_text(json.dumps([
        {"id": 999999, "name": "Kuku Raadio otse-eeter (Test)", "live_only": True}
    ]))
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-999999", "Kuku Raadio otse-eeter (Test)")
    gh.upload_asset(rel, None, "100.mp3", "Otse-eetri test (5 min)")
    kuku = FakeKuku({999999: ShowNotFound})
    warnings = sync(data, kuku, gh, good_download, NOW)
    assert warnings == []
    lib = read(data, "library.json")
    assert len(lib["shows"]) == 1
    assert lib["shows"][0]["id"] == 999999
    assert len(lib["shows"][0]["episodes"]) == 1
