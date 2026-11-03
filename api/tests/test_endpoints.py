import base64
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

SECRET = "WORKSHOP_SECRET_2026"
ONE_HOUR_SECONDS = 3600
UNREACHABLE_HEALTH_URL = "http://127.0.0.1:9/q/health"
OVERSIZED_PROBE_BYTES = 10 * 1024 * 1024
SEEDED_STUDENT_TITLES = ["Refactor login", "Review API"]
TASK_FIELDS = {"id", "title", "description", "status", "owner", "priority", "createdAt"}
SUMMARY_FIELDS = {"owner", "total", "byStatus", "highPriorityOpen"}
UPLOAD_FIELDS = {"owner", "fileName", "storedAt", "size"}
REASON_H_API_02 = "H-API-02 pendiente: el cliente elige el owner"
REASON_H_API_04 = "H-API-04 pendiente: falta validacion de carga"


def legacy_token(username: str = "student", expires_at: int | None = None, secret: str = SECRET) -> str:
    expiry = expires_at if expires_at is not None else int(time.time()) + ONE_HOUR_SECONDS
    return base64.b64encode(f"{username}|STUDENT|{expiry}|{secret}".encode()).decode()


def auth(username: str = "student") -> dict[str, str]:
    return {"Authorization": f"Bearer {legacy_token(username)}"}


class _HealthStub(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b'{"status":"UP"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def health_stub() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _HealthStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/q/health"
    finally:
        server.shutdown()
        server.server_close()


PROTECTED_REQUESTS: list[tuple[str, str, dict[str, Any]]] = [
    ("GET", "/api/tasks", {}),
    ("POST", "/api/tasks", {"json": {"title": "t"}}),
    ("GET", "/api/summary", {}),
    ("POST", "/api/requirements", {"files": {"file": ("a.txt", b"x", "text/plain")}}),
    ("GET", "/api/backend-health", {}),
]

INVALID_AUTH_HEADERS: list[dict[str, str]] = [
    {},
    {"Authorization": f"Bearer {legacy_token(expires_at=0)}"},
    {"Authorization": f"Bearer {legacy_token(secret='SECRETO_FICTICIO')}"},
    {"Authorization": "Bearer abc"},
]


@pytest.mark.parametrize("method,url,options", PROTECTED_REQUESTS)
@pytest.mark.parametrize("headers", INVALID_AUTH_HEADERS)
def test_protected_endpoints_return_401_for_invalid_token(
    client: TestClient, method: str, url: str, options: dict[str, Any], headers: dict[str, str]
) -> None:
    response = client.request(method, url, headers=headers, **options)
    assert response.status_code == 401
    assert response.json()["detail"].startswith("Invalid token: ")


# GET /api/tasks
def test_list_returns_seeded_tasks_for_token_owner(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth())
    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == SEEDED_STUDENT_TITLES


def test_list_with_own_owner_query_returns_same_tasks(client: TestClient) -> None:
    response = client.get("/api/tasks", params={"owner": "student"}, headers=auth())
    assert [task["title"] for task in response.json()] == SEEDED_STUDENT_TITLES


def test_list_items_have_contract_fields(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth())
    assert all(set(task) == TASK_FIELDS for task in response.json())


def test_list_is_ordered_by_id(client: TestClient) -> None:
    ids = [task["id"] for task in client.get("/api/tasks", headers=auth()).json()]
    assert ids == sorted(ids)


def test_list_returns_empty_array_when_owner_has_no_tasks(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth("nadie"))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.xfail(strict=True, reason=REASON_H_API_02)
def test_list_user_cannot_read_other_owner_tasks(client: TestClient) -> None:
    response = client.get("/api/tasks", params={"owner": "trainer"}, headers=auth())
    assert response.status_code == 403 or response.json() == []


# POST /api/tasks
def test_create_with_full_body_returns_201(client: TestClient) -> None:
    payload = {"title": "Nueva tarea", "description": "Detalle", "status": "TODO", "priority": "HIGH"}
    response = client.post("/api/tasks", headers=auth(), json=payload)
    body = response.json()
    assert response.status_code == 201
    assert set(body) == TASK_FIELDS
    assert (body["title"], body["description"], body["status"], body["priority"], body["owner"]) == (
        "Nueva tarea",
        "Detalle",
        "TODO",
        "HIGH",
        "student",
    )


def test_create_with_empty_payload_applies_defaults(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={})
    body = response.json()
    assert response.status_code == 201
    assert (body["title"], body["description"], body["status"], body["priority"], body["owner"]) == (
        "",
        "",
        "TODO",
        "MEDIUM",
        "student",
    )


def test_create_without_body_returns_422(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body"]


@pytest.mark.xfail(strict=True, reason=REASON_H_API_02)
def test_create_ignores_owner_sent_in_body(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "Ajena", "owner": "trainer"})
    assert response.status_code == 201
    assert response.json()["owner"] == "student"


# GET /api/summary
def test_summary_for_token_owner(client: TestClient) -> None:
    response = client.get("/api/summary", headers=auth())
    assert response.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_summary_for_owner_without_tasks_is_zero(client: TestClient) -> None:
    response = client.get("/api/summary", headers=auth("nadie"))
    assert response.json() == {"owner": "nadie", "total": 0, "byStatus": {}, "highPriorityOpen": 0}


def test_summary_excludes_done_and_archived_from_high_priority_open(client: TestClient) -> None:
    for status in ("TODO", "DONE", "ARCHIVED"):
        client.post("/api/tasks", headers=auth("tester"), json={"title": status, "status": status, "priority": "HIGH"})
    body = client.get("/api/summary", headers=auth("tester")).json()
    assert set(body) == SUMMARY_FIELDS
    assert (body["total"], body["highPriorityOpen"]) == (3, 1)


@pytest.mark.xfail(strict=True, reason=REASON_H_API_02)
def test_summary_user_cannot_read_other_owner(client: TestClient) -> None:
    response = client.get("/api/summary", params={"owner": "trainer"}, headers=auth())
    assert response.status_code == 403 or response.json().get("total") == 0


# POST /api/requirements
def test_upload_returns_201_with_contract_fields(client: TestClient, tmp_path: Path) -> None:
    content = b"Login debe ser accesible"
    response = client.post(
        "/api/requirements", headers=auth(), files={"file": ("requirements.txt", content, "text/plain")}
    )
    body = response.json()
    assert response.status_code == 201
    assert set(body) == UPLOAD_FIELDS
    assert (body["owner"], body["fileName"], body["size"]) == ("student", "requirements.txt", len(content))
    assert (tmp_path / "uploads" / "requirements.txt").read_bytes() == content


def test_upload_empty_file_is_stored_with_size_zero(client: TestClient) -> None:
    response = client.post("/api/requirements", headers=auth(), files={"file": ("vacio.txt", b"", "text/plain")})
    assert response.status_code == 201
    assert response.json()["size"] == 0


def test_upload_file_without_extension_is_accepted_as_observed(client: TestClient) -> None:
    # Caracterizacion del comportamiento actual: no hay validacion de extension (riesgo H-API-04).
    response = client.post("/api/requirements", headers=auth(), files={"file": ("LEEME", b"x", "text/plain")})
    assert response.status_code == 201


@pytest.mark.xfail(strict=True, reason=REASON_H_API_04)
def test_upload_rejects_oversized_file(client: TestClient) -> None:
    payload = b"x" * OVERSIZED_PROBE_BYTES
    response = client.post("/api/requirements", headers=auth(), files={"file": ("grande.txt", payload, "text/plain")})
    assert response.status_code == 413


@pytest.mark.xfail(strict=True, reason=REASON_H_API_04)
def test_upload_name_cannot_escape_upload_dir(client: TestClient, tmp_path: Path) -> None:
    client.post("/api/requirements", headers=auth(), files={"file": ("../escape.txt", b"x", "text/plain")})
    assert not (tmp_path / "escape.txt").exists()


def test_upload_without_file_returns_422(client: TestClient) -> None:
    response = client.post("/api/requirements", headers=auth())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


# GET /api/backend-health
def test_backend_health_reports_upstream_status(
    client: TestClient, health_stub: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", health_stub)
    response = client.get("/api/backend-health", headers=auth())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": '{"status":"UP"}'}


def test_backend_health_unreachable_returns_200_with_status_zero(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", UNREACHABLE_HEALTH_URL)
    body = client.get("/api/backend-health", headers=auth()).json()
    assert body["requestedBy"] == "student"
    assert body["status"] == 0
    assert body["body"] != ""
