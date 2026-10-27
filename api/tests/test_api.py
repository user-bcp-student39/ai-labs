import base64
import json
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Literal

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import main as api_main
from app import security
from app import upload_storage
from app.main import create_app


EndpointName = Literal["list_tasks", "create_task", "summary", "upload_requirement", "backend_health"]
ENDPOINT_NAMES: tuple[EndpointName, ...] = (
    "list_tasks",
    "create_task",
    "summary",
    "upload_requirement",
    "backend_health",
)
SQL_ENDPOINT_NAMES: tuple[EndpointName, ...] = ("list_tasks", "create_task", "summary")
TEST_ISSUER = "https://auth.example.test"
TEST_AUDIENCE = "workshop-api"
TEST_TOKEN_LIFETIME_SECONDS = 3600
TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEST_PUBLIC_JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(TEST_PRIVATE_KEY.public_key()))
TEST_PUBLIC_JWK.update({"kid": "api-test-key", "use": "sig", "alg": "RS256"})
LEGACY_TEST_SECRET = "WORKSHOP_SECRET_2026"


def token(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
    issuer: str = TEST_ISSUER,
    audience: str = TEST_AUDIENCE,
    private_key: rsa.RSAPrivateKey = TEST_PRIVATE_KEY,
    include_role: bool = True,
) -> str:
    expiration = expires_at if expires_at is not None else int(time.time()) + TEST_TOKEN_LIFETIME_SECONDS
    claims = {"sub": username, "iss": issuer, "aud": audience, "exp": expiration}
    if include_role:
        claims["role"] = role
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "api-test-key"})


def legacy_token(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
    secret: str = LEGACY_TEST_SECRET,
) -> str:
    expiration = expires_at if expires_at is not None else int(time.time()) + TEST_TOKEN_LIFETIME_SECONDS
    raw = f"{username}|{role}|{expiration}|{secret}"
    return base64.b64encode(raw.encode()).decode()


class LocalJwksHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        response_body = json.dumps({"keys": [TEST_PUBLIC_JWK]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(autouse=True)
def configure_local_jwks(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalJwksHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    monkeypatch.setenv("jwt_iss", TEST_ISSUER)
    monkeypatch.setenv("jwt_aud", TEST_AUDIENCE)
    monkeypatch.setenv("jwks_endpoint", f"http://127.0.0.1:{server.server_port}/jwks")
    yield
    server.shutdown()
    server_thread.join()
    server.server_close()


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def request_endpoint(
    client: TestClient,
    endpoint: EndpointName,
    request_headers: dict[str, str],
) -> httpx.Response:
    if endpoint == "list_tasks":
        return client.get("/api/tasks", headers=request_headers)
    if endpoint == "create_task":
        return client.post(
            "/api/tasks",
            headers=request_headers,
            json={
                "title": "Contract task",
                "description": "Fictional test data",
                "status": "TODO",
                "priority": "MEDIUM",
            },
        )
    if endpoint == "summary":
        return client.get("/api/summary", headers=request_headers)
    if endpoint == "upload_requirement":
        return client.post(
            "/api/requirements",
            headers=request_headers,
            files={"file": ("requirements.txt", b"Fictional requirements", "text/plain")},
        )
    return client.get("/api/backend-health", headers=request_headers)


class StubHealthResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.data = body


def install_health_response(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    body: bytes,
) -> list[tuple[str, str, float]]:
    calls: list[tuple[str, str, float]] = []
    upstream_response = StubHealthResponse(status, body)

    class StubPoolManager:
        def request(self, method: str, url: str, timeout: float) -> StubHealthResponse:
            calls.append((method, url, timeout))
            return upstream_response

    def create_pool_manager() -> StubPoolManager:
        return StubPoolManager()

    monkeypatch.setattr(api_main.urllib3, "PoolManager", create_pool_manager)
    return calls


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_returns_summary_for_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/summary", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    file_content = b"Login must be accessible"
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", file_content, "text/plain")},
        )
    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements.txt",
        "storedAt": "requirements.txt",
        "size": len(file_content),
    }
    assert (upload_dir / "requirements.txt").read_bytes() == file_content


@pytest.mark.parametrize("filename", ["../outside.txt", r"..\nested\outside.txt", r"C:\incoming\outside.txt"])
def test_normalizes_upload_filename_without_writing_outside_upload_dir(tmp_path: Path, filename: str) -> None:
    upload_dir = tmp_path / "uploads"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_bytes(b"Preserve existing file")
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))

    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": (filename, b"Safe content", "text/plain")},
        )

    assert response.status_code == 201
    assert response.json()["fileName"] == "outside.txt"
    assert response.json()["storedAt"] == "outside.txt"
    assert (upload_dir / "outside.txt").read_bytes() == b"Safe content"
    assert outside_file.read_bytes() == b"Preserve existing file"


@pytest.mark.parametrize("filename", ["requirements.txt", "notes.md", "data.json", "UPPER.TXT"])
def test_accepts_allowed_upload_extensions(tmp_path: Path, filename: str) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": (filename, b"Allowed content", "application/octet-stream")},
        )

    assert response.status_code == 201
    assert (upload_dir / filename).read_bytes() == b"Allowed content"


def test_rejects_disallowed_upload_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.csv", b"Not allowed", "text/csv")},
        )

    assert response.status_code == 400
    assert list(upload_dir.iterdir()) == []


def test_accepts_upload_at_maximum_size(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    content = b"x" * (5 * 1024 * 1024)
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("maximum.txt", content, "text/plain")},
        )

    assert response.status_code == 201
    assert response.json()["size"] == len(content)
    assert (upload_dir / "maximum.txt").stat().st_size == len(content)


def test_rejects_upload_over_maximum_size_without_leaving_partial_file(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    content = b"x" * (5 * 1024 * 1024 + 1)
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("oversized.txt", content, "text/plain")},
        )

    assert response.status_code == 413
    assert list(upload_dir.iterdir()) == []


def test_rejects_duplicate_upload_name_without_overwriting_existing_file(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        original = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("duplicate.txt", b"Original", "text/plain")},
        )
        duplicate = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("duplicate.txt", b"Replacement", "text/plain")},
        )

    assert original.status_code == 201
    assert duplicate.status_code == 409
    assert (upload_dir / "duplicate.txt").read_bytes() == b"Original"
    assert list(upload_dir.glob(".upload-*.tmp")) == []


def test_rejects_expired_legacy_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    expired_headers = {"Authorization": f"Bearer {legacy_token(expires_at=int(time.time()) - 1)}"}

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=expired_headers)

    assert response.status_code == 401


def test_rejects_wrong_legacy_secret(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    invalid_headers = {"Authorization": f"Bearer {legacy_token(secret='fictional-wrong-secret')}"}

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=invalid_headers)

    assert response.status_code == 401


def test_accepts_valid_rs256_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_rejects_legacy_token_format(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    legacy_headers = {"Authorization": f"Bearer {legacy_token()}"}

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=legacy_headers)

    assert response.status_code == 401


def test_rejects_jwt_with_invalid_signature(tmp_path: Path) -> None:
    invalid_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    invalid_headers = {"Authorization": f"Bearer {token(private_key=invalid_key)}"}

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=invalid_headers)

    assert response.status_code == 401


def test_rejects_expired_rs256_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    expired_headers = {"Authorization": f"Bearer {token(expires_at=int(time.time()) - 1)}"}

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=expired_headers)

    assert response.status_code == 401


def test_rejects_jwt_with_wrong_issuer_or_audience(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    invalid_issuer_headers = {"Authorization": f"Bearer {token(issuer='https://wrong.example.test')}"}
    invalid_audience_headers = {"Authorization": f"Bearer {token(audience='wrong-api')}"}

    with TestClient(app) as client:
        issuer_response = client.get("/api/tasks", headers=invalid_issuer_headers)
        audience_response = client.get("/api/tasks", headers=invalid_audience_headers)

    assert issuer_response.status_code == 401
    assert audience_response.status_code == 401


def test_rejects_jwt_without_required_role_claim(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    token_headers = {"Authorization": f"Bearer {token(include_role=False)}"}

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=token_headers)

    assert response.status_code == 401


def test_returns_generic_error_when_jwt_configuration_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("jwt_iss")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 503
    assert response.json()["detail"] == "Token verification is not configured"


def test_returns_generic_error_when_jwks_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class UnavailableJwksClient:
        def get_signing_key_from_jwt(self, token_value: str) -> None:
            raise jwt.PyJWKClientConnectionError("fictional upstream detail")

    def unavailable_jwks_client(endpoint: str) -> UnavailableJwksClient:
        return UnavailableJwksClient()

    monkeypatch.setattr(security, "get_jwks_client", unavailable_jwks_client)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 503
    assert response.json()["detail"] == "Token verification is unavailable"


def test_rejects_cross_owner_task_reads_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    student_headers = {"Authorization": f"Bearer {token('student', 'STUDENT')}"}
    with TestClient(app) as client:
        task_response = client.get("/api/tasks", params={"owner": "trainer"}, headers=student_headers)
        summary_response = client.get("/api/summary", params={"owner": "trainer"}, headers=student_headers)

    assert task_response.status_code == 403
    assert task_response.json() == {"detail": "Not authorized for requested owner"}
    assert summary_response.status_code == 403
    assert summary_response.json() == {"detail": "Not authorized for requested owner"}


def test_rejects_cross_owner_task_creation(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    student_headers = {"Authorization": f"Bearer {token('student', 'STUDENT')}"}
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=student_headers,
            json={
                "title": "Trainer task",
                "description": "Fictional characterization data",
                "owner": "trainer",
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized for requested owner"}


def test_allows_matching_owner_for_task_operations(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    student_headers = {"Authorization": f"Bearer {token('student', 'STUDENT')}"}
    with TestClient(app) as client:
        task_response = client.get("/api/tasks", params={"owner": "student"}, headers=student_headers)
        summary_response = client.get("/api/summary", params={"owner": "student"}, headers=student_headers)
        create_response = client.post(
            "/api/tasks",
            headers=student_headers,
            json={
                "title": "Student task",
                "description": "Fictional characterization data",
                "owner": "student",
            },
        )

    assert task_response.status_code == 200
    assert all(task["owner"] == "student" for task in task_response.json())
    assert summary_response.status_code == 200
    assert summary_response.json()["owner"] == "student"
    assert create_response.status_code == 201
    assert create_response.json()["owner"] == "student"


def test_binds_quoted_owner_filters(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    quoted_owner = "student'"
    app.state.connection.execute(
        "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))",
        ("Quoted owner task", "Fictional characterization data", "TODO", quoted_owner, "LOW"),
    )
    app.state.connection.commit()
    owner_headers = {"Authorization": f"Bearer {token(quoted_owner, 'STUDENT')}"}

    with TestClient(app, raise_server_exceptions=False) as client:
        task_response = client.get("/api/tasks", headers=owner_headers)
        summary_response = client.get("/api/summary", headers=owner_headers)

    assert task_response.status_code == 200
    assert [task["title"] for task in task_response.json()] == ["Quoted owner task"]
    assert summary_response.status_code == 200
    assert summary_response.json()["owner"] == quoted_owner
    assert summary_response.json()["total"] == 1


def test_binds_quoted_task_values(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    student_headers = {"Authorization": f"Bearer {token('student', 'STUDENT')}"}

    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=student_headers,
            json={
                "title": "Owner's notes",
                "description": "Fictional characterization data",
            },
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Owner's notes"
    assert response.json()["owner"] == "student"


@pytest.mark.parametrize("endpoint", ENDPOINT_NAMES)
@pytest.mark.parametrize(
    "request_headers",
    [{}, {"Authorization": "Bearer invalid"}],
    ids=["missing-header", "invalid-token"],
)
def test_every_endpoint_rejects_missing_or_invalid_authentication(
    tmp_path: Path,
    endpoint: EndpointName,
    request_headers: dict[str, str],
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, endpoint, request_headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize("endpoint", ENDPOINT_NAMES)
def test_every_endpoint_returns_503_when_jwt_configuration_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: EndpointName,
) -> None:
    monkeypatch.delenv("jwt_iss")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, endpoint, headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Token verification is not configured"}


@pytest.mark.parametrize("endpoint", ENDPOINT_NAMES)
def test_every_endpoint_returns_503_when_jwks_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: EndpointName,
) -> None:
    class UnavailableJwksClient:
        def get_signing_key_from_jwt(self, token_value: str) -> None:
            raise jwt.PyJWKClientConnectionError("fictional local JWKS failure")

    def unavailable_jwks_client(endpoint_url: str) -> UnavailableJwksClient:
        return UnavailableJwksClient()

    monkeypatch.setattr(security, "get_jwks_client", unavailable_jwks_client)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, endpoint, headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Token verification is unavailable"}


def test_lists_empty_task_collection(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DELETE FROM tasks WHERE owner = ?", ("student",))
    app.state.connection.commit()
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert response.json() == []


def test_creates_task_from_empty_json_object(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})
    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


def test_create_task_rejects_missing_or_non_object_json_body(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        missing_body = client.post("/api/tasks", headers=headers())
        non_object_body = client.post("/api/tasks", headers=headers(), json=[])
    assert missing_body.status_code == 422
    assert missing_body.json()["detail"][0]["loc"] == ["body"]
    assert non_object_body.status_code == 422
    assert non_object_body.json()["detail"][0]["type"] == "dict_type"


def test_returns_empty_summary_for_owner_without_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DELETE FROM tasks WHERE owner = ?", ("student",))
    app.state.connection.commit()
    with TestClient(app) as client:
        response = client.get("/api/summary", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_uploads_empty_file(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("empty.txt", b"", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == 0
    assert (upload_dir / "empty.txt").read_bytes() == b""


def test_upload_requires_file_part(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_returns_500_when_file_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingTemporaryFile:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.path.touch()

        @property
        def name(self) -> str:
            return str(self.path)

        def __enter__(self) -> "FailingTemporaryFile":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def write(self, _content: bytes) -> int:
            raise OSError("fictional local write failure")

    def fail_temporary_file(*, dir: Path, **_: object) -> FailingTemporaryFile:
        return FailingTemporaryFile(dir / ".upload-failure.tmp")

    monkeypatch.setattr(upload_storage, "NamedTemporaryFile", fail_temporary_file)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Fictional content", "text/plain")},
        )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert list((tmp_path / "uploads").iterdir()) == []


@pytest.mark.parametrize("endpoint", SQL_ENDPOINT_NAMES)
def test_task_endpoints_return_500_for_sqlite_errors(
    tmp_path: Path,
    endpoint: EndpointName,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DROP TABLE tasks")
    app.state.connection.commit()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = request_endpoint(client, endpoint, headers())
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_backend_health_passes_through_upstream_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = install_health_response(monkeypatch, 200, b'{"status":"UP"}')
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://auth.example.test/q/health")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '{"status":"UP"}',
    }
    assert calls == [("GET", "http://auth.example.test/q/health", 3.0)]


def test_backend_health_keeps_outer_200_for_upstream_error_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_health_response(monkeypatch, 503, b"unavailable")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json()["status"] == 503
    assert response.json()["body"] == "unavailable"


def test_backend_health_encodes_upstream_exception_as_status_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedPoolManager:
        def request(self, method: str, url: str, timeout: float) -> StubHealthResponse:
            raise RuntimeError("fictional local connection failure")

    def create_failed_pool_manager() -> FailedPoolManager:
        return FailedPoolManager()

    monkeypatch.setattr(api_main.urllib3, "PoolManager", create_failed_pool_manager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "fictional local connection failure",
    }


def test_backend_health_returns_500_for_error_before_upstream_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_getenv = api_main.os.getenv

    def fail_auth_health_setting(name: str, default: str | None = None) -> str | None:
        if name == "AUTH_HEALTH_URL":
            raise RuntimeError("fictional local configuration failure")
        return original_getenv(name, default)

    monkeypatch.setattr(api_main.os, "getenv", fail_auth_health_setting)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
