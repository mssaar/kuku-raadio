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
        value = self.episodes[show_id]
        if value is ShowNotFound:
            raise ShowNotFound(show_id)
        return [e for e in value if e.published_at >= since]

    def episode_url(self, episode_id):
        return f"https://cdn/{episode_id}.mp3"


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


def test_downloads_free_episodes_and_writes_library(data):
    gh = FakeGitHub()
    kuku = FakeKuku({209: [ep(2, 1), ep(1, 8, premium=True)]})
    assert sync(data, kuku, gh, good_download, NOW) == []
    assert list(gh.releases["saade-209"]["assets"]) == ["2.mp3"]
    lib = read(data, "library.json")
    assert lib["shows"][0]["name"] == "Digitund"
    entry = lib["shows"][0]["episodes"][0]
    assert entry["id"] == 2 and entry["url"] == "https://gh/2.mp3"
    assert entry["expires_at"] == "2027-04-01T12:00:00Z"
    assert read(data, "catalog.json")["shows"][0]["name"] == "Digitund"


def test_second_run_does_not_redownload(data):
    gh, calls = FakeGitHub(), []
    kuku = FakeKuku({209: [ep(2, 1)]})
    sync(data, kuku, gh, good_download, NOW)
    sync(data, kuku, gh, lambda u, d: calls.append(u), NOW)
    assert calls == []
    assert len(read(data, "library.json")["shows"][0]["episodes"]) == 1


def test_expired_episodes_are_deleted(data):
    gh = FakeGitHub()
    sync(data, FakeKuku({209: [ep(2, 1)]}), gh, good_download, NOW)
    later = NOW + timedelta(days=190)
    sync(data, FakeKuku({209: []}), gh, good_download, later)
    assert gh.releases["saade-209"]["assets"] == {}
    assert read(data, "library.json")["shows"][0]["episodes"] == []


def test_removed_show_release_is_deleted(data):
    gh = FakeGitHub()
    sync(data, FakeKuku({209: [ep(2, 1)]}), gh, good_download, NOW)
    (data / "shows.json").write_text("[]")
    sync(data, FakeKuku({}), gh, good_download, NOW)
    assert "saade-209" not in gh.releases
    assert read(data, "library.json")["shows"] == []


def test_teaser_download_raises_api_changed_and_is_not_uploaded(data):
    gh = FakeGitHub()
    with pytest.raises(KukuApiChanged, match="teaser"):
        sync(data, FakeKuku({209: [ep(2, 1)]}), gh, lambda u, d: d.write_bytes(b"ID3short"), NOW)
    assert gh.releases["saade-209"]["assets"] == {}


def test_failed_download_skips_episode_and_continues(data):
    gh = FakeGitHub()

    def flaky(url, dest):
        if "/2.mp3" in url:
            raise OSError("ühendus katkes")
        dest.write_bytes(MP3)

    warnings = sync(data, FakeKuku({209: [ep(3, 1), ep(2, 8)]}), gh, flaky, NOW)
    assert list(gh.releases["saade-209"]["assets"]) == ["3.mp3"]
    assert any("Osa 2" in w for w in warnings)


def test_missing_show_is_warning_not_failure(data):
    (data / "shows.json").write_text(json.dumps([{"id": 5, "name": "Kadunud"},
                                                 {"id": 209, "name": "Digitund"}]))
    gh = FakeGitHub()
    warnings = sync(data, FakeKuku({5: ShowNotFound, 209: [ep(2, 1)]}), gh, good_download, NOW)
    assert any("Kadunud" in w for w in warnings)
    assert "2.mp3" in gh.releases["saade-209"]["assets"]


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


def test_asset_without_library_entry_is_restored_from_kuku(data):
    gh = FakeGitHub()
    rel = gh.get_or_create_release("saade-209", "Digitund")
    rel["assets"]["2.mp3"] = {"id": 50, "browser_download_url": "https://gh/2.mp3",
                              "label": "Osa 2", "created_at": "2026-10-01T13:00:00Z"}
    calls = []
    sync(data, FakeKuku({209: [ep(2, 1)]}), gh, lambda u, d: calls.append(u), NOW)
    assert calls == []
    entry = read(data, "library.json")["shows"][0]["episodes"][0]
    assert entry["id"] == 2 and entry["url"] == "https://gh/2.mp3"
    assert entry["published_at"] == "2026-10-01T12:00:00Z"


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


def test_failed_upload_skips_episode_and_continues(data):
    gh = FakeGitHub(fail_upload=True)
    warnings = sync(data, FakeKuku({209: [ep(2, 1)]}), gh, good_download, NOW)
    assert any("Osa 2" in w for w in warnings)
    assert read(data, "library.json")["shows"][0]["episodes"] == []


def test_network_error_for_one_show_is_warning(data):
    import requests

    class Flaky(FakeKuku):
        def list_episodes(self, show_id, since):
            if show_id == 5:
                raise requests.ConnectionError("ühendus katkes")
            return super().list_episodes(show_id, since)

    (data / "shows.json").write_text(json.dumps([{"id": 5, "name": "Katki"}, {"id": 209, "name": "Digitund"}]))
    gh = FakeGitHub()
    warnings = sync(data, Flaky({209: [ep(2, 1)]}), gh, good_download, NOW)
    assert any("Katki" in w for w in warnings)
    assert "2.mp3" in gh.releases["saade-209"]["assets"]


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
