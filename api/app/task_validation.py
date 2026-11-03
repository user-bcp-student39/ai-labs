from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TASK_STATUSES = frozenset({"TODO", "IN_PROGRESS", "DONE", "ARCHIVED"})
TASK_PRIORITIES = frozenset({"HIGH", "MEDIUM", "LOW"})
DEFAULT_STATUS = "TODO"
DEFAULT_PRIORITY = "MEDIUM"
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000


class TaskValidationError(Exception):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("invalid task payload")
        self.errors = errors


@dataclass(frozen=True)
class ValidatedTask:
    title: str
    description: str
    status: str
    priority: str


def validate_task_payload(payload: dict[str, Any]) -> ValidatedTask:
    errors: list[dict[str, str]] = []
    title = _required_text(payload, "title", MAX_TITLE_LENGTH, errors)
    description = _optional_text(payload, "description", "", MAX_DESCRIPTION_LENGTH, errors)
    status = _allowed_value(payload, "status", DEFAULT_STATUS, TASK_STATUSES, errors)
    priority = _allowed_value(payload, "priority", DEFAULT_PRIORITY, TASK_PRIORITIES, errors)
    if errors:
        raise TaskValidationError(errors)
    return ValidatedTask(title, description, status, priority)


def _required_text(payload: dict[str, Any], field: str, max_length: int, errors: list[dict[str, str]]) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(_error(field, "must be a non-empty string"))
        return ""
    return _within_limit(value, field, max_length, errors)


def _optional_text(
    payload: dict[str, Any], field: str, default: str, max_length: int, errors: list[dict[str, str]]
) -> str:
    if field not in payload:
        return default
    value = payload[field]
    if not isinstance(value, str):
        errors.append(_error(field, "must be a string"))
        return default
    return _within_limit(value, field, max_length, errors)


def _allowed_value(
    payload: dict[str, Any], field: str, default: str, allowed: frozenset[str], errors: list[dict[str, str]]
) -> str:
    if field not in payload:
        return default
    value = payload[field]
    if not isinstance(value, str) or value not in allowed:
        errors.append(_error(field, "must be one of: " + ", ".join(sorted(allowed))))
        return default
    return value


def _within_limit(value: str, field: str, max_length: int, errors: list[dict[str, str]]) -> str:
    if len(value) > max_length:
        errors.append(_error(field, f"must be at most {max_length} characters"))
    return value


def _error(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}
