from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from features.ndc.server.governance import NDCSensitiveDataMinimizer
from features.ndc.server.normalized_store import NDCNormalizedStore


DOCUMENT_TYPES: tuple[str, ...] = (
    "project_summary",
    "timeline_chunk",
    "note_context_chunk",
    "tool_context_chunk",
)

QUALITY_THRESHOLD = 0.45


class NDCDerivedDocumentError(RuntimeError):
    """Raised when the derived document pipeline cannot build or persist documents."""


@dataclass(frozen=True)
class NDCDerivedDocument:
    document_id: str
    document_type: str
    source_id: str
    project_id: str
    title: str
    text: str
    metadata: dict[str, Any]
    provenance: dict[str, Any]
    quality_score: float
    quality_flags: tuple[str, ...]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "source_id": self.source_id,
            "project_id": self.project_id,
            "title": self.title,
            "text": self.text,
            "metadata": self.metadata,
            "provenance": self.provenance,
            "quality_score": self.quality_score,
            "quality_flags": list(self.quality_flags),
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class NDCDerivedBuildResult:
    source_id: str
    project_id: str
    documents: tuple[NDCDerivedDocument, ...]
    rejected_documents: tuple[dict[str, Any], ...]
    output_dir: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "project_id": self.project_id,
            "document_count": len(self.documents),
            "rejected_count": len(self.rejected_documents),
            "output_dir": str(self.output_dir),
            "documents": [document.to_dict() for document in self.documents],
            "rejected_documents": list(self.rejected_documents),
        }


class NDCDerivedDocumentPipeline:
    def __init__(
        self,
        base_dir: str | Path,
        *,
        normalized_store: NDCNormalizedStore,
        minimizer: NDCSensitiveDataMinimizer | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.normalized_store = normalized_store
        self.minimizer = minimizer or NDCSensitiveDataMinimizer()
        self.documents_root = self.base_dir / "derived_documents"
        self.failures_path = self.base_dir / "derived_document_failures.jsonl"
        self.documents_root.mkdir(parents=True, exist_ok=True)

    def rebuild_project_documents(
        self,
        project_id: str,
        *,
        source_id: str | None = None,
    ) -> NDCDerivedBuildResult:
        timeline = self.normalized_store.reconstruct_project_timeline(
            project_id,
            source_id=source_id,
        )
        resolved_source_id = str(timeline["source_id"])
        resolved_project_id = str(timeline["project_id"])
        note_histories = self._load_note_histories(resolved_source_id, resolved_project_id)
        tool_rows = self._load_tool_rows(resolved_source_id, resolved_project_id)

        candidates: list[dict[str, Any]] = []
        candidates.extend(self._build_project_summary_candidates(timeline))
        candidates.extend(self._build_timeline_candidates(timeline))
        candidates.extend(self._build_note_candidates(timeline, note_histories))
        candidates.extend(self._build_tool_candidates(timeline, tool_rows))

        admitted_documents, rejected_documents = self._finalize_candidates(candidates)
        output_dir = self.documents_root / resolved_source_id / resolved_project_id
        self._persist_documents(
            output_dir,
            admitted_documents,
            rejected_documents,
            source_id=resolved_source_id,
            project_id=resolved_project_id,
        )
        return NDCDerivedBuildResult(
            source_id=resolved_source_id,
            project_id=resolved_project_id,
            documents=tuple(admitted_documents),
            rejected_documents=tuple(rejected_documents),
            output_dir=output_dir,
        )

    def record_failure(
        self,
        *,
        source_id: str | None,
        project_id: str,
        error: Exception,
    ) -> None:
        self._append_jsonl(
            self.failures_path,
            {
                "source_id": source_id,
                "project_id": project_id,
                "error": str(error),
            },
        )

    def _build_project_summary_candidates(self, timeline: dict[str, Any]) -> list[dict[str, Any]]:
        final_state = timeline["final_state"]
        project_state = final_state["project"]
        nodes = list(final_state["nodes"].values())
        active_notes = [note for note in final_state["notes"].values() if not note.get("deleted")]
        tool_activity = list(final_state["tool_activity"])
        snapshots = list(final_state["snapshots"])
        recent_note_titles = [note.get("title") for note in active_notes if note.get("title")][:3]
        recent_tool_summaries = [entry.get("result_summary") for entry in tool_activity if entry.get("result_summary")][:3]
        text = "\n".join(
            [
                f"Project {project_state.get('project_title') or timeline['project_id']} ({timeline['project_id']}) from source {timeline['source_id']}.",
                f"Lifecycle status: {project_state.get('lifecycle_status') or 'unknown'}.",
                f"Current graph has {len(final_state['nodes'])} nodes and {len(final_state['edges'])} edges.",
                f"Active notes: {len(active_notes)}. Tool activity records: {len(tool_activity)}. Snapshot checkpoints: {len(snapshots)}.",
                "Current nodes: " + ", ".join(
                    self._describe_node(node)
                    for node in nodes[:6]
                )
                if nodes
                else "Current nodes: none.",
                "Recent note context: " + "; ".join(recent_note_titles)
                if recent_note_titles
                else "Recent note context: none.",
                "Recent tool context: " + "; ".join(recent_tool_summaries)
                if recent_tool_summaries
                else "Recent tool context: none.",
            ]
        )
        event_ids = [entry["event_id"] for entry in timeline["entries"]]
        receipt_ids = self._dedupe_preserve_order(entry["receipt_id"] for entry in timeline["entries"])
        return [
            self._candidate(
                document_id=f"{timeline['source_id']}:{timeline['project_id']}:project_summary",
                document_type="project_summary",
                source_id=timeline["source_id"],
                project_id=timeline["project_id"],
                title=f"Project summary for {project_state.get('project_title') or timeline['project_id']}",
                text=text,
                metadata={
                    "lifecycle_status": project_state.get("lifecycle_status"),
                    "node_count": len(final_state["nodes"]),
                    "edge_count": len(final_state["edges"]),
                    "active_note_count": len(active_notes),
                    "tool_activity_count": len(tool_activity),
                    "snapshot_count": len(snapshots),
                    "node_ids": sorted(final_state["nodes"].keys()),
                    "note_ids": sorted(note["note_id"] for note in active_notes),
                    "tool_names": sorted(
                        {
                            entry["tool_name"]
                            for entry in tool_activity
                            if entry.get("tool_name")
                        }
                    ),
                    "tags": sorted(
                        {
                            tag
                            for note in active_notes
                            for tag in note.get("tags", [])
                        }
                    ),
                },
                provenance={
                    "event_ids": event_ids,
                    "receipt_ids": receipt_ids,
                    "sequence_range": self._sequence_range(timeline["entries"]),
                },
            )
        ]

    def _build_timeline_candidates(self, timeline: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        current_chunk: list[dict[str, Any]] = []
        current_lines: list[str] = []

        def flush_chunk() -> None:
            if not current_chunk:
                return
            chunk_index = len(candidates)
            title = f"Timeline chunk {chunk_index + 1} for {timeline['project_id']}"
            text = "\n".join(current_lines).strip()
            candidates.append(
                self._candidate(
                    document_id=f"{timeline['source_id']}:{timeline['project_id']}:timeline:{chunk_index}",
                    document_type="timeline_chunk",
                    source_id=timeline["source_id"],
                    project_id=timeline["project_id"],
                    title=title,
                    text=text,
                    metadata={
                        "chunk_index": chunk_index,
                        "event_count": len(current_chunk),
                        "families": sorted({entry["family"] for entry in current_chunk}),
                        "sequence_range": self._sequence_range(current_chunk),
                    },
                    provenance={
                        "event_ids": [entry["event_id"] for entry in current_chunk],
                        "receipt_ids": self._dedupe_preserve_order(entry["receipt_id"] for entry in current_chunk),
                        "sequence_range": self._sequence_range(current_chunk),
                    },
                )
            )
            current_chunk.clear()
            current_lines.clear()

        for entry in timeline["entries"]:
            line = self._timeline_line(entry)
            projected_text = "\n".join(current_lines + [line]).strip()
            if current_chunk and (len(current_chunk) >= 6 or len(projected_text) > 1100):
                flush_chunk()
            current_chunk.append(entry)
            current_lines.append(line)

        flush_chunk()
        return candidates

    def _build_note_candidates(
        self,
        timeline: dict[str, Any],
        note_histories: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        final_notes = timeline["final_state"]["notes"]
        for note_id, note_state in sorted(final_notes.items()):
            if note_state.get("deleted"):
                continue
            body = str(note_state.get("body") or "").strip()
            title = str(note_state.get("title") or note_id).strip()
            note_lines = [
                f"Note {title} ({note_id}).",
                f"Scope: {note_state.get('note_scope') or 'unknown'}. Category: {note_state.get('category') or 'other'}.",
            ]
            if note_state.get("linked_node_id"):
                note_lines.append(f"Linked node: {note_state['linked_node_id']}.")
            if note_state.get("source_ref"):
                note_lines.append(f"Captured from: {note_state['source_ref']}.")
            if note_state.get("updated_at"):
                note_lines.append(f"Updated at: {note_state['updated_at']}.")
            if note_state.get("tags"):
                note_lines.append("Tags: " + ", ".join(note_state["tags"]) + ".")
            note_lines.append("Content:")
            prefix = "\n".join(note_lines)
            note_chunks = self._split_text_into_chunks(body or title, max_chars=900)
            history_rows = note_histories.get(note_id, [])
            provenance = {
                "event_ids": [row["event_id"] for row in history_rows],
                "receipt_ids": self._dedupe_preserve_order(row["receipt_id"] for row in history_rows),
                "sequence_range": self._sequence_range(history_rows),
            }
            for chunk_index, chunk_text in enumerate(note_chunks):
                text = f"{prefix}\n{chunk_text}".strip()
                candidates.append(
                    self._candidate(
                        document_id=f"{timeline['source_id']}:{timeline['project_id']}:note:{note_id}:{chunk_index}",
                        document_type="note_context_chunk",
                        source_id=timeline["source_id"],
                        project_id=timeline["project_id"],
                        title=f"Note context for {title} ({chunk_index + 1}/{len(note_chunks)})",
                        text=text,
                        metadata={
                            "note_id": note_id,
                            "chunk_index": chunk_index,
                            "chunk_count": len(note_chunks),
                            "content_char_count": len(chunk_text),
                            "note_scope": note_state.get("note_scope"),
                            "category": note_state.get("category"),
                            "linked_node_id": note_state.get("linked_node_id"),
                            "source_ref": note_state.get("source_ref"),
                            "tags": list(note_state.get("tags", [])),
                            "updated_at": note_state.get("updated_at"),
                        },
                        provenance=provenance,
                        dedupe_basis=f"note:{note_state.get('note_scope')}:{note_state.get('category')}:{self._normalize_document_text(chunk_text)}",
                    )
                )
        return candidates

    def _build_tool_candidates(
        self,
        timeline: dict[str, Any],
        tool_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in tool_rows:
            grouped.setdefault(row["tool_name"], []).append(row)

        candidates: list[dict[str, Any]] = []
        for tool_name, rows in sorted(grouped.items()):
            current_rows: list[dict[str, Any]] = []
            current_lines: list[str] = []

            def flush_chunk() -> None:
                if not current_rows:
                    return
                chunk_index = len(
                    [
                        candidate
                        for candidate in candidates
                        if candidate["document_type"] == "tool_context_chunk"
                        and candidate["metadata"].get("tool_name") == tool_name
                    ]
                )
                text = "\n".join(current_lines).strip()
                candidates.append(
                    self._candidate(
                        document_id=f"{timeline['source_id']}:{timeline['project_id']}:tool:{tool_name}:{chunk_index}",
                        document_type="tool_context_chunk",
                        source_id=timeline["source_id"],
                        project_id=timeline["project_id"],
                        title=f"Tool context for {tool_name} ({chunk_index + 1})",
                        text=text,
                        metadata={
                            "tool_name": tool_name,
                            "chunk_index": chunk_index,
                            "event_count": len(current_rows),
                            "result_summary_count": sum(1 for row in current_rows if row.get("result_summary")),
                            "surfaces": sorted({row["surface"] for row in current_rows if row.get("surface")}),
                            "context_scopes": sorted(
                                {row["context_scope"] for row in current_rows if row.get("context_scope")}
                            ),
                            "related_node_ids": sorted(
                                {
                                    row["related_node_id"]
                                    for row in current_rows
                                    if row.get("related_node_id")
                                }
                            ),
                            "statuses": sorted(
                                {
                                    row["result_status"]
                                    for row in current_rows
                                    if row.get("result_status")
                                }
                            ),
                        },
                        provenance={
                            "event_ids": [row["event_id"] for row in current_rows],
                            "receipt_ids": self._dedupe_preserve_order(row["receipt_id"] for row in current_rows),
                            "sequence_range": self._sequence_range(current_rows),
                        },
                        dedupe_basis=f"tool:{tool_name}:{self._normalize_document_text(text)}",
                    )
                )
                current_rows.clear()
                current_lines.clear()

            for row in rows:
                line = self._tool_line(row)
                projected_text = "\n".join(current_lines + [line]).strip()
                if current_rows and (len(current_rows) >= 5 or len(projected_text) > 1000):
                    flush_chunk()
                current_rows.append(row)
                current_lines.append(line)
            flush_chunk()
        return candidates

    def _finalize_candidates(
        self,
        candidates: list[dict[str, Any]],
    ) -> tuple[list[NDCDerivedDocument], list[dict[str, Any]]]:
        admitted: list[NDCDerivedDocument] = []
        rejected: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()

        for candidate in candidates:
            normalized_text = self._normalize_document_text(candidate["text"])
            quality_score, quality_flags = self._score_candidate(
                document_type=candidate["document_type"],
                text=normalized_text,
                provenance=candidate["provenance"],
                metadata=candidate["metadata"],
            )
            dedupe_basis = self._normalize_document_text(candidate.get("dedupe_basis") or normalized_text)
            content_hash = hashlib.sha256(dedupe_basis.encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                quality_flags = tuple(sorted(set(quality_flags + ("duplicate_content",))))
                quality_score = max(0.0, quality_score - 0.4)

            document = NDCDerivedDocument(
                document_id=candidate["document_id"],
                document_type=candidate["document_type"],
                source_id=candidate["source_id"],
                project_id=candidate["project_id"],
                title=self._normalize_inline_text(candidate["title"]),
                text=normalized_text,
                metadata=candidate["metadata"],
                provenance=candidate["provenance"],
                quality_score=round(quality_score, 3),
                quality_flags=quality_flags,
                content_hash=content_hash,
            )
            if document.quality_score < QUALITY_THRESHOLD or "duplicate_content" in document.quality_flags:
                rejected.append(document.to_dict())
                continue
            admitted.append(document)
            seen_hashes.add(content_hash)

        return admitted, rejected

    def _persist_documents(
        self,
        output_dir: Path,
        documents: list[NDCDerivedDocument],
        rejected_documents: list[dict[str, Any]],
        *,
        source_id: str,
        project_id: str,
    ) -> None:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "built_at": _utc_now(),
            "source_id": source_id,
            "project_id": project_id,
            "document_count": len(documents),
            "rejected_count": len(rejected_documents),
            "document_types": sorted({document.document_type for document in documents}),
            "documents": [],
            "rejected_documents": rejected_documents,
        }

        for document in documents:
            document_dir = output_dir / document.document_type
            document_dir.mkdir(parents=True, exist_ok=True)
            relative_path = Path(document.document_type) / f"{document.document_id}.json"
            absolute_path = output_dir / relative_path
            absolute_path.write_text(
                json.dumps(document.to_dict(), indent=2, ensure_ascii=True, sort_keys=True),
                encoding="utf-8",
            )
            manifest["documents"].append(
                {
                    "document_id": document.document_id,
                    "document_type": document.document_type,
                    "path": str(relative_path),
                    "quality_score": document.quality_score,
                }
            )

        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )

    def _load_note_histories(self, source_id: str, project_id: str) -> dict[str, list[dict[str, Any]]]:
        with sqlite3.connect(self.normalized_store.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT event_id, note_id, action, note_scope, title, body, tags_json, linked_node_id,
                       source_ref, note_created_at, note_updated_at, sequence_number, created_at, receipt_id
                FROM notes
                WHERE source_id = ? AND project_id = ?
                ORDER BY sequence_number ASC, created_at ASC, event_id ASC
                """,
                (source_id, project_id),
            ).fetchall()

        histories: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            item = dict(row)
            item["tags"] = json.loads(item.pop("tags_json") or "[]")
            histories.setdefault(str(item["note_id"]), []).append(item)
        return histories

    def _load_tool_rows(self, source_id: str, project_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.normalized_store.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT event_id, tool_name, action, action_kind, context_scope, surface, result_summary,
                       result_status, result_count, related_node_id, target_ref, command_ref,
                       artifact_refs_json, sequence_number, created_at, receipt_id
                FROM tool_activity
                WHERE source_id = ? AND project_id = ?
                ORDER BY sequence_number ASC, created_at ASC, event_id ASC
                """,
                (source_id, project_id),
            ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["artifact_refs"] = json.loads(item.pop("artifact_refs_json") or "[]")
            results.append(item)
        return results

    def _candidate(
        self,
        *,
        document_id: str,
        document_type: str,
        source_id: str,
        project_id: str,
        title: str,
        text: str,
        metadata: dict[str, Any],
        provenance: dict[str, Any],
        dedupe_basis: str | None = None,
    ) -> dict[str, Any]:
        if document_type not in DOCUMENT_TYPES:
            raise NDCDerivedDocumentError(f"Unsupported derived document type '{document_type}'.")
        candidate = {
            "document_id": self._sanitize_id(document_id),
            "document_type": document_type,
            "source_id": source_id,
            "project_id": project_id,
            "title": self.minimizer.sanitize_text(title),
            "text": self.minimizer.sanitize_text(text),
            "metadata": self.minimizer.sanitize_json_value(self._clean_json_value(metadata)),
            "provenance": self.minimizer.sanitize_json_value(self._clean_json_value(provenance)),
        }
        if dedupe_basis is not None:
            candidate["dedupe_basis"] = self.minimizer.sanitize_text(dedupe_basis)
        return candidate

    def _timeline_line(self, entry: dict[str, Any]) -> str:
        payload = entry["payload"]
        family = entry["family"]
        action = entry["action"]
        subject = payload.get("node_id") or payload.get("edge_id") or payload.get("note_id") or payload.get("tool_name") or payload.get("snapshot_id") or payload.get("project_title") or entry["project_id"] if "project_id" in entry else "event"
        summary = [f"{entry['created_at']} [{entry['sequence_number']}] {family}.{action}"]
        if subject:
            summary.append(str(subject))
        if family == "node":
            details = []
            if payload.get("node_type"):
                details.append(f"type={payload['node_type']}")
            if payload.get("label"):
                details.append(f"label={payload['label']}")
            if payload.get("status"):
                details.append(f"status={payload['status']}")
            if payload.get("tags"):
                details.append("tags=" + ",".join(payload["tags"]))
            if details:
                summary.append("(" + "; ".join(details) + ")")
        elif family == "edge":
            summary.append(
                f"({payload.get('source_node_id')} -> {payload.get('target_node_id')})"
            )
        elif family == "note":
            details = []
            if payload.get("title"):
                details.append(f"title={payload['title']}")
            if payload.get("category"):
                details.append(f"category={payload['category']}")
            if payload.get("note_scope"):
                details.append(f"scope={payload['note_scope']}")
            if payload.get("linked_node_id"):
                details.append(f"linked_node={payload['linked_node_id']}")
            if details:
                summary.append("(" + "; ".join(details) + ")")
        elif family == "tool":
            details = [f"action_kind={payload.get('action_kind')}"]
            if payload.get("result_status"):
                details.append(f"status={payload['result_status']}")
            if payload.get("result_summary"):
                details.append(f"summary={payload['result_summary']}")
            summary.append("(" + "; ".join(details) + ")")
        elif family == "snapshot":
            summary.append(
                f"(trigger={payload.get('trigger')}; nodes={payload.get('node_count', 0)}; edges={payload.get('edge_count', 0)})"
            )
        elif family == "project":
            details = []
            if payload.get("project_title"):
                details.append(f"title={payload['project_title']}")
            if payload.get("reason"):
                details.append(f"reason={payload['reason']}")
            summary.append("(" + "; ".join(details) + ")" if details else "")
        return self._normalize_inline_text(" ".join(part for part in summary if part))

    def _tool_line(self, row: dict[str, Any]) -> str:
        details = [
            f"{row['created_at']} [{row['sequence_number']}] {row['tool_name']} {row['action_kind']}",
            f"scope={row['context_scope']}",
            f"surface={row['surface']}",
        ]
        if row.get("result_status"):
            details.append(f"status={row['result_status']}")
        if row.get("result_summary"):
            details.append(f"summary={row['result_summary']}")
        if row.get("result_count") is not None:
            details.append(f"count={row['result_count']}")
        if row.get("related_node_id"):
            details.append(f"node={row['related_node_id']}")
        return self._normalize_inline_text("; ".join(details))

    def _describe_node(self, node: dict[str, Any]) -> str:
        label = node.get("label") or node["node_id"]
        node_type = node.get("node_type") or "unknown"
        status = f", status={node['status']}" if node.get("status") else ""
        return f"{label} [{node_type}{status}]"

    def _split_text_into_chunks(self, text: str, *, max_chars: int) -> list[str]:
        normalized = self._normalize_document_text(text)
        paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()] or [normalized]
        chunks: list[str] = []
        current_parts: list[str] = []

        for paragraph in paragraphs:
            projected = "\n\n".join(current_parts + [paragraph]).strip()
            if current_parts and len(projected) > max_chars:
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = [paragraph]
                continue
            if len(paragraph) > max_chars:
                if current_parts:
                    chunks.append("\n\n".join(current_parts).strip())
                    current_parts = []
                chunks.extend(self._split_long_line(paragraph, max_chars=max_chars))
                continue
            current_parts.append(paragraph)

        if current_parts:
            chunks.append("\n\n".join(current_parts).strip())
        return [chunk for chunk in chunks if chunk]

    def _split_long_line(self, text: str, *, max_chars: int) -> list[str]:
        words = text.split()
        if not words:
            return [text[:max_chars]]
        pieces: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                pieces.append(current)
            current = word
        if current:
            pieces.append(current)
        return pieces

    def _score_candidate(
        self,
        *,
        document_type: str,
        text: str,
        provenance: dict[str, Any],
        metadata: dict[str, Any],
    ) -> tuple[float, tuple[str, ...]]:
        score = 0.6
        flags: list[str] = []
        stripped = text.strip()
        char_count = len(stripped)
        words = [word for word in stripped.lower().split() if word]
        unique_ratio = len(set(words)) / len(words) if words else 0.0
        event_count = len(provenance.get("event_ids", []))

        if char_count == 0:
            flags.append("empty_text")
            score -= 0.8
        elif char_count < 80:
            flags.append("too_short")
            score -= 0.45
        elif char_count >= 200:
            score += 0.12
        else:
            score += 0.05

        if event_count == 0:
            flags.append("missing_provenance")
            score -= 0.25
        elif event_count >= 3:
            score += 0.1
        else:
            score += 0.04

        if unique_ratio < 0.45:
            flags.append("repetitive_text")
            score -= 0.12
        else:
            score += 0.05

        if document_type == "project_summary":
            score += 0.08
        if document_type == "timeline_chunk" and metadata.get("event_count", 0) < 2:
            flags.append("low_signal_timeline")
            score -= 0.15
        if document_type == "note_context_chunk" and not metadata.get("note_id"):
            flags.append("missing_note_anchor")
            score -= 0.2
        if document_type == "note_context_chunk" and int(metadata.get("content_char_count", 0) or 0) < 30:
            flags.append("low_signal_note_chunk")
            score -= 0.28
        if document_type == "tool_context_chunk":
            if not metadata.get("tool_name"):
                flags.append("missing_tool_anchor")
                score -= 0.2
            if int(metadata.get("result_summary_count", 0) or 0) == 0 and event_count < 2:
                flags.append("low_signal_tool_chunk")
                score -= 0.3

        return max(0.0, min(score, 1.0)), tuple(sorted(set(flags)))

    def _normalize_document_text(self, text: str) -> str:
        normalized_lines = [self._normalize_inline_text(line) for line in str(text or "").splitlines()]
        lines = [line for line in normalized_lines if line]
        if not lines:
            return ""
        compact_lines: list[str] = []
        previous_blank = False
        for line in lines:
            if line:
                compact_lines.append(line)
                previous_blank = False
            elif not previous_blank:
                compact_lines.append("")
                previous_blank = True
        return "\n".join(compact_lines).strip()

    def _normalize_inline_text(self, text: str) -> str:
        return " ".join(str(text or "").replace("\r", "\n").split())

    def _clean_json_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._clean_json_value(item) for key, item in value.items() if item is not None}
        if isinstance(value, (list, tuple, set)):
            return [self._clean_json_value(item) for item in value if item is not None]
        return value

    def _sequence_range(self, rows: list[dict[str, Any]]) -> dict[str, int] | None:
        if not rows:
            return None
        sequence_numbers = [int(row["sequence_number"]) for row in rows]
        return {"start": min(sequence_numbers), "end": max(sequence_numbers)}

    def _dedupe_preserve_order(self, values) -> list[Any]:
        seen = set()
        result: list[Any] = []
        for value in values:
            if value in seen or value is None:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _sanitize_id(self, value: str) -> str:
        cleaned = []
        for char in str(value):
            if char.isalnum() or char in {"-", "_", ":"}:
                cleaned.append(char)
            else:
                cleaned.append("_")
        return "".join(cleaned)

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
            handle.write("\n")


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
