from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from features.beatroot_canvas.models.graph_data import GraphData
from features.beatroot_canvas.models.node import Node
from features.beatroot_canvas.models.edge import Edge


EXCLUDED_NODE_PROPERTY_KEYS = {
    "image_data",
    "metadata",
    "all_metadata",
    "exif_data",
    "png_info",
    "last_output",
    "last_output_preview",
}

MAX_STRING_LENGTH = 512
MAX_LIST_ITEMS = 25
MAX_DICT_ITEMS = 50


@dataclass(frozen=True)
class GraphChange:
    family: str
    action: str
    payload: dict[str, Any]


def diff_graph_state(before: GraphData | None, after: GraphData | None) -> list[GraphChange]:
    before = before or GraphData()
    after = after or GraphData()

    changes: list[GraphChange] = []
    changes.extend(_diff_nodes(before, after))
    changes.extend(_diff_edges(before, after))
    return changes


def build_snapshot_payload(
    graph_data: GraphData,
    *,
    trigger: str,
    capture_kind: str = "graph_checkpoint",
    summary: str | None = None,
) -> dict[str, Any]:
    node_count = len(graph_data.nodes)
    edge_count = len(graph_data.edges)
    payload = {
        "snapshot_id": compute_graph_fingerprint(graph_data),
        "trigger": str(trigger).strip() or "unspecified",
        "capture_kind": str(capture_kind).strip() or "graph_checkpoint",
        "node_count": node_count,
        "edge_count": edge_count,
        "summary": summary
        or f"Checkpoint for graph state with {node_count} nodes and {edge_count} edges.",
    }
    return payload


def compute_graph_fingerprint(graph_data: GraphData) -> str:
    canonical = {
        "title": str(graph_data.metadata.get("title", "") or "").strip(),
        "nodes": {
            node_id: _capture_node_semantics(node)
            for node_id, node in sorted(graph_data.nodes.items())
        },
        "edges": {
            edge_id: _capture_edge_semantics(edge)
            for edge_id, edge in sorted(graph_data.edges.items())
        },
    }
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _diff_nodes(before: GraphData, after: GraphData) -> list[GraphChange]:
    changes: list[GraphChange] = []
    before_ids = set(before.nodes.keys())
    after_ids = set(after.nodes.keys())

    for node_id in sorted(after_ids - before_ids):
        node = after.nodes[node_id]
        changes.append(
            GraphChange(
                family="node",
                action="created",
                payload=_build_node_payload(node),
            )
        )

    for node_id in sorted(before_ids - after_ids):
        node = before.nodes[node_id]
        changes.append(
            GraphChange(
                family="node",
                action="deleted",
                payload=_build_node_payload(node),
            )
        )

    for node_id in sorted(before_ids & after_ids):
        previous = before.nodes[node_id]
        current = after.nodes[node_id]
        previous_semantics = _capture_node_semantics(previous)
        current_semantics = _capture_node_semantics(current)
        if previous_semantics == current_semantics:
            continue

        if previous_semantics["status"] != current_semantics["status"]:
            changes.append(
                GraphChange(
                    family="node",
                    action="status_changed",
                    payload=_build_node_payload(current, properties={}),
                )
            )

        if previous_semantics["tags"] != current_semantics["tags"]:
            changes.append(
                GraphChange(
                    family="node",
                    action="tags_changed",
                    payload=_build_node_payload(current, properties={}),
                )
            )

        changed_properties = _dict_changes(
            previous_semantics["properties"],
            current_semantics["properties"],
        )
        other_changes = {
            key
            for key in ("position", "label", "evidence_refs", "properties")
            if previous_semantics[key] != current_semantics[key]
        }
        if other_changes:
            properties_payload = changed_properties if changed_properties else {}
            changes.append(
                GraphChange(
                    family="node",
                    action="updated",
                    payload=_build_node_payload(current, properties=properties_payload),
                )
            )

    return changes


def _diff_edges(before: GraphData, after: GraphData) -> list[GraphChange]:
    changes: list[GraphChange] = []
    before_ids = set(before.edges.keys())
    after_ids = set(after.edges.keys())

    for edge_id in sorted(after_ids - before_ids):
        edge = after.edges[edge_id]
        changes.append(
            GraphChange(
                family="edge",
                action="created",
                payload=_build_edge_payload(edge),
            )
        )

    for edge_id in sorted(before_ids - after_ids):
        edge = before.edges[edge_id]
        changes.append(
            GraphChange(
                family="edge",
                action="deleted",
                payload=_build_edge_payload(edge),
            )
        )

    for edge_id in sorted(before_ids & after_ids):
        previous = before.edges[edge_id]
        current = after.edges[edge_id]
        previous_semantics = _capture_edge_semantics(previous)
        current_semantics = _capture_edge_semantics(current)
        if previous_semantics == current_semantics:
            continue

        changes.append(
            GraphChange(
                family="edge",
                action="updated",
                payload=_build_edge_payload(
                    current,
                    properties=_dict_changes(
                        previous_semantics["properties"],
                        current_semantics["properties"],
                    ),
                ),
            )
        )

    return changes


def _build_node_payload(node: Node, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    semantics = _capture_node_semantics(node)
    payload: dict[str, Any] = {
        "node_id": node.id,
        "node_type": node.type,
        "position": semantics["position"],
    }
    if semantics["label"]:
        payload["label"] = semantics["label"]
    if semantics["status"]:
        payload["status"] = semantics["status"]
    if semantics["tags"]:
        payload["tags"] = semantics["tags"]
    if semantics["evidence_refs"]:
        payload["evidence_refs"] = semantics["evidence_refs"]

    if properties is None:
        properties = semantics["properties"]
    if properties:
        payload["properties"] = properties
    return payload


def _build_edge_payload(edge: Edge, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    semantics = _capture_edge_semantics(edge)
    payload: dict[str, Any] = {
        "edge_id": edge.id,
        "source_node_id": edge.source_id,
        "target_node_id": edge.target_id,
    }
    if semantics["label"]:
        payload["label"] = semantics["label"]
    if semantics["edge_type"]:
        payload["edge_type"] = semantics["edge_type"]
    if properties is None:
        properties = semantics["properties"]
    if properties:
        payload["properties"] = properties
    return payload


def _capture_node_semantics(node: Node) -> dict[str, Any]:
    properties = _filter_node_properties(node.data or {})
    return {
        "position": {
            "x": float(node.position.x()),
            "y": float(node.position.y()),
        },
        "label": _infer_node_label(node.data or {}),
        "status": _extract_status(node.data or {}),
        "tags": _extract_tags(node.data or {}),
        "evidence_refs": _extract_evidence_refs(node.data or {}),
        "properties": properties,
    }


def _capture_edge_semantics(edge: Edge) -> dict[str, Any]:
    properties = {
        "color": _sanitize_json_value(edge.color),
        "style": _sanitize_json_value(edge.style),
        "weight": _sanitize_json_value(edge.weight),
        "description": _sanitize_json_value(edge.description),
    }
    properties = {key: value for key, value in properties.items() if value not in ("", None, [], {})}
    return {
        "label": str(edge.label or "").strip(),
        "edge_type": str(edge.edge_type or "").strip(),
        "properties": properties,
    }


def _filter_node_properties(raw_data: dict[str, Any]) -> dict[str, Any]:
    filtered: dict[str, Any] = {}
    for key, value in raw_data.items():
        if not isinstance(key, str):
            continue
        if key.startswith("__") or key in EXCLUDED_NODE_PROPERTY_KEYS:
            continue
        sanitized = _sanitize_json_value(value)
        if sanitized in ("", None, [], {}):
            continue
        filtered[key] = sanitized
    return dict(list(sorted(filtered.items()))[:MAX_DICT_ITEMS])


def _sanitize_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        if len(normalized) > MAX_STRING_LENGTH:
            return normalized[: MAX_STRING_LENGTH - 15] + "...[truncated]"
        return normalized
    if isinstance(value, (list, tuple)):
        items = [_sanitize_json_value(item) for item in list(value)[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            items.append("...[truncated]")
        return items
    if isinstance(value, dict):
        sanitized_items = {}
        for index, key in enumerate(sorted(value.keys(), key=lambda item: str(item))):
            if index >= MAX_DICT_ITEMS:
                sanitized_items["..."] = "[truncated]"
                break
            sanitized_items[str(key)] = _sanitize_json_value(value[key])
        return sanitized_items
    return str(value)


def _infer_node_label(data: dict[str, Any]) -> str:
    for key in ("label", "title", "name", "target", "filename", "host", "domain", "ip", "url", "command"):
        value = str(data.get(key, "") or "").strip()
        if value:
            return value[:MAX_STRING_LENGTH]
    return ""


def _extract_status(data: dict[str, Any]) -> str:
    for key in ("status", "analysis_status"):
        value = str(data.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _extract_tags(data: dict[str, Any]) -> list[str]:
    raw_tags = data.get("tags", [])
    if isinstance(raw_tags, str):
        values = [item.strip() for item in raw_tags.split(",") if item.strip()]
    elif isinstance(raw_tags, (list, tuple)):
        values = [str(item).strip() for item in raw_tags if str(item).strip()]
    else:
        values = []
    return values[:MAX_LIST_ITEMS]


def _extract_evidence_refs(data: dict[str, Any]) -> list[str]:
    raw_refs = data.get("evidence_refs", [])
    if isinstance(raw_refs, str):
        refs = [raw_refs.strip()] if raw_refs.strip() else []
    elif isinstance(raw_refs, (list, tuple)):
        refs = [str(item).strip() for item in raw_refs if str(item).strip()]
    else:
        refs = []
    return refs[:MAX_LIST_ITEMS]


def _dict_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed: dict[str, Any] = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        if before.get(key) != after.get(key):
            changed[key] = after.get(key)
    return changed

