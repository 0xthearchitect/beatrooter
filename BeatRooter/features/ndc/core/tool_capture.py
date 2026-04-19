from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .schema import ToolPayload

MAX_TOOL_SUMMARY_CHARS = 240
DEFAULT_ARTIFACT_LIMIT = 5

_ACTION_KIND_BY_EVENT_ACTION = {
    "opened": "open",
    "executed": "run",
    "imported": "import",
    "exported": "export",
    "helper_invoked": "helper_action",
    "analysis_captured": "side_analysis",
}


def compact_tool_summary(text: str, *, max_chars: int = MAX_TOOL_SUMMARY_CHARS) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    clipped = normalized[: max(1, max_chars - 3)].rstrip()
    return f"{clipped}..."


def build_artifact_refs(
    values: Iterable[str],
    *,
    root_path: str | None = None,
    limit: int = DEFAULT_ARTIFACT_LIMIT,
) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    max_items = max(1, int(limit))
    resolved_root = _resolve_root_path(root_path)

    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value:
            continue

        normalized = _normalize_artifact_ref(value, resolved_root)
        if not normalized or normalized in seen:
            continue

        refs.append(normalized)
        seen.add(normalized)
        if len(refs) >= max_items:
            break

    return tuple(refs)


def build_tool_payload(
    *,
    event_action: str,
    tool_name: str,
    surface: str,
    result_summary: str | None = None,
    result_status: str | None = None,
    result_count: int | None = None,
    related_node_id: str | None = None,
    target_ref: str | None = None,
    command_ref: str | None = None,
    artifact_refs: Iterable[str] = (),
    context_scope: str | None = None,
) -> ToolPayload:
    action_kind = _ACTION_KIND_BY_EVENT_ACTION[event_action]
    node_id = _clean_optional_value(related_node_id)
    return ToolPayload(
        tool_name=str(tool_name or "").strip(),
        action_kind=action_kind,
        context_scope=str(context_scope or ("node" if node_id else "project")).strip(),
        surface=str(surface or "").strip(),
        result_summary=compact_tool_summary(result_summary) if result_summary else None,
        result_status=_clean_optional_value(result_status),
        result_count=result_count,
        related_node_id=node_id,
        target_ref=_clean_optional_value(target_ref),
        command_ref=_clean_optional_value(command_ref),
        artifact_refs=_clean_artifact_refs(artifact_refs),
    )


def _resolve_root_path(root_path: str | None) -> Path | None:
    raw_root = str(root_path or "").strip()
    if not raw_root:
        return None
    try:
        return Path(raw_root).expanduser().resolve()
    except OSError:
        return None


def _normalize_artifact_ref(value: str, root_path: Path | None) -> str:
    candidate = Path(value).expanduser()
    if root_path is not None:
        try:
            resolved_candidate = candidate.resolve()
            return str(resolved_candidate.relative_to(root_path))
        except Exception:
            pass

    if candidate.name:
        return candidate.name
    return value


def _clean_optional_value(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _clean_artifact_refs(values: Iterable[str]) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value or value in seen:
            continue
        refs.append(value)
        seen.add(value)
    return tuple(refs)
