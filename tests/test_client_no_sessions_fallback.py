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


class RecordingSession:
    def __init__(self, response):
        self.response = response
        self.urls = []

    def request(self, method, url, **kwargs):
        self.urls.append(url)
        return self.response


def test_send_message_never_calls_plural_sessions_route():
    client = OpenCodeClient("http://opencode.test")
    client.session = RecordingSession(_response("not found", status=404))

    with pytest.raises(OpenCodeError):
        client.send_message("ses", "hello")

    assert client.session.urls == ["http://opencode.test/session/ses/message"]


def test_html_response_has_clear_api_route_error():
    client = OpenCodeClient("http://opencode.test")
    client.session = RecordingSession(_response("<html></html>", "text/html"))

    with pytest.raises(OpenCodeError, match="OpenCode returned HTML, likely hit the web frontend route instead of API route"):
        client.send_message("ses", "hello")
