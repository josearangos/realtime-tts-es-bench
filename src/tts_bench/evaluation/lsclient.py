"""Minimal stdlib REST client for Label Studio 1.23.x (endpoints verified in research R14)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request


class LSError(RuntimeError):
    """Label Studio answered with an error status."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class LSUnreachable(LSError):
    """Label Studio could not be reached (CLI exit code 3)."""


def _items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "tasks", "users", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


class LSClient:
    def __init__(self, url: str, token: str, timeout: float = 30.0, retries: int = 3, backoff: float = 0.5):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    # transport ----------------------------------------------------------
    def request(self, method: str, path: str, body=None, query: dict | None = None):
        url = self.url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Authorization": f"Token {self.token}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        last: Exception | None = None
        for attempt in range(self.retries):
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw.strip() else None
            except urllib.error.HTTPError as exc:  # server answered: do not retry
                detail = exc.read().decode("utf-8", "replace")[:300]
                raise LSError(f"{method} {path} -> HTTP {exc.code}: {detail}", exc.code) from None
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
                last = exc
                time.sleep(self.backoff * (attempt + 1))
        raise LSUnreachable(f"{method} {url}: {last}")

    # endpoints ----------------------------------------------------------
    def health(self) -> bool:
        try:
            r = self.request("GET", "/health")
            return isinstance(r, dict) and r.get("status") == "UP"
        except LSError:
            return False

    def wait_healthy(self, timeout: float = 120.0, interval: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        quick = LSClient(self.url, self.token, timeout=5.0, retries=1, backoff=0)
        while True:
            if quick.health():
                return
            if time.monotonic() >= deadline:
                raise LSUnreachable(f"Label Studio at {self.url} not healthy after {timeout:.0f}s")
            time.sleep(interval)

    def list_projects(self) -> list[dict]:
        return _items(self.request("GET", "/api/projects", query={"page_size": 1000}))

    def create_project(self, title: str, label_config: str, instructions: str, sampling: str,
                       description: str = "") -> dict:
        return self.request("POST", "/api/projects", {
            "title": title, "label_config": label_config, "expert_instruction": instructions,
            "show_instruction": True, "sampling": sampling, "description": description,
        })

    def list_tasks(self, project_id: int) -> list[dict]:
        # Data Manager endpoint: /api/projects/{id}/tasks/ answers 404 for an empty project (verified on 1.23)
        out, page = [], 1
        while True:
            chunk = _items(self.request("GET", "/api/tasks",
                                        query={"project": project_id, "page": page, "page_size": 100, "fields": "all"}))
            out.extend(chunk)
            if len(chunk) < 100:
                return out
            page += 1

    def import_tasks(self, project_id: int, tasks: list[dict]) -> None:
        for i in range(0, len(tasks), 200):
            self.request("POST", f"/api/projects/{project_id}/import", [{"data": t} for t in tasks[i:i + 200]],
                         query={"commit_to_project": "true"})

    def delete_task(self, task_id: int) -> None:
        self.request("DELETE", f"/api/tasks/{task_id}")

    def list_storages(self, project_id: int) -> list[dict]:
        return _items(self.request("GET", "/api/storages/localfiles/", query={"project": project_id}))

    def create_local_storage(self, project_id: int, path: str, title: str) -> dict:
        return self.request("POST", "/api/storages/localfiles/", {
            "project": project_id, "title": title, "path": path, "use_blob_urls": False,
        })

    def list_users(self) -> list[dict]:
        return _items(self.request("GET", "/api/users/"))

    def create_user(self, email: str, password: str) -> dict:
        # 1.23 requires `username` (verified on a running server); the pseudonym is the local part of the email
        return self.request("POST", "/api/users/", {"username": email.split("@")[0], "email": email,
                                                    "password": password})

    def export_annotations(self, project_id: int) -> list[dict]:
        r = self.request("GET", f"/api/projects/{project_id}/export",
                         query={"exportType": "JSON", "download_all_tasks": "true"})
        return r if isinstance(r, list) else _items(r)
