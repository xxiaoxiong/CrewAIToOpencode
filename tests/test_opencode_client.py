import pytest
import requests

from src.opencode.client import OpenCodeClient
from src.opencode.errors import OpenCodeError


def _response(body: str, content_type: str = "application/json", status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = body.encode("utf-8")
    response.headers["content-type"] = content_type
    return response


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.paths = []

    def request(self, method, url, **kwargs):
        self.paths.append(url.rsplit("/", 1)[-1])
        return self.responses.pop(0)


def test_agents_uses_json_endpoint_before_spa_fallback():
    client = OpenCodeClient("http://opencode.test")
    client.session = FakeSession([_response('[{"name":"build"}]')])

    result = client.agents()

    assert result == {"data": [{"name": "build"}]}
    assert client.session.paths == ["agent"]


def test_request_skips_html_fallback_when_trying_candidates():
    client = OpenCodeClient("http://opencode.test")
    client.session = FakeSession(
        [
            _response("<!doctype html><title>OpenCode</title>", "text/html"),
            _response('{"ok":true}'),
        ]
    )

    result = client._request("GET", ["/missing", "/real"])

    assert result == {"ok": True}


def test_request_rejects_single_html_fallback():
    client = OpenCodeClient("http://opencode.test")
    client.session = FakeSession([_response("<html></html>", "text/html")])

    with pytest.raises(OpenCodeError, match="returned HTML instead of JSON"):
        client._request("GET", "/missing")
