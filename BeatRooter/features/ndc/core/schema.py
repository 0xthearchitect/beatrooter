from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Mapping
from uuid import uuid4


CURRENT_NDC_SCHEMA_VERSION = "1.0.0"
SUPPORTED_NDC_SCHEMA_VERSIONS: tuple[str, ...] = (CURRENT_NDC_SCHEMA_VERSION,)

NDC_SCHEMA_MIGRATION_EXPECTATIONS: dict[str, str] = {
    CURRENT_NDC_SCHEMA_VERSION: (
        "Baseline envelope and payload contract. Additive optional fields may be introduced "
        "without changing the version, but breaking changes require a new schema_version, an "
        "explicit migration adapter, dual-read validation, and replay tests against stored events."
    ),
}

_ISO_8601_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class NDCValidationError(ValueError):
    """Raised when an event does not satisfy the NDC schema contract."""


class NDCEventFamily(StrEnum):
    NODE = "node"
    EDGE = "edge"
    NOTE = "note"
    TOOL = "tool"
    PROJECT = "project"
    SNAPSHOT = "snapshot"


CANONICAL_EVENT_ACTIONS: dict[NDCEventFamily, tuple[str, ...]] = {
    NDCEventFamily.NODE: (
        "created",
        "updated",
        "deleted",
        "status_changed",
        "tags_changed",
        "evidence_attached",
        "evidence_removed",
    ),
    NDCEventFamily.EDGE: (
        "created",
        "updated",
        "deleted",
    ),
    NDCEventFamily.NOTE: (
        "created",
        "updated",
        "deleted",
        "tags_changed",
        "linked",
        "unlinked",
    ),
    NDCEventFamily.TOOL: (
        "opened",
        "executed",
        "imported",
        "exported",
        "helper_invoked",
        "analysis_captured",
    ),
    NDCEventFamily.PROJECT: (
        "opened",
        "saved",
        "autosaved",
        "duplicated",
        "exported",
        "archived",
        "restored",
        "migrated",
        "closed",
    ),
    NDCEventFamily.SNAPSHOT: (
        "checkpoint_created",
        "checkpoint_saved",
        "checkpoint_exported",
        "checkpoint_closed",
        "checkpoint_scheduled",
    ),
}

NOTE_SCOPES: tuple[str, ...] = ("standalone", "project", "node")
TOOL_ACTION_KINDS: tuple[str, ...] = (
    "open",
    "run",
    "import",
    "export",
    "helper_action",
    "side_analysis",
)
TOOL_SURFACES: tuple[str, ...] = (
    "side_panel",
    "helper_window",
    "import_wizard",
    "export_flow",
    "analysis_utility",
    "background_service",
    "cli",
)
TOOL_RESULT_STATUSES: tuple[str, ...] = ("success", "partial", "failure", "cancelled")

_TOOL_ACTION_BY_EVENT_ACTION: dict[str, str] = {
    "opened": "open",
    "executed": "run",
    "imported": "import",
    "exported": "export",
    "helper_invoked": "helper_action",
    "analysis_captured": "side_analysis",
}


@dataclass(frozen=True)
class NotePayload:
    note_id: str
    title: str
    note_scope: str
    body: str = ""
    format: str = "plain_text"
    category: str = "other"
    tags: tuple[str, ...] = ()
    linked_node_id: str | None = None
    source_ref: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "note_id": self.note_id,
            "title": self.title,
            "note_scope": self.note_scope,
            "body": self.body,
            "format": self.format,
            "category": self.category,
            "tags": list(self.tags),
        }
        if self.linked_node_id is not None:
            payload["linked_node_id"] = self.linked_node_id
        if self.source_ref is not None:
            payload["source_ref"] = self.source_ref
        if self.created_at is not None:
            payload["created_at"] = self.created_at
        if self.updated_at is not None:
            payload["updated_at"] = self.updated_at
        return payload


@dataclass(frozen=True)
class ToolPayload:
    tool_name: str
    action_kind: str
    context_scope: str
    surface: str
    result_summary: str | None = None
    result_status: str | None = None
    result_count: int | None = None
    related_node_id: str | None = None
    target_ref: str | None = None
    command_ref: str | None = None
    artifact_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool_name": self.tool_name,
            "action_kind": self.action_kind,
            "context_scope": self.context_scope,
            "surface": self.surface,
            "artifact_refs": list(self.artifact_refs),
        }
        if self.result_summary is not None:
            payload["result_summary"] = self.result_summary
        if self.result_status is not None:
            payload["result_status"] = self.result_status
        if self.result_count is not None:
            payload["result_count"] = self.result_count
        if self.related_node_id is not None:
            payload["related_node_id"] = self.related_node_id
        if self.target_ref is not None:
            payload["target_ref"] = self.target_ref
        if self.command_ref is not None:
            payload["command_ref"] = self.command_ref
        return payload


@dataclass(frozen=True)
class NDCEvent:
    family: NDCEventFamily
    action: str
    event_id: str
    source_id: str
    project_id: str
    created_at: str
    schema_version: str
    payload: dict[str, Any]
    content_hash: str
    sequence_number: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family.value,
            "action": self.action,
            "event_id": self.event_id,
            "source_id": self.source_id,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "content_hash": self.content_hash,
            "sequence_number": self.sequence_number,
        }


def create_ndc_event(
    *,
    family: str | NDCEventFamily,
    action: str,
    source_id: str,
    project_id: str,
    sequence_number: int,
    payload: Mapping[str, Any] | NotePayload | ToolPayload,
    event_id: str | None = None,
    created_at: str | None = None,
    schema_version: str = CURRENT_NDC_SCHEMA_VERSION,
    content_hash: str | None = None,
) -> NDCEvent:
    normalized_family = _normalize_family(family)
    normalized_action = _normalize_action(normalized_family, action)
    normalized_payload = validate_payload(
        normalized_family,
        normalized_action,
        _payload_to_dict(payload),
    )
    normalized_created_at = _normalize_timestamp(
        "created_at",
        created_at or _utc_now_iso(),
    )
    normalized_schema_version = _normalize_schema_version(schema_version)
    normalized_content_hash = content_hash or compute_content_hash(
        normalized_family,
        normalized_action,
        normalized_payload,
    )

    event = NDCEvent(
        family=normalized_family,
        action=normalized_action,
        event_id=_normalize_identifier("event_id", event_id or str(uuid4())),
        source_id=_normalize_identifier("source_id", source_id),
        project_id=_normalize_identifier("project_id", project_id),
        created_at=normalized_created_at,
        schema_version=normalized_schema_version,
        payload=normalized_payload,
        content_hash=_normalize_content_hash(
            normalized_family,
            normalized_action,
            normalized_payload,
            normalized_content_hash,
        ),
        sequence_number=_normalize_non_negative_int("sequence_number", sequence_number),
    )
    return event


def validate_ndc_event(candidate: Mapping[str, Any]) -> NDCEvent:
    if not isinstance(candidate, Mapping):
        raise NDCValidationError("NDC event must be a mapping.")

    family = _normalize_family(candidate.get("family"))
    action = _normalize_action(family, candidate.get("action"))
    payload = validate_payload(family, action, candidate.get("payload"))

    return NDCEvent(
        family=family,
        action=action,
        event_id=_normalize_identifier("event_id", candidate.get("event_id")),
        source_id=_normalize_identifier("source_id", candidate.get("source_id")),
        project_id=_normalize_identifier("project_id", candidate.get("project_id")),
        created_at=_normalize_timestamp("created_at", candidate.get("created_at")),
        schema_version=_normalize_schema_version(candidate.get("schema_version")),
        payload=payload,
        content_hash=_normalize_content_hash(
            family,
            action,
            payload,
            candidate.get("content_hash"),
        ),
        sequence_number=_normalize_non_negative_int(
            "sequence_number",
            candidate.get("sequence_number"),
        ),
    )


def validate_payload(
    family: str | NDCEventFamily,
    action: str,
    payload: Any,
) -> dict[str, Any]:
    normalized_family = _normalize_family(family)
    normalized_action = _normalize_action(normalized_family, action)
    if not isinstance(payload, Mapping):
        raise NDCValidationError("payload must be a mapping.")

    payload_dict = dict(payload)
    if normalized_family is NDCEventFamily.NODE:
        return _validate_node_payload(payload_dict)
    if normalized_family is NDCEventFamily.EDGE:
        return _validate_edge_payload(payload_dict)
    if normalized_family is NDCEventFamily.NOTE:
        return _validate_note_payload(normalized_action, payload_dict)
    if normalized_family is NDCEventFamily.TOOL:
        return _validate_tool_payload(normalized_action, payload_dict)
    if normalized_family is NDCEventFamily.PROJECT:
        return _validate_project_payload(payload_dict)
    if normalized_family is NDCEventFamily.SNAPSHOT:
        return _validate_snapshot_payload(payload_dict)

    raise NDCValidationError(f"Unsupported NDC family: {normalized_family!r}")


def compute_content_hash(
    family: str | NDCEventFamily,
    action: str,
    payload: Mapping[str, Any],
) -> str:
    normalized_family = _normalize_family(family)
    normalized_action = _normalize_action(normalized_family, action)
    normalized_payload = validate_payload(normalized_family, normalized_action, payload)

    try:
        canonical_blob = json.dumps(
            {
                "family": normalized_family.value,
                "action": normalized_action,
                "payload": normalized_payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    except TypeError as exc:
        raise NDCValidationError(f"payload must be JSON-serializable: {exc}") from exc

    return hashlib.sha256(canonical_blob.encode("utf-8")).hexdigest()


def migration_expectations_for(schema_version: str) -> str:
    normalized = _normalize_schema_version(schema_version)
    return NDC_SCHEMA_MIGRATION_EXPECTATIONS[normalized]


def _validate_node_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "node_id": _normalize_identifier("payload.node_id", payload.get("node_id")),
        "node_type": _normalize_simple_string("payload.node_type", payload.get("node_type")),
    }

    optional_strings = ("label", "status")
    for field_name in optional_strings:
        if field_name in payload and payload[field_name] is not None:
            normalized[field_name] = _normalize_simple_string(
                f"payload.{field_name}",
                payload[field_name],
            )

    if "tags" in payload and payload["tags"] is not None:
        normalized["tags"] = _normalize_string_list("payload.tags", payload["tags"])

    if "evidence_refs" in payload and payload["evidence_refs"] is not None:
        normalized["evidence_refs"] = _normalize_string_list(
            "payload.evidence_refs",
            payload["evidence_refs"],
        )

    if "properties" in payload and payload["properties"] is not None:
        normalized["properties"] = _normalize_json_object("payload.properties", payload["properties"])

    if "position" in payload and payload["position"] is not None:
        position = payload["position"]
        if not isinstance(position, Mapping):
            raise NDCValidationError("payload.position must be a mapping.")
        normalized["position"] = {
            "x": _normalize_number("payload.position.x", position.get("x")),
            "y": _normalize_number("payload.position.y", position.get("y")),
        }

    return normalized


def _validate_edge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "edge_id": _normalize_identifier("payload.edge_id", payload.get("edge_id")),
        "source_node_id": _normalize_identifier(
            "payload.source_node_id",
            payload.get("source_node_id"),
        ),
        "target_node_id": _normalize_identifier(
            "payload.target_node_id",
            payload.get("target_node_id"),
        ),
    }

    for field_name in ("label", "edge_type"):
        if field_name in payload and payload[field_name] is not None:
            normalized[field_name] = _normalize_simple_string(
                f"payload.{field_name}",
                payload[field_name],
            )

    if "properties" in payload and payload["properties"] is not None:
        normalized["properties"] = _normalize_json_object("payload.properties", payload["properties"])

    return normalized


def _validate_note_payload(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "note_id": _normalize_identifier("payload.note_id", payload.get("note_id")),
        "note_scope": _normalize_choice("payload.note_scope", payload.get("note_scope"), NOTE_SCOPES),
    }

    title = payload.get("title")
    if action != "deleted" or title is not None:
        normalized["title"] = _normalize_simple_string("payload.title", title)

    if action != "deleted" or "body" in payload:
        normalized["body"] = _normalize_multiline_string(
            "payload.body",
            payload.get("body", ""),
        )

    if action != "deleted" or "format" in payload:
        normalized["format"] = _normalize_simple_string(
            "payload.format",
            payload.get("format", "plain_text"),
        )

    if action != "deleted" or "category" in payload:
        normalized["category"] = _normalize_simple_string(
            "payload.category",
            payload.get("category", "other"),
        )

    if action != "deleted" or "tags" in payload:
        normalized["tags"] = _normalize_string_list("payload.tags", payload.get("tags", []))

    if payload.get("linked_node_id") is not None:
        normalized["linked_node_id"] = _normalize_identifier(
            "payload.linked_node_id",
            payload.get("linked_node_id"),
        )

    if normalized["note_scope"] == "node" and "linked_node_id" not in normalized:
        raise NDCValidationError("Node-linked notes must include payload.linked_node_id.")

    if normalized["note_scope"] != "node" and "linked_node_id" in normalized:
        raise NDCValidationError("Only node-linked notes may include payload.linked_node_id.")

    if payload.get("source_ref") is not None:
        normalized["source_ref"] = _normalize_simple_string("payload.source_ref", payload.get("source_ref"))

    for timestamp_field in ("created_at", "updated_at"):
        if payload.get(timestamp_field) is not None:
            normalized[timestamp_field] = _normalize_timestamp(
                f"payload.{timestamp_field}",
                payload.get(timestamp_field),
            )

    return normalized


def _validate_tool_payload(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "tool_name": _normalize_simple_string("payload.tool_name", payload.get("tool_name")),
        "action_kind": _normalize_choice(
            "payload.action_kind",
            payload.get("action_kind"),
            TOOL_ACTION_KINDS,
        ),
        "context_scope": _normalize_simple_string(
            "payload.context_scope",
            payload.get("context_scope"),
        ),
        "surface": _normalize_choice("payload.surface", payload.get("surface"), TOOL_SURFACES),
        "artifact_refs": _normalize_string_list(
            "payload.artifact_refs",
            payload.get("artifact_refs", []),
        ),
    }

    expected_action_kind = _TOOL_ACTION_BY_EVENT_ACTION[action]
    if normalized["action_kind"] != expected_action_kind:
        raise NDCValidationError(
            f"payload.action_kind must be '{expected_action_kind}' when tool action is '{action}'."
        )

    if payload.get("result_summary") is not None:
        normalized["result_summary"] = _normalize_multiline_string(
            "payload.result_summary",
            payload.get("result_summary"),
        )

    if action in {"executed", "imported", "exported", "analysis_captured"} and "result_summary" not in normalized:
        raise NDCValidationError(
            f"payload.result_summary is required for tool action '{action}'."
        )

    if payload.get("result_status") is not None:
        normalized["result_status"] = _normalize_choice(
            "payload.result_status",
            payload.get("result_status"),
            TOOL_RESULT_STATUSES,
        )

    if payload.get("result_count") is not None:
        normalized["result_count"] = _normalize_non_negative_int(
            "payload.result_count",
            payload.get("result_count"),
        )

    for field_name in ("related_node_id", "target_ref", "command_ref"):
        if payload.get(field_name) is not None:
            normalizer = _normalize_identifier if field_name == "related_node_id" else _normalize_simple_string
            normalized[field_name] = normalizer(f"payload.{field_name}", payload.get(field_name))

    return normalized


def _validate_project_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "project_title": _normalize_simple_string("payload.project_title", payload.get("project_title")),
    }

    for field_name in ("file_path", "reason", "schema_from", "schema_to"):
        if payload.get(field_name) is not None:
            normalized[field_name] = _normalize_simple_string(
                f"payload.{field_name}",
                payload.get(field_name),
            )

    return normalized


def _validate_snapshot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "snapshot_id": _normalize_identifier("payload.snapshot_id", payload.get("snapshot_id")),
        "trigger": _normalize_simple_string("payload.trigger", payload.get("trigger")),
        "capture_kind": _normalize_simple_string(
            "payload.capture_kind",
            payload.get("capture_kind"),
        ),
    }

    for field_name in ("node_count", "edge_count"):
        if payload.get(field_name) is not None:
            normalized[field_name] = _normalize_non_negative_int(
                f"payload.{field_name}",
                payload.get(field_name),
            )

    if payload.get("summary") is not None:
        normalized["summary"] = _normalize_multiline_string("payload.summary", payload.get("summary"))

    return normalized


def _normalize_family(value: Any) -> NDCEventFamily:
    text = _normalize_simple_string("family", value)
    try:
        return NDCEventFamily(text)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in NDCEventFamily)
        raise NDCValidationError(f"family must be one of: {allowed}.") from exc


def _normalize_action(family: NDCEventFamily, action: Any) -> str:
    text = _normalize_simple_string("action", action)
    allowed_actions = CANONICAL_EVENT_ACTIONS[family]
    if text not in allowed_actions:
        allowed = ", ".join(allowed_actions)
        raise NDCValidationError(f"action must be one of [{allowed}] for family '{family.value}'.")
    return text


def _normalize_schema_version(value: Any) -> str:
    text = _normalize_simple_string("schema_version", value)
    if text not in SUPPORTED_NDC_SCHEMA_VERSIONS:
        supported = ", ".join(SUPPORTED_NDC_SCHEMA_VERSIONS)
        raise NDCValidationError(f"schema_version must be one of: {supported}.")
    return text


def _normalize_content_hash(
    family: NDCEventFamily,
    action: str,
    payload: Mapping[str, Any],
    value: Any,
) -> str:
    text = _normalize_simple_string("content_hash", value).lower()
    if not _HEX_SHA256_RE.fullmatch(text):
        raise NDCValidationError("content_hash must be a lowercase SHA-256 hex digest.")

    expected = compute_content_hash(family, action, payload)
    if text != expected:
        raise NDCValidationError("content_hash does not match the canonical payload hash.")
    return text


def _normalize_identifier(name: str, value: Any) -> str:
    text = _normalize_simple_string(name, value)
    if any(char.isspace() for char in text):
        raise NDCValidationError(f"{name} must not contain whitespace.")
    return text


def _normalize_simple_string(name: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise NDCValidationError(f"{name} is required.")
    if any(char in text for char in ("\n", "\r", "\t")):
        raise NDCValidationError(f"{name} must be a single line.")
    return text


def _normalize_multiline_string(name: str, value: Any) -> str:
    if value is None:
        raise NDCValidationError(f"{name} is required.")
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _normalize_choice(name: str, value: Any, allowed_values: tuple[str, ...]) -> str:
    text = _normalize_simple_string(name, value)
    if text not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise NDCValidationError(f"{name} must be one of: {allowed}.")
    return text


def _normalize_string_list(name: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise NDCValidationError(f"{name} must be a list of strings.")
    return [_normalize_simple_string(f"{name}[{index}]", item) for index, item in enumerate(value)]


def _normalize_json_object(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise NDCValidationError(f"{name} must be a mapping.")

    normalized = {str(key): raw_value for key, raw_value in value.items()}
    try:
        json.dumps(normalized, sort_keys=True, ensure_ascii=True)
    except TypeError as exc:
        raise NDCValidationError(f"{name} must contain JSON-serializable values: {exc}") from exc
    return normalized


def _normalize_timestamp(name: str, value: Any) -> str:
    text = _normalize_simple_string(name, value)
    if not _ISO_8601_UTC_RE.fullmatch(text):
        raise NDCValidationError(f"{name} must be an ISO-8601 timestamp with timezone.")
    candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise NDCValidationError(f"{name} must be a valid ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise NDCValidationError(f"{name} must include timezone information.")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_non_negative_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise NDCValidationError(f"{name} must be a non-negative integer.")
    if value < 0:
        raise NDCValidationError(f"{name} must be a non-negative integer.")
    return value


def _normalize_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NDCValidationError(f"{name} must be numeric.")
    return float(value)


def _payload_to_dict(payload: Mapping[str, Any] | NotePayload | ToolPayload) -> dict[str, Any]:
    if isinstance(payload, (NotePayload, ToolPayload)):
        return payload.to_dict()
    if isinstance(payload, Mapping):
        return dict(payload)
    raise NDCValidationError("payload must be a mapping or an NDC payload helper dataclass.")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

