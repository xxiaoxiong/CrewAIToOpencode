from __future__ import annotations

from typing import Any, Iterable

import requests
from requests.auth import HTTPBasicAuth

from src.opencode.errors import OpenCodeError


def _is_html_fallback(response: requests.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    text = response.text.lstrip().lower()
    return "text/html" in content_type or text.startswith("<!doctype html") or text.startswith("<html")


class OpenCodeClient:
    def __init__(
        self,
        base_url: str,
        username: str = "",
        password: str = "",
        provider_id: str = "",
        model_id: str = "",
        timeout: int = 600,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.provider_id = provider_id
        self.model_id = model_id
        self.timeout = timeout
        self.session = requests.Session()
        if username or password:
            self.session.auth = HTTPBasicAuth(username, password)

    @classmethod
    def from_project_config(cls, project_config: dict[str, Any]) -> "OpenCodeClient":
        return cls(
            base_url=project_config.get("opencode_base_url", "http://127.0.0.1:4096"),
            username=project_config.get("opencode_username", ""),
            password=project_config.get("opencode_password", ""),
            provider_id=project_config.get("opencode_provider_id", ""),
            model_id=project_config.get("opencode_model_id", ""),
            timeout=int((project_config.get("opencode_timeouts", {}) or {}).get("default", 600)),
        )

    def _request(
        self,
        method: str,
        paths: str | Iterable[str],
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        candidates = [paths] if isinstance(paths, str) else list(paths)
        errors: list[str] = []
        request_timeout = int(timeout or self.timeout)

        for path in candidates:
            url = f"{self.base_url}{path}"
            try:
                response = self.session.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                    timeout=request_timeout,
                )
            except requests.Timeout as exc:
                errors.append(f"{method} {path}: timed out after {request_timeout} seconds: {exc}")
                continue
            except requests.RequestException as exc:
                errors.append(f"{method} {path}: {exc}")
                continue

            if response.status_code == 404 and len(candidates) > 1:
                errors.append(f"{method} {path}: 404")
                continue

            if not response.ok:
                text = response.text[:2000]
                raise OpenCodeError(f"{method} {path} failed: HTTP {response.status_code}: {text}")

            if not response.text.strip():
                return {}
            try:
                payload = response.json()
            except ValueError:
                if _is_html_fallback(response):
                    errors.append(
                        f"{method} {path}: OpenCode returned HTML, likely hit web frontend route instead of API route."
                    )
                    if len(candidates) > 1:
                        continue
                    raise OpenCodeError(errors[-1])
                return {"raw": response.text}
            return payload if isinstance(payload, dict) else {"data": payload}

        raise OpenCodeError("; ".join(errors) or f"{method} request failed")

    def health(self) -> dict[str, Any]:
        return self._request("GET", ["/global/health", "/health"])

    def current_path(self) -> dict[str, Any]:
        return self._request("GET", ["/path", "/global/path"])

    def vcs(self) -> dict[str, Any]:
        return self._request("GET", ["/vcs", "/global/vcs"])

    def agents(self) -> dict[str, Any]:
        return self._request("GET", ["/agent", "/agents"])

    def create_session(self, title: str) -> dict[str, Any]:
        return self._request("POST", "/session", json_body={"title": title})

    def send_message(
        self,
        session_id: str,
        text: str,
        agent: str = "build",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "agent": agent,
            "parts": [{"type": "text", "text": text}],
        }
        if self.provider_id and self.model_id:
            body["model"] = {"providerID": self.provider_id, "modelID": self.model_id}
        return self._request(
            "POST",
            f"/session/{session_id}/message",
            json_body=body,
            timeout=timeout,
        )

    def list_messages(self, session_id: str, limit: int = 20) -> dict[str, Any]:
        return self._request(
            "GET",
            [f"/session/{session_id}/message", f"/session/{session_id}/messages"],
            params={"limit": limit},
        )

    def get_diff(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/session/{session_id}/diff")

    def file_status(self) -> dict[str, Any]:
        return self._request("GET", ["/file/status", "/files/status"])

    def abort(self, session_id: str) -> dict[str, Any]:
        return self._request("POST", f"/session/{session_id}/abort")
