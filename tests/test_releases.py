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


def test_list_assets_maps_names():
    s = FakeSession([("GET", "/releases/1/assets", Resp(200, [
        {"id": 5, "name": "77.mp3", "browser_download_url": "https://gh/77.mp3"}]))])
    assets = GitHubClient("o/r", "t", s).list_assets({"id": 1})
    assert assets == {"77.mp3": {"id": 5, "browser_download_url": "https://gh/77.mp3"}}


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
