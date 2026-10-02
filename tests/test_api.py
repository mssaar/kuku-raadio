from datetime import datetime, timezone

import pytest

from kuku.api import KukuApiChanged, KukuClient, ShowNotFound
from tests.fixtures import SHOWS_PAGE, episode, episodes_page


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, routes):
        self.routes = routes  # {(path, page): (status, payload)}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        path = url.split("/api", 1)[1]
        page = (params or {}).get("page", 1)
        self.calls.append((path, page))
        status, payload = self.routes[(path, page)]
        return FakeResponse(status, payload)


def test_list_shows_parses_results():
    client = KukuClient(FakeSession({("/kuula/shows", 1): (200, SHOWS_PAGE)}))
    shows = client.list_shows()
    assert [s.id for s in shows] == [209, 246]
    assert shows[0].image == "https://img/209.png"
    assert shows[1].description == "" and shows[1].image == ""


def test_list_shows_missing_key_raises_api_changed():
    broken = {"items": []}
    client = KukuClient(FakeSession({("/kuula/shows", 1): (200, broken)}))
    with pytest.raises(KukuApiChanged, match="results"):
        client.list_shows()


def test_non_json_raises_api_changed():
    client = KukuClient(FakeSession({("/kuula/shows", 1): (200, ValueError("html"))}))
    with pytest.raises(KukuApiChanged, match="JSON"):
        client.list_shows()


def test_list_episodes_stops_before_since():
    since = datetime(2026, 5, 1, tzinfo=timezone.utc)
    page1 = episodes_page([episode(3, "2026-09-28T08:00:00.000000Z"),
                           episode(2, "2026-06-01T08:00:00.000000Z")], page=1, total=3)
    page2 = episodes_page([episode(1, "2026-04-01T08:00:00.000000Z")], page=2, total=3)
    session = FakeSession({("/kuula/shows/209/episodes", 1): (200, page1),
                           ("/kuula/shows/209/episodes", 2): (200, page2)})
    eps = KukuClient(session).list_episodes(209, since)
    assert [e.id for e in eps] == [3, 2]
    assert ("/kuula/shows/209/episodes", 3) not in session.calls
    assert eps[0].published_at == datetime(2026, 9, 28, 8, tzinfo=timezone.utc)
    assert eps[0].is_premium is False


def test_list_episodes_missing_field_raises_api_changed():
    bad = episodes_page([{"id": 1, "title": "x", "published_at": "2026-09-28T08:00:00Z"}])
    client = KukuClient(FakeSession({("/kuula/shows/209/episodes", 1): (200, bad)}))
    with pytest.raises(KukuApiChanged, match="is_premium"):
        client.list_episodes(209, datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_list_episodes_404_raises_show_not_found():
    client = KukuClient(FakeSession({("/kuula/shows/5/episodes", 1): (404, {})}))
    with pytest.raises(ShowNotFound):
        client.list_episodes(5, datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_episode_url():
    client = KukuClient(FakeSession({("/kuula/episodes/urls", 1): (200, {"77": "https://cdn/77.mp3"})}))
    assert client.episode_url(77) == "https://cdn/77.mp3"


def test_episode_url_missing_raises_api_changed():
    client = KukuClient(FakeSession({("/kuula/episodes/urls", 1): (200, {})}))
    with pytest.raises(KukuApiChanged, match="77"):
        client.episode_url(77)
