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

    def _req(self, method, url, ok=(200, 201, 204), timeout=60, **kwargs):
        if url.startswith("/"):
            url = f"{API}/repos/{self.repo}{url}"
        resp = self.session.request(method, url, timeout=timeout, **kwargs)
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
