"""Raadio Kuku järelkuulamise API klient.

API pole ametlik avalik liides. Iga vastus valideeritakse; kui kuju muutub,
visatakse KukuApiChanged, et oleks selge, et koodi tuleb kohandada.
"""

import time
from dataclasses import dataclass
from datetime import datetime

import requests

API_BASE = "https://ams.postimees.ee/api"
DOMAIN = "kuku.pleier.ee"


class KukuApiChanged(Exception):
    """Kuku API vastus ei vasta oodatule — kood vajab kohandamist."""


class ShowNotFound(Exception):
    """Saadet Kukus enam pole."""


@dataclass
class Show:
    id: int
    name: str
    description: str
    image: str


@dataclass
class Episode:
    id: int
    title: str
    published_at: datetime
    is_premium: bool
    is_playable: bool
    duration_seconds: float


def _field(obj, key, types, where):
    if not isinstance(obj, dict) or key not in obj:
        raise KukuApiChanged(f"{where}: puudub väli '{key}'")
    value = obj[key]
    if not isinstance(value, types):
        raise KukuApiChanged(f"{where}: väli '{key}' on {type(value).__name__}, oodati {types}")
    return value


def _parse_time(value, where):
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise KukuApiChanged(f"{where}: ajatempel '{value}' pole loetav") from None


class KukuClient:
    def __init__(self, session=None, base=API_BASE):
        self.session = session or requests.Session()
        self.base = base

    def _get(self, path, params, where):
        url = self.base + path
        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=30)
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(5)
                continue
            if response.status_code >= 500 and attempt < 2:
                time.sleep(5)
                continue
            break
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise KukuApiChanged(f"{where}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise KukuApiChanged(f"{where}: vastus pole JSON") from None

    def list_shows(self):
        shows, page, total = [], 1, 1
        while page <= total:
            where = f"saadete nimekiri (lk {page})"
            data = self._get("/kuula/shows", {"domain": DOMAIN, "page": page}, where)
            if data is None:
                raise KukuApiChanged(f"{where}: HTTP 404")
            for item in _field(data, "results", list, where):
                thumb = item.get("thumbnail") if isinstance(item, dict) else None
                shows.append(Show(
                    id=_field(item, "id", int, where),
                    name=_field(item, "name", str, where),
                    description=item.get("description_short") or "",
                    image=(thumb or {}).get("square_250_x1") or "",
                ))
            total = _field(data, "total_pages", int, where)
            page += 1
        return shows

    def list_episodes(self, show_id, since):
        episodes, page, total = [], 1, 1
        while page <= total:
            where = f"saate {show_id} osad (lk {page})"
            data = self._get(f"/kuula/shows/{show_id}/episodes", {"domain": DOMAIN, "page": page}, where)
            if data is None:
                raise ShowNotFound(show_id)
            block = _field(data, "episodes", dict, where)
            reached_since = False
            for item in _field(block, "results", list, where):
                ep = Episode(
                    id=_field(item, "id", int, where),
                    title=_field(item, "title", str, where),
                    published_at=_parse_time(_field(item, "published_at", str, where), where),
                    is_premium=bool(_field(item, "is_premium", (int, bool), where)),
                    is_playable=bool(_field(item, "is_playable", (int, bool), where)),
                    duration_seconds=float(_field(item, "duration_seconds", (int, float), where)),
                )
                if ep.published_at < since:
                    reached_since = True
                    continue
                episodes.append(ep)
            if reached_since:
                break
            total = _field(block, "total_pages", int, where)
            page += 1
        return episodes

    def episode_url(self, episode_id):
        where = f"osa {episode_id} helifaili aadress"
        data = self._get("/kuula/episodes/urls", {"ids": episode_id}, where)
        url = data.get(str(episode_id)) if isinstance(data, dict) else None
        if not isinstance(url, str) or not url.startswith("http"):
            raise KukuApiChanged(f"{where}: vastuses puudub aadress osale {episode_id}")
        return url
