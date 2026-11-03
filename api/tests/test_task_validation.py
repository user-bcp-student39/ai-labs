from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.task_validation import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    TASK_PRIORITIES,
    TASK_STATUSES,
    TaskValidationError,
    validate_task_payload,
)
from test_endpoints import TASK_FIELDS, auth


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as test_client:
        yield test_client


def task_count(client: TestClient) -> int:
    return len(client.get("/api/tasks", headers=auth()).json())


def field_errors(response: Any) -> dict[str, str]:
    return {item["field"]: item["message"] for item in response.json()["detail"]}


# H-API-13 caracterizacion: lo que se preserva con valores validos.
def test_valid_task_keeps_201_and_contract_fields(client: TestClient) -> None:
    payload = {"title": "Nueva tarea", "description": "Detalle", "status": "TODO", "priority": "HIGH"}
    response = client.post("/api/tasks", headers=auth(), json=payload)
    assert response.status_code == 201
    assert set(response.json()) == TASK_FIELDS


def test_title_only_applies_defaults(client: TestClient) -> None:
    body = client.post("/api/tasks", headers=auth(), json={"title": "Solo titulo"}).json()
    assert (body["description"], body["status"], body["priority"], body["owner"]) == ("", "TODO", "MEDIUM", "student")


@pytest.mark.parametrize("status", sorted(TASK_STATUSES))
def test_every_allowed_status_is_accepted(client: TestClient, status: str) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "t", "status": status})
    assert response.status_code == 201
    assert response.json()["status"] == status


@pytest.mark.parametrize("priority", sorted(TASK_PRIORITIES))
def test_every_allowed_priority_is_accepted(client: TestClient, priority: str) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "t", "priority": priority})
    assert response.status_code == 201
    assert response.json()["priority"] == priority


def test_title_and_description_at_max_length_are_accepted(client: TestClient) -> None:
    payload = {"title": "t" * MAX_TITLE_LENGTH, "description": "d" * MAX_DESCRIPTION_LENGTH}
    assert client.post("/api/tasks", headers=auth(), json=payload).status_code == 201


def test_summary_counts_high_priority_open_after_validated_creates(client: TestClient) -> None:
    for status in ("TODO", "IN_PROGRESS", "DONE", "ARCHIVED"):
        client.post("/api/tasks", headers=auth("validador"), json={"title": status, "status": status, "priority": "HIGH"})
    body = client.get("/api/summary", headers=auth("validador")).json()
    assert (body["total"], body["highPriorityOpen"]) == (4, 2)


# H-API-13 correccion: entradas invalidas devuelven 400 y no crean filas.
@pytest.mark.parametrize(
    "payload,field",
    [
        ({}, "title"),
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"title": None}, "title"),
        ({"title": 123}, "title"),
        ({"title": ["a"]}, "title"),
        ({"title": "t" * (MAX_TITLE_LENGTH + 1)}, "title"),
        ({"title": "t", "description": None}, "description"),
        ({"title": "t", "description": 5}, "description"),
        ({"title": "t", "description": "d" * (MAX_DESCRIPTION_LENGTH + 1)}, "description"),
        ({"title": "t", "status": "x"}, "status"),
        ({"title": "t", "status": "todo"}, "status"),
        ({"title": "t", "status": None}, "status"),
        ({"title": "t", "status": 1}, "status"),
        ({"title": "t", "priority": "high"}, "priority"),
        ({"title": "t", "priority": "URGENT"}, "priority"),
        ({"title": "t", "priority": None}, "priority"),
    ],
)
def test_invalid_payload_returns_400_and_creates_nothing(client: TestClient, payload: dict[str, Any], field: str) -> None:
    before = task_count(client)
    response = client.post("/api/tasks", headers=auth(), json=payload)
    assert response.status_code == 400
    assert field in field_errors(response)
    assert task_count(client) == before


def test_invalid_payload_reports_every_invalid_field(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "", "status": "x", "priority": "y"})
    assert set(field_errors(response)) == {"title", "status", "priority"}


def test_error_message_does_not_echo_the_received_value(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "t", "status": "VALOR_SENSIBLE_123"})
    assert "VALOR_SENSIBLE_123" not in response.text


def test_missing_body_still_returns_422(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_invalid_token_is_checked_before_payload_validation(client: TestClient) -> None:
    response = client.post("/api/tasks", headers={"Authorization": "Bearer x"}, json={})
    assert response.status_code == 401


def test_owner_in_body_is_still_accepted_while_h_api_02_is_pending(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "t", "owner": "trainer"})
    assert response.status_code == 201


def test_validate_task_payload_returns_defaults() -> None:
    validated = validate_task_payload({"title": "t"})
    assert (validated.title, validated.description, validated.status, validated.priority) == ("t", "", "TODO", "MEDIUM")


def test_validate_task_payload_raises_with_all_errors() -> None:
    with pytest.raises(TaskValidationError) as raised:
        validate_task_payload({"status": "x"})
    assert {item["field"] for item in raised.value.errors} == {"title", "status"}
