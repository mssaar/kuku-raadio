# Kuku arhiiv — tööplaan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub Pages leht, kus saab Kuku saateid otsida, salvestamiseks valida ja salvestatud (reklaamideta) osi 6 kuu jooksul kuulata; GitHub Actions laeb tasuta osad Releases'i ja annab teada, kui Kuku API muutub.

**Architecture:** Python-pakett `kuku/` (API klient valideerimisega, puhas loogika, GitHub Releases klient, sync-orkestreerija) jookseb GitHub Actionsis iga 3 h, kirjutab `site/data/*.json` ja deploy'b `site/` Pages'i. Staatiline leht (`site/`, ES-moodulid, ilma build-sammuta) loeb neid JSON-e, mängib Releases'i MP3-e ja muudab `shows.json`-i GitHub Contents API kaudu võtmega, mis on repos parooliga krüpteeritud (`auth.json`).

**Tech Stack:** Python 3.12, `requests`, pytest; vanilla JS (ES modules), WebCrypto, `node --test` (Node 22); GitHub Actions, Releases, Pages.

**Spec:** `docs/superpowers/specs/2026-10-02-kuku-arhiiv-design.md`

## Global Constraints

- Kuku API baas: `https://ams.postimees.ee/api`, kõigil päringutel `domain=kuku.pleier.ee` (v.a `episodes/urls`).
- Laetakse ainult osi, kus `is_premium == 0` ja `is_playable == true`.
- Säilitusaeg: 182 päeva alates `published_at`.
- Allalaaditud fail peab algama MP3 päisega ja olema ≥ `duration_seconds × 8000` baiti.
- `KukuApiChanged` → `status.json` `ok:false`, issue sildiga `kuku-muutus`, töövoog ebaõnnestub.
- Krüpto: PBKDF2-SHA256, 600 000 iteratsiooni, AES-GCM 256; `auth.json` = `{v:1, salt, iv, iterations, ciphertext}` base64.
- Sessioon `localStorage` võtmes `kuku.session`, kehtib 365 päeva.
- Parooli ei kirjutata ühtegi faili. Kogu UI tekst eesti keeles.
- Release tag `saade-<show_id>`, asset `<episode_id>.mp3`.

## Review Focus

1. Saade kaob Kukust (episodes → 404): ülejäänud saated peavad ikka sünkima; status näitab hoiatust, aga see pole "API muutus".
2. Ühe osa allalaadimine katkeb võrguvea tõttu: teised osad jätkuvad, järgmine käivitus proovib uuesti; poolik fail ei jõua Releases'i.
3. Vale parool / rikutud `auth.json`: leht ütleb "Vale parool", ei viska erindit ega logi sisse.
4. Kasutaja eemaldab saate: release ja kirje library.json-ist kaovad järgmisel sync'il; uuesti lisamine töötab.
5. Sync ebaõnnestub: `status.json` ja Pages uuenevad sellest hoolimata (bänner nähtav).

---

## Failistruktuur

```
kuku/__init__.py        tühi
kuku/api.py             KukuApiChanged, ShowNotFound, Show, Episode, KukuClient
kuku/logic.py           puhtad funktsioonid: cutoff, select_new, is_expired, looks_like_full_mp3, expires_at
kuku/releases.py        GitHubClient: releases/assets/issues
kuku/sync.py            sync() orkestreerija + main()
tests/fixtures.py       Kuku näidisvastused
tests/test_api.py
tests/test_logic.py
tests/test_sync.py
site/index.html
site/style.css
site/app.js             UI
site/lib/crypto.js      encryptToken / decryptToken
site/lib/session.js     saveSession / loadSession / clearSession
site/lib/search.js      normalize / searchShows
site/lib/github.js      getFile / putFile (Contents API)
site/data/config.json   {"repo": "mssaar/kuku-raadio"}
site/data/shows.json    []
site/data/catalog.json  {"updated_at": null, "shows": []}
site/data/library.json  {"shows": []}
site/data/status.json   {"ok": true, "message": "", "checked_at": null}
tests_js/*.test.mjs
.github/workflows/sync.yml
requirements.txt        requests, pytest
```

Eemaldatakse: `record.py`, `test_record.py`, `.github/workflows/record.yml` (pole commit'itud).

---

### Task 1: Kuku API klient valideerimisega

**Files:**
- Create: `kuku/__init__.py`, `kuku/api.py`, `tests/__init__.py`, `tests/fixtures.py`, `tests/test_api.py`, `requirements.txt`
- Delete: `record.py`, `test_record.py`, `.github/workflows/record.yml`

**Interfaces:**
- Produces:
  - `class KukuApiChanged(Exception)`, `class ShowNotFound(Exception)`
  - `@dataclass Show(id:int, name:str, description:str, image:str)`
  - `@dataclass Episode(id:int, title:str, published_at:datetime, is_premium:bool, is_playable:bool, duration_seconds:float)`
  - `KukuClient(session=None, base=API_BASE)` with `list_shows() -> list[Show]`, `list_episodes(show_id:int, since:datetime) -> list[Episode]` (uuemad eespool, peatub kui leht ulatub enne `since`), `episode_url(episode_id:int) -> str`

- [ ] **Step 1: Fixtures**

```python
# tests/fixtures.py
SHOWS_PAGE = {
    "results": [
        {"id": 209, "name": "Digitund", "description_short": "Tehnoloogiasaade",
         "thumbnail": {"square_250_x1": "https://img/209.png"}},
        {"id": 246, "name": "Olukorrast ajakirjanduses", "description_short": None, "thumbnail": None},
    ],
    "current_page": 1,
    "total_pages": 1,
}


def episode(id, published_at, premium=0, playable=True, duration=2796.5, title=None):
    return {"id": id, "title": title or f"Osa {id}", "published_at": published_at,
            "is_premium": premium, "is_playable": playable, "duration_seconds": duration}


def episodes_page(results, page=1, total=1):
    return {"show": {"id": 209, "name": "Digitund"},
            "episodes": {"results": results, "current_page": page, "total_pages": total}}
```

- [ ] **Step 2: Failing tests**

```python
# tests/test_api.py
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
```

- [ ] **Step 3: Run** `python -m pytest tests/test_api.py -q` → FAIL (module missing)

- [ ] **Step 4: Implement**

```python
# kuku/api.py
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
        if not isinstance(data, dict) or not isinstance(data.get(str(episode_id)), str) \
                or not data[str(episode_id)].startswith("http"):
            raise KukuApiChanged(f"{where}: vastuses puudub aadress osale {episode_id}")
        return data[str(episode_id)]
```

`requirements.txt`:
```
requests>=2.31
pytest>=8
```

- [ ] **Step 5: Run** `python -m pytest tests/test_api.py -q` → PASS

- [ ] **Step 6: Commit** `git add -A kuku tests requirements.txt && git commit -m "Kuku API klient valideerimisega"`

---

### Task 2: Puhas loogika

**Files:** Create `kuku/logic.py`, `tests/test_logic.py`

**Interfaces:**
- Consumes: `Episode` (Task 1)
- Produces:
  - `RETENTION = timedelta(days=182)`
  - `cutoff(now:datetime) -> datetime`
  - `expires_at(published_at:datetime) -> datetime`
  - `select_new(episodes:list[Episode], stored_ids:set[int], now:datetime) -> list[Episode]` (vanemad eespool)
  - `is_expired(published_at:datetime, now:datetime) -> bool`
  - `looks_like_full_mp3(head:bytes, size:int, duration_seconds:float) -> bool`

- [ ] **Step 1: Failing tests**

```python
# tests/test_logic.py
from datetime import datetime, timedelta, timezone

from kuku.api import Episode
from kuku.logic import cutoff, expires_at, is_expired, looks_like_full_mp3, select_new

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)


def ep(id, days_ago, premium=False, playable=True):
    return Episode(id, f"Osa {id}", NOW - timedelta(days=days_ago), premium, playable, 2800.0)


def test_select_new_keeps_free_unstored_recent_oldest_first():
    eps = [ep(5, 1), ep(4, 8), ep(3, 15, premium=True), ep(2, 22, playable=False), ep(1, 200)]
    assert [e.id for e in select_new(eps, stored_ids={5}, now=NOW)] == [4]


def test_select_new_orders_oldest_first():
    assert [e.id for e in select_new([ep(2, 1), ep(1, 8)], set(), NOW)] == [1, 2]


def test_expiry_is_182_days():
    published = NOW - timedelta(days=10)
    assert expires_at(published) == published + timedelta(days=182)
    assert cutoff(NOW) == NOW - timedelta(days=182)
    assert not is_expired(NOW - timedelta(days=181), NOW)
    assert is_expired(NOW - timedelta(days=183), NOW)


def test_looks_like_full_mp3():
    big = 2800 * 8000
    assert looks_like_full_mp3(b"ID3\x04", big, 2800)
    assert looks_like_full_mp3(b"\xff\xfb\x90\x00", big, 2800)
    assert not looks_like_full_mp3(b"<html", big, 2800)
    assert not looks_like_full_mp3(b"ID3\x04", 70 * 40000, 2800)  # ~1 min teaser
```

- [ ] **Step 2: Run** `python -m pytest tests/test_logic.py -q` → FAIL

- [ ] **Step 3: Implement**

```python
# kuku/logic.py
from datetime import timedelta

RETENTION = timedelta(days=182)
MIN_BYTES_PER_SECOND = 8000  # 64 kbit/s; tasuliste osade teaser on ~1 min


def cutoff(now):
    return now - RETENTION


def expires_at(published_at):
    return published_at + RETENTION


def is_expired(published_at, now):
    return published_at < cutoff(now)


def select_new(episodes, stored_ids, now):
    fresh = [e for e in episodes
             if not e.is_premium and e.is_playable
             and e.id not in stored_ids and not is_expired(e.published_at, now)]
    return sorted(fresh, key=lambda e: e.published_at)


def looks_like_full_mp3(head, size, duration_seconds):
    is_mp3 = head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    return is_mp3 and size >= duration_seconds * MIN_BYTES_PER_SECOND
```

- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit** `git add kuku/logic.py tests/test_logic.py && git commit -m "Osade valiku ja säilituse loogika"`

---

### Task 3: GitHub Releases ja issue klient

**Files:** Create `kuku/releases.py`, `tests/test_releases.py`

**Interfaces:**
- Produces: `GitHubClient(repo:str, token:str, session=None)` with
  - `get_or_create_release(tag:str, name:str) -> dict` (`id`, `upload_url`, `assets`)
  - `find_release(tag:str) -> dict | None`
  - `list_assets(release:dict) -> dict[str, dict]` nimi → `{id, browser_download_url}`
  - `upload_asset(release:dict, path:Path, name:str, label:str) -> dict` (`browser_download_url`)
  - `delete_asset(asset_id:int) -> None`
  - `delete_release(release:dict, tag:str) -> None` (kustutab ka tag'i)
  - `report_api_change(message:str) -> None` (uus issue sildiga `kuku-muutus` või kommentaar avatud issue'le)

- [ ] **Step 1: Failing tests** (fake session salvestab päringud)

```python
# tests/test_releases.py
from kuku.releases import GitHubClient


class Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self, responses):
        self.responses = responses  # list of (method, url_contains, Resp)
        self.calls = []
        self.headers = {}

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        for i, (m, part, resp) in enumerate(self.responses):
            if m == method and part in url:
                self.responses.pop(i)
                return resp
        raise AssertionError(f"ootamatu päring {method} {url}")


def test_get_or_create_release_creates_when_missing():
    s = FakeSession([("GET", "/releases/tags/saade-209", Resp(404)),
                     ("POST", "/releases", Resp(201, {"id": 1, "upload_url": "u{?name,label}", "assets": []}))])
    rel = GitHubClient("o/r", "t", s).get_or_create_release("saade-209", "Digitund")
    assert rel["id"] == 1
    assert s.calls[1][2]["json"]["tag_name"] == "saade-209"


def test_report_api_change_comments_on_open_issue():
    s = FakeSession([("GET", "/issues", Resp(200, [{"number": 7}])),
                     ("POST", "/issues/7/comments", Resp(201, {}))])
    GitHubClient("o/r", "t", s).report_api_change("puudub väli 'results'")
    assert "puudub väli" in s.calls[1][2]["json"]["body"]


def test_report_api_change_opens_issue_when_none():
    s = FakeSession([("GET", "/issues", Resp(200, [])),
                     ("POST", "/repos/o/r/issues", Resp(201, {}))])
    GitHubClient("o/r", "t", s).report_api_change("x")
    body = s.calls[1][2]["json"]
    assert body["labels"] == ["kuku-muutus"]
    assert "Kuku" in body["title"]
```

- [ ] **Step 2: Run** `python -m pytest tests/test_releases.py -q` → FAIL

- [ ] **Step 3: Implement**

```python
# kuku/releases.py
"""GitHub Releases (helifailide hoidla) ja issue'd (veateavitus)."""

import requests

API = "https://api.github.com"
LABEL = "kuku-muutus"


class GitHubClient:
    def __init__(self, repo, token, session=None):
        self.repo = repo
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _req(self, method, url, ok=(200, 201, 204), **kwargs):
        if url.startswith("/"):
            url = f"{API}/repos/{self.repo}{url}"
        resp = self.session.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
        if resp.status_code not in ok:
            resp.raise_for_status()
            raise RuntimeError(f"GitHub {method} {url}: HTTP {resp.status_code}")
        return resp

    def find_release(self, tag):
        resp = self._req("GET", f"/releases/tags/{tag}", ok=(200, 404))
        return None if resp.status_code == 404 else resp.json()

    def get_or_create_release(self, tag, name):
        release = self.find_release(tag)
        if release:
            return release
        return self._req("POST", "/releases", json={
            "tag_name": tag, "name": name,
            "body": f"Kuku saate „{name}“ salvestised (hoitakse 6 kuud).",
        }).json()

    def list_assets(self, release):
        assets, page = {}, 1
        while True:
            batch = self._req("GET", f"/releases/{release['id']}/assets",
                              params={"per_page": 100, "page": page}).json()
            for a in batch:
                assets[a["name"]] = {"id": a["id"], "browser_download_url": a["browser_download_url"]}
            if len(batch) < 100:
                return assets
            page += 1

    def upload_asset(self, release, path, name, label):
        url = release["upload_url"].split("{", 1)[0]
        with open(path, "rb") as f:
            return self._req("POST", url, params={"name": name, "label": label[:200]},
                             headers={"Content-Type": "audio/mpeg"}, data=f, timeout=600).json()

    def delete_asset(self, asset_id):
        self._req("DELETE", f"/releases/assets/{asset_id}", ok=(204, 404))

    def delete_release(self, release, tag):
        self._req("DELETE", f"/releases/{release['id']}", ok=(204, 404))
        self._req("DELETE", f"/git/refs/tags/{tag}", ok=(204, 404, 422))

    def report_api_change(self, message):
        body = (f"Automaatne kontroll leidis, et Kuku liides on muutunud:\n\n> {message}\n\n"
                "Salvestamine on peatunud, kuni kood on parandatud (`kuku/api.py`).")
        issues = self._req("GET", "/issues", params={"labels": LABEL, "state": "open"}).json()
        if issues:
            self._req("POST", f"/issues/{issues[0]['number']}/comments", json={"body": body})
        else:
            self._req("POST", "/issues", json={
                "title": "Kuku on midagi muutnud — kood vajab parandamist",
                "body": body, "labels": [LABEL]})
```

- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit** `git add kuku/releases.py tests/test_releases.py && git commit -m "GitHub Releases ja issue klient"`

---

### Task 4: Sync orkestreerija

**Files:** Create `kuku/sync.py`, `tests/test_sync.py`; create `site/data/{config,shows,catalog,library,status}.json`

**Interfaces:**
- Consumes: `KukuClient`, `KukuApiChanged`, `ShowNotFound`, `Show`, `Episode` (T1); logic (T2); `GitHubClient` (T3)
- Produces:
  - `sync(data_dir:Path, kuku, github, download, now:datetime) -> list[str]` — tagastab hoiatused; `download(url:str, dest:Path) -> None`
  - `run(data_dir:Path, kuku, github, download, now) -> int` — kutsub `sync`, kirjutab `status.json`, `KukuApiChanged` korral `github.report_api_change`; tagastab exit-koodi
  - `main()` — env `GITHUB_REPOSITORY`, `GITHUB_TOKEN`; `python -m kuku.sync`
- JSON kujud:
  - `shows.json`: `[{"id": 209, "name": "Digitund"}]`
  - `catalog.json`: `{"updated_at": iso, "shows": [{"id","name","description","image"}]}`
  - `library.json`: `{"shows": [{"id","name","episodes":[{"id","title","published_at","expires_at","duration_seconds","url"}]}]}` (osad uuemad eespool)
  - `status.json`: `{"ok": bool, "message": str, "checked_at": iso}`

- [ ] **Step 1: Failing tests** (fake'id mälus)

```python
# tests/test_sync.py
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
    def __init__(self):
        self.releases = {}  # tag -> {"id", "name", "assets": {name: {...}}}
        self.reports = []
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

    def upload_asset(self, release, path, name, label):
        asset = {"id": self._next, "browser_download_url": f"https://gh/{name}"}
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
    assert entry["expires_at"].startswith("2027-03-")
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
    with pytest.raises(KukuApiChanged, match="teaser|lühike"):
        sync(data, FakeKuku({209: [ep(2, 1)]}), gh, lambda u, d: d.write_bytes(b"ID3short"), NOW)
    assert gh.releases["saade-209"]["assets"] == {}


def test_failed_download_skips_episode_and_continues(data):
    gh = FakeGitHub()

    def flaky(url, dest):
        if "2.mp3" in url:
            raise OSError("ühendus katkes")
        dest.write_bytes(MP3)

    warnings = sync(data, FakeKuku({209: [ep(3, 1), ep(2, 8)]}), gh, flaky, NOW)
    assert list(gh.releases["saade-209"]["assets"]) == ["3.mp3"]
    assert any("2" in w for w in warnings)


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
```

- [ ] **Step 2: Run** `python -m pytest tests/test_sync.py -q` → FAIL

- [ ] **Step 3: Implement**

```python
# kuku/sync.py
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
            if not looks_like_full_mp3(head, dest.stat().st_size, episode.duration_seconds):
                raise KukuApiChanged(
                    f"osa {episode.id} fail on liiga lühike või pole MP3 "
                    f"({dest.stat().st_size} baiti, oodati ~{int(episode.duration_seconds)} s) — "
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
```

Algandmed:
- `site/data/config.json`: `{"repo": "mssaar/kuku-raadio"}`
- `site/data/shows.json`: `[]`
- `site/data/catalog.json`: `{"updated_at": null, "shows": []}`
- `site/data/library.json`: `{"shows": []}`
- `site/data/status.json`: `{"ok": true, "message": "", "checked_at": null}`

- [ ] **Step 4: Run** `python -m pytest -q` → kõik PASS
- [ ] **Step 5: Päris API kuivkäivitus** (ilma GitHubita): `python -c "from kuku.api import *; from datetime import *; c=KukuClient(); print(len(c.list_shows())); print([e.id for e in c.list_episodes(209, datetime.now(timezone.utc)-timedelta(days=182))][:3])"` → ~146 ja Digitunni osade id-d
- [ ] **Step 6: Commit** `git add kuku/sync.py tests/test_sync.py site/data && git commit -m "Sync: allalaadimine, säilitus, library ja status"`

---

### Task 5: JS teegid (krüpto, sessioon, otsing, GitHub)

**Files:** Create `site/lib/crypto.js`, `site/lib/session.js`, `site/lib/search.js`, `site/lib/github.js`, `tests_js/crypto.test.mjs`, `tests_js/session.test.mjs`, `tests_js/search.test.mjs`

**Interfaces:**
- Produces:
  - `encryptToken(token, password, iterations = 600000) -> Promise<{v,salt,iv,iterations,ciphertext}>`
  - `decryptToken(blob, password) -> Promise<string>`; vale parool → `Error` nimega `WrongPassword`
  - `saveSession(storage, token, now = Date.now())`, `loadSession(storage, now = Date.now()) -> string|null`, `clearSession(storage)`
  - `normalize(text) -> string`, `searchShows(shows, query, limit = 50) -> show[]`
  - `getFile(repo, path, token) -> Promise<{json, sha}|null>`, `putFile(repo, path, value, sha, token, message) -> Promise<sha>`

- [ ] **Step 1: Failing tests**

```js
// tests_js/crypto.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { encryptToken, decryptToken } from "../site/lib/crypto.js";

test("krüpteeri ja dekrüpteeri", async () => {
  const blob = await encryptToken("ghp_abc", "salasõna", 1000);
  assert.equal(blob.v, 1);
  assert.ok(!JSON.stringify(blob).includes("ghp_abc"));
  assert.equal(await decryptToken(blob, "salasõna"), "ghp_abc");
});

test("vale parool annab WrongPassword", async () => {
  const blob = await encryptToken("ghp_abc", "õige", 1000);
  await assert.rejects(decryptToken(blob, "vale"), { name: "WrongPassword" });
});

test("rikutud blob annab WrongPassword", async () => {
  await assert.rejects(decryptToken({ v: 1, salt: "x", iv: "y", iterations: 1000, ciphertext: "z" }, "p"),
    { name: "WrongPassword" });
});
```

```js
// tests_js/session.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { saveSession, loadSession, clearSession } from "../site/lib/session.js";

function mem() {
  const m = new Map();
  return { getItem: k => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k) };
}

test("sessioon kehtib aasta", () => {
  const s = mem(), now = Date.UTC(2026, 9, 2);
  saveSession(s, "tok", now);
  assert.equal(loadSession(s, now + 364 * 864e5), "tok");
  assert.equal(loadSession(s, now + 366 * 864e5), null);
});

test("väljalogimine ja katkine sisu", () => {
  const s = mem();
  saveSession(s, "tok");
  clearSession(s);
  assert.equal(loadSession(s), null);
  s.setItem("kuku.session", "{katki");
  assert.equal(loadSession(s), null);
});
```

```js
// tests_js/search.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { normalize, searchShows } from "../site/lib/search.js";

const shows = [
  { id: 1, name: "Digitund", description: "Tehnoloogia" },
  { id: 2, name: "Õiguse horisont", description: "" },
  { id: 3, name: "Kuku hommikuraadio", description: "digi uudised" },
];

test("normalize eemaldab täpid ja suurtähed", () => {
  assert.equal(normalize("Õiguse HÖRISONT"), "oiguse horisont");
});

test("nimi enne kirjeldust, täpitähed paindlikud", () => {
  assert.deepEqual(searchShows(shows, "digi").map(s => s.id), [1, 3]);
  assert.deepEqual(searchShows(shows, "oigus").map(s => s.id), [2]);
  assert.deepEqual(searchShows(shows, "  ").map(s => s.id), []);
});
```

- [ ] **Step 2: Run** `node --test tests_js/` → FAIL

- [ ] **Step 3: Implement**

```js
// site/lib/crypto.js
const enc = new TextEncoder();
const dec = new TextDecoder();
const b64 = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes)));
const unb64 = text => Uint8Array.from(atob(text), c => c.charCodeAt(0));

async function deriveKey(password, salt, iterations) {
  const base = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt, iterations },
    base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

export async function encryptToken(token, password, iterations = 600000) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(password, salt, iterations);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, enc.encode(token));
  return { v: 1, salt: b64(salt), iv: b64(iv), iterations, ciphertext: b64(ciphertext) };
}

export async function decryptToken(blob, password) {
  try {
    const key = await deriveKey(password, unb64(blob.salt), blob.iterations);
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(blob.iv) }, key, unb64(blob.ciphertext));
    return dec.decode(plain);
  } catch {
    const err = new Error("Vale parool");
    err.name = "WrongPassword";
    throw err;
  }
}
```

```js
// site/lib/session.js
const KEY = "kuku.session";
const YEAR_MS = 365 * 24 * 60 * 60 * 1000;

export function saveSession(storage, token, now = Date.now()) {
  storage.setItem(KEY, JSON.stringify({ token, expires: now + YEAR_MS }));
}

export function loadSession(storage, now = Date.now()) {
  try {
    const s = JSON.parse(storage.getItem(KEY));
    return s && typeof s.token === "string" && s.expires > now ? s.token : null;
  } catch {
    return null;
  }
}

export function clearSession(storage) {
  storage.removeItem(KEY);
}
```

```js
// site/lib/search.js
export function normalize(text) {
  return (text || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

export function searchShows(shows, query, limit = 50) {
  const words = normalize(query).split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const scored = [];
  for (const show of shows) {
    const name = normalize(show.name);
    const all = `${name} ${normalize(show.description)}`;
    if (!words.every(w => all.includes(w))) continue;
    const score = words.every(w => name.includes(w)) ? (name.startsWith(words[0]) ? 0 : 1) : 2;
    scored.push([score, show]);
  }
  scored.sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name, "et"));
  return scored.slice(0, limit).map(([, s]) => s);
}
```

```js
// site/lib/github.js
const API = "https://api.github.com";

function headers(token) {
  return { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json" };
}

function toBase64Utf8(text) {
  return btoa(String.fromCharCode(...new TextEncoder().encode(text)));
}

function fromBase64Utf8(b64) {
  return new TextDecoder().decode(Uint8Array.from(atob(b64.replace(/\n/g, "")), c => c.charCodeAt(0)));
}

export async function getFile(repo, path, token) {
  const resp = await fetch(`${API}/repos/${repo}/contents/${path}`, { headers: headers(token), cache: "no-store" });
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(`GitHub vastas ${resp.status}`);
  const data = await resp.json();
  return { json: JSON.parse(fromBase64Utf8(data.content)), sha: data.sha };
}

export async function putFile(repo, path, value, sha, token, message) {
  const body = { message, content: toBase64Utf8(JSON.stringify(value, null, 1) + "\n") };
  if (sha) body.sha = sha;
  const resp = await fetch(`${API}/repos/${repo}/contents/${path}`,
    { method: "PUT", headers: headers(token), body: JSON.stringify(body) });
  if (resp.status === 401 || resp.status === 403) throw new Error("GitHubi võti ei kehti või tal pole õigusi");
  if (resp.status === 409) throw new Error("Fail muutus vahepeal, proovi uuesti");
  if (!resp.ok) throw new Error(`GitHub vastas ${resp.status}`);
  return (await resp.json()).content.sha;
}
```

- [ ] **Step 4: Run** `node --test tests_js/` → PASS
- [ ] **Step 5: Commit** `git add site/lib tests_js && git commit -m "Lehe teegid: krüpto, sessioon, otsing, GitHub"`

---

### Task 6: Leht (UI)

**Files:** Create `site/index.html`, `site/style.css`, `site/app.js`

**Interfaces:**
- Consumes: kõik Task 5 ekspordid; `site/data/*.json` kujud (Task 4)

Enne koodi: lae `impeccable` oskus ja tee `shape` (isiklik raadioarhiiv; rahulik, loetav, mobiil; Kuku-neutraalne, mitte Kuku brändi imiteeriv). Kujunduslikud otsused tulevad sealt; funktsionaalsed nõuded allpool on kohustuslikud.

Vaated ja käitumine (`app.js`):
1. Laadimisel: `fetch("data/config.json"|"status.json"|"catalog.json"|"library.json", {cache:"no-store"})`, `auth.json` (404 → seadistamata).
2. `status.ok === false` → punane bänner kõigis vaadetes: „Kuku on midagi muutnud — salvestamine on peatunud ja kood vajab parandamist.“ + `status.message` + link repo issue'dele.
3. `auth.json` puudub → **Seadistus**: väljad „GitHubi võti“, „Parool“, „Parool uuesti“; paroolid peavad kattuma ja olema ≥ 12 märki; `encryptToken` → `putFile(repo,"site/data/auth.json",blob,null,token,"Seadista parool")` → `saveSession` → peavaade. Link juhendile (README).
4. Sessioon puudub → **Sisselogimine**: parool → `decryptToken(auth)`; `WrongPassword` → „Vale parool“ välja all; õnnestumisel `saveSession` → peavaade.
5. **Peavaade** (sisse logitud):
   - Päises „Logi välja“ (`clearSession` → sisselogimine) ja „Viimati kontrollitud: <checked_at kohalikus ajas>“.
   - **Otsing**: sisend, `searchShows(catalog.shows, q)`; iga tulemus: pilt (kui on), nimi, kirjeldus, nupp „Salvesta“ / „Salvestatud ✓“ (kui juba `shows.json`-is).
   - „Salvesta“: `getFile(shows.json)` → lisa `{id,name}` kui puudub → `putFile(..., "Lisa saade: <nimi>")`; nupp näitab „Lisan…“ ja vea korral teadet.
   - **Minu saated**: `shows.json` (API-st, värske) järjekorras nime järgi; iga saate all `library.json`-i osad: pealkiri, kuupäev (`et-EE`), kestus (min), „Kustub <kuupäev>“, `<audio controls preload="none" src=url>`. Saate juures „Eemalda“ (kinnitus `confirm("Eemaldada … ja kustutada selle salvestised?")`) → `putFile` ilma selle saateta.
   - Saade valitud, aga `library.json`-is veel osi pole → „Ootel — esimesed osad ilmuvad mõne minuti jooksul.“
   - `401/403` GitHubist → logi välja ja näita „GitHubi võti on aegunud — seadista uuesti“ (kustutab sessiooni; uue võtme jaoks link README juhendile).
6. Kõik tekstid eesti keeles, `lang="et"`, ilma väliste skriptideta.

- [ ] **Step 1:** impeccable `shape` → kujunduse suund kirja (lühidalt, vestlusesse)
- [ ] **Step 2:** kirjuta `index.html`, `style.css`, `app.js` ülaltoodud käitumise järgi
- [ ] **Step 3: Kohalik kontroll**: täida ajutiselt `site/data` päris sync'i väljundiga (Task 4 kuivkäivitus + käsitsi `library.json` ühe osaga, `url` = Kuku MP3 või kohalik fail), `python -m http.server -d site 8000`, kontrolli brauseris: seadistus → sisselogimine → otsing „digi“ → mängimine → väljalogimine → vale parool; mobiililaius 375px. Taasta `site/data` algväärtused.
- [ ] **Step 4:** impeccable `audit`/`polish`; paranda leitu
- [ ] **Step 5: Commit** `git add site && git commit -m "Veebileht: otsing, saadete valik, kuulamine, sisselogimine"`

---

### Task 7: Töövoog, README, avaldamine

**Files:** Create `.github/workflows/sync.yml`; Modify `README.md`, `.gitignore`

- [ ] **Step 1: Töövoog**

```yaml
# .github/workflows/sync.yml
name: Kuku sync

on:
  schedule:
    - cron: "17 */3 * * *"
  workflow_dispatch:
  push:
    branches: [main]
    paths: ["site/**", "kuku/**", ".github/workflows/sync.yml"]

concurrency:
  group: kuku-sync
  cancel-in-progress: false

permissions:
  contents: write
  issues: write
  pages: write
  id-token: write

jobs:
  sync:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python -m pytest -q
      - name: Sünkroniseeri Kuku
        id: sync
        continue-on-error: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python -m kuku.sync
      - name: Salvesta andmed
        if: always()
        run: |
          git config user.name "kuku-bot"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add site/data
          if ! git diff --cached --quiet; then
            git commit -m "Andmete uuendus"
            git pull --rebase
            git push
          fi
      - uses: actions/upload-pages-artifact@v3
        if: always()
        with:
          path: site
      - id: deploy
        if: always()
        uses: actions/deploy-pages@v4
      - name: Märgi sync'i viga
        if: steps.sync.outcome == 'failure'
        run: exit 1
```

- [ ] **Step 2: README** — eesti keeles: mis see on; seadistamine (1. Settings → Pages → Source: GitHub Actions; 2. Actions → Kuku sync → Run workflow; 3. GitHubi võti: Settings → Developer settings → Fine-grained tokens → Only select repositories: kuku-raadio → Permissions: Contents: Read and write → aegumine 1 aasta; 4. ava `https://mssaar.github.io/kuku-raadio/`, kleebi võti ja vali parool); kuidas teavitus töötab; piirangud (failid avalikud, Kuku API mitteametlik). `.gitignore` + `recordings/`.

- [ ] **Step 3:** `python -m pytest -q && node --test tests_js/` → kõik PASS
- [ ] **Step 4: Commit** `git add -A && git commit -m "Sync töövoog ja juhend"`
- [ ] **Step 5: Push** `git push` (kasutaja on lubanud)
- [ ] **Step 6:** Kasutaja lülitab Pages'i sisse (Settings → Pages → GitHub Actions) ja käivitab töövoo; kontrolli `gh`/veebist: töövoog roheline, release `saade-…` olemas pärast saate lisamist, leht avaneb, `<audio>` mängib ja kerib Releases'i failiga.
