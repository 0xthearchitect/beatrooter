from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

from features.ndc.core.schema import NDCEvent


class NDCNormalizedStoreError(RuntimeError):
    """Raised when the normalized store cannot persist or reconstruct data."""


class NDCSequenceConflictError(NDCNormalizedStoreError):
    """Raised when multiple events reuse the same source/project sequence number."""


@dataclass(frozen=True)
class ProjectTimelineEntry:
    event_id: str
    family: str
    action: str
    created_at: str
    sequence_number: int
    receipt_id: str
    payload: dict[str, Any]
    state: dict[str, Any]


class NDCNormalizedStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def apply_batch(
        self,
        events: list[NDCEvent],
        *,
        receipt_id: str,
        received_at: str,
    ) -> None:
        if not events:
            return

        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for batch_event_index, event in enumerate(events):
                    self._insert_event(
                        connection,
                        event,
                        receipt_id=receipt_id,
                        received_at=received_at,
                        batch_event_index=batch_event_index,
                    )
                    self._upsert_source(connection, event, receipt_id=receipt_id)
                    self._upsert_project(connection, event, receipt_id=receipt_id)
                    self._insert_provenance(
                        connection,
                        record_type="source",
                        record_id=event.source_id,
                        event=event,
                        receipt_id=receipt_id,
                        batch_event_index=batch_event_index,
                    )
                    self._insert_provenance(
                        connection,
                        record_type="project",
                        record_id=self._project_record_id(event.source_id, event.project_id),
                        event=event,
                        receipt_id=receipt_id,
                        batch_event_index=batch_event_index,
                    )
                    self._insert_provenance(
                        connection,
                        record_type="event",
                        record_id=event.event_id,
                        event=event,
                        receipt_id=receipt_id,
                        batch_event_index=batch_event_index,
                    )

                    if event.family.value == "note":
                        self._insert_note(connection, event, receipt_id=receipt_id)
                        self._insert_provenance(
                            connection,
                            record_type="note",
                            record_id=self._note_record_id(event.source_id, event.project_id, event.payload["note_id"]),
                            event=event,
                            receipt_id=receipt_id,
                            batch_event_index=batch_event_index,
                        )
                    elif event.family.value == "tool":
                        self._insert_tool_activity(connection, event, receipt_id=receipt_id)
                        self._insert_provenance(
                            connection,
                            record_type="tool_activity",
                            record_id=event.event_id,
                            event=event,
                            receipt_id=receipt_id,
                            batch_event_index=batch_event_index,
                        )
                    elif event.family.value == "snapshot":
                        self._insert_snapshot(connection, event, receipt_id=receipt_id)
                        self._insert_provenance(
                            connection,
                            record_type="snapshot",
                            record_id=self._snapshot_record_id(
                                event.source_id,
                                event.project_id,
                                event.payload["snapshot_id"],
                            ),
                            event=event,
                            receipt_id=receipt_id,
                            batch_event_index=batch_event_index,
                        )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                message = str(exc).lower()
                if "events.source_id, events.project_id, events.sequence_number" in message:
                    raise NDCSequenceConflictError(
                        "source_id/project_id/sequence_number must be unique in the normalized store."
                    ) from exc
                if "events.event_id" in message:
                    raise NDCNormalizedStoreError(
                        "event_id already exists in the normalized store."
                    ) from exc
                raise NDCNormalizedStoreError(str(exc)) from exc

    def list_provenance(self, record_type: str, record_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT record_type, record_id, event_id, receipt_id, batch_event_index, linked_at
                FROM normalized_provenance
                WHERE record_type = ? AND record_id = ?
                ORDER BY linked_at, batch_event_index
                """,
                (str(record_type), str(record_id)),
            ).fetchall()
        return [dict(row) for row in rows]

    def reconstruct_project_timeline(
        self,
        project_id: str,
        *,
        source_id: str | None = None,
        up_to_sequence_number: int | None = None,
    ) -> dict[str, Any]:
        resolved_source_id = self._resolve_project_source(project_id, source_id=source_id)
        params: list[Any] = [resolved_source_id, project_id]
        sequence_clause = ""
        if up_to_sequence_number is not None:
            sequence_clause = "AND sequence_number <= ?"
            params.append(int(up_to_sequence_number))

        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                f"""
                SELECT event_id, family, action, created_at, sequence_number, receipt_id, payload_json
                FROM events
                WHERE source_id = ? AND project_id = ?
                {sequence_clause}
                ORDER BY sequence_number ASC, created_at ASC, event_id ASC
                """,
                tuple(params),
            ).fetchall()

        state = {
            "project": {
                "project_id": project_id,
                "source_id": resolved_source_id,
                "project_title": None,
                "file_path": None,
                "lifecycle_status": None,
                "reason": None,
                "schema_from": None,
                "schema_to": None,
            },
            "nodes": {},
            "edges": {},
            "notes": {},
            "tool_activity": [],
            "snapshots": [],
        }
        entries: list[ProjectTimelineEntry] = []

        for row in rows:
            payload = json.loads(row["payload_json"])
            self._apply_event_to_state(
                state,
                family=str(row["family"]),
                action=str(row["action"]),
                payload=payload,
                event_id=str(row["event_id"]),
                created_at=str(row["created_at"]),
                sequence_number=int(row["sequence_number"]),
                receipt_id=str(row["receipt_id"]),
            )
            entries.append(
                ProjectTimelineEntry(
                    event_id=str(row["event_id"]),
                    family=str(row["family"]),
                    action=str(row["action"]),
                    created_at=str(row["created_at"]),
                    sequence_number=int(row["sequence_number"]),
                    receipt_id=str(row["receipt_id"]),
                    payload=deepcopy(payload),
                    state=deepcopy(state),
                )
            )

        return {
            "source_id": resolved_source_id,
            "project_id": project_id,
            "entry_count": len(entries),
            "entries": [
                {
                    "event_id": entry.event_id,
                    "family": entry.family,
                    "action": entry.action,
                    "created_at": entry.created_at,
                    "sequence_number": entry.sequence_number,
                    "receipt_id": entry.receipt_id,
                    "payload": entry.payload,
                    "state": entry.state,
                }
                for entry in entries
            ],
            "final_state": deepcopy(state),
        }

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        event: NDCEvent,
        *,
        receipt_id: str,
        received_at: str,
        batch_event_index: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO events (
                event_id,
                source_id,
                project_id,
                family,
                action,
                created_at,
                received_at,
                sequence_number,
                schema_version,
                content_hash,
                payload_json,
                receipt_id,
                batch_event_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.source_id,
                event.project_id,
                event.family.value,
                event.action,
                event.created_at,
                received_at,
                event.sequence_number,
                event.schema_version,
                event.content_hash,
                json.dumps(event.payload, ensure_ascii=True, sort_keys=True),
                receipt_id,
                int(batch_event_index),
            ),
        )

    def _upsert_source(
        self,
        connection: sqlite3.Connection,
        event: NDCEvent,
        *,
        receipt_id: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO sources (
                source_id,
                first_seen_at,
                last_seen_at,
                first_receipt_id,
                last_receipt_id,
                last_schema_version,
                event_count
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(source_id) DO UPDATE SET
                last_seen_at = excluded.last_seen_at,
                last_receipt_id = excluded.last_receipt_id,
                last_schema_version = excluded.last_schema_version,
                event_count = sources.event_count + 1
            """,
            (
                event.source_id,
                event.created_at,
                event.created_at,
                receipt_id,
                receipt_id,
                event.schema_version,
            ),
        )

    def _upsert_project(
        self,
        connection: sqlite3.Connection,
        event: NDCEvent,
        *,
        receipt_id: str,
    ) -> None:
        payload = event.payload
        project_title = payload.get("project_title") if event.family.value == "project" else None
        file_path = payload.get("file_path") if event.family.value == "project" else None
        lifecycle_status = event.action if event.family.value == "project" else None
        connection.execute(
            """
            INSERT INTO projects (
                source_id,
                project_id,
                first_seen_at,
                last_seen_at,
                first_receipt_id,
                last_receipt_id,
                latest_title,
                latest_file_path,
                lifecycle_status,
                event_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(source_id, project_id) DO UPDATE SET
                last_seen_at = excluded.last_seen_at,
                last_receipt_id = excluded.last_receipt_id,
                latest_title = COALESCE(excluded.latest_title, projects.latest_title),
                latest_file_path = COALESCE(excluded.latest_file_path, projects.latest_file_path),
                lifecycle_status = COALESCE(excluded.lifecycle_status, projects.lifecycle_status),
                event_count = projects.event_count + 1
            """,
            (
                event.source_id,
                event.project_id,
                event.created_at,
                event.created_at,
                receipt_id,
                receipt_id,
                project_title,
                file_path,
                lifecycle_status,
            ),
        )

    def _insert_note(
        self,
        connection: sqlite3.Connection,
        event: NDCEvent,
        *,
        receipt_id: str,
    ) -> None:
        payload = event.payload
        connection.execute(
            """
            INSERT INTO notes (
                event_id,
                source_id,
                project_id,
                note_id,
                note_scope,
                action,
                title,
                body,
                format,
                category,
                tags_json,
                linked_node_id,
                source_ref,
                note_created_at,
                note_updated_at,
                is_deleted,
                sequence_number,
                created_at,
                receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.source_id,
                event.project_id,
                payload["note_id"],
                payload["note_scope"],
                event.action,
                payload.get("title"),
                payload.get("body"),
                payload.get("format"),
                payload.get("category"),
                json.dumps(payload.get("tags", []), ensure_ascii=True, sort_keys=True),
                payload.get("linked_node_id"),
                payload.get("source_ref"),
                payload.get("created_at"),
                payload.get("updated_at"),
                int(event.action == "deleted"),
                event.sequence_number,
                event.created_at,
                receipt_id,
            ),
        )

    def _insert_tool_activity(
        self,
        connection: sqlite3.Connection,
        event: NDCEvent,
        *,
        receipt_id: str,
    ) -> None:
        payload = event.payload
        connection.execute(
            """
            INSERT INTO tool_activity (
                event_id,
                source_id,
                project_id,
                tool_name,
                action,
                action_kind,
                context_scope,
                surface,
                result_summary,
                result_status,
                result_count,
                related_node_id,
                target_ref,
                command_ref,
                artifact_refs_json,
                sequence_number,
                created_at,
                receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.source_id,
                event.project_id,
                payload["tool_name"],
                event.action,
                payload["action_kind"],
                payload["context_scope"],
                payload["surface"],
                payload.get("result_summary"),
                payload.get("result_status"),
                payload.get("result_count"),
                payload.get("related_node_id"),
                payload.get("target_ref"),
                payload.get("command_ref"),
                json.dumps(payload.get("artifact_refs", []), ensure_ascii=True, sort_keys=True),
                event.sequence_number,
                event.created_at,
                receipt_id,
            ),
        )

    def _insert_snapshot(
        self,
        connection: sqlite3.Connection,
        event: NDCEvent,
        *,
        receipt_id: str,
    ) -> None:
        payload = event.payload
        connection.execute(
            """
            INSERT INTO snapshots (
                event_id,
                source_id,
                project_id,
                snapshot_id,
                action,
                trigger,
                capture_kind,
                node_count,
                edge_count,
                summary,
                sequence_number,
                created_at,
                receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.source_id,
                event.project_id,
                payload["snapshot_id"],
                event.action,
                payload["trigger"],
                payload["capture_kind"],
                payload.get("node_count"),
                payload.get("edge_count"),
                payload.get("summary"),
                event.sequence_number,
                event.created_at,
                receipt_id,
            ),
        )

    def _insert_provenance(
        self,
        connection: sqlite3.Connection,
        *,
        record_type: str,
        record_id: str,
        event: NDCEvent,
        receipt_id: str,
        batch_event_index: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO normalized_provenance (
                record_type,
                record_id,
                event_id,
                receipt_id,
                batch_event_index,
                linked_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record_type,
                record_id,
                event.event_id,
                receipt_id,
                int(batch_event_index),
                event.created_at,
            ),
        )

    def _resolve_project_source(self, project_id: str, *, source_id: str | None) -> str:
        if source_id is not None:
            return str(source_id)

        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT source_id
                FROM projects
                WHERE project_id = ?
                ORDER BY last_seen_at DESC, source_id ASC
                """,
                (str(project_id),),
            ).fetchall()

        source_ids = [str(row[0]) for row in rows]
        if not source_ids:
            raise NDCNormalizedStoreError(f"Unknown project_id '{project_id}'.")
        if len(set(source_ids)) > 1:
            raise NDCNormalizedStoreError(
                f"project_id '{project_id}' exists for multiple sources; supply source_id explicitly."
            )
        return source_ids[0]

    def _apply_event_to_state(
        self,
        state: dict[str, Any],
        *,
        family: str,
        action: str,
        payload: dict[str, Any],
        event_id: str,
        created_at: str,
        sequence_number: int,
        receipt_id: str,
    ) -> None:
        if family == "project":
            project_state = state["project"]
            project_state["lifecycle_status"] = action
            for field_name in ("project_title", "file_path", "reason", "schema_from", "schema_to"):
                if field_name in payload:
                    project_state[field_name] = payload.get(field_name)
            project_state["last_event_id"] = event_id
            project_state["last_receipt_id"] = receipt_id
            return

        if family == "node":
            node_id = payload["node_id"]
            if action == "deleted":
                state["nodes"].pop(node_id, None)
                edge_ids = [
                    edge_id
                    for edge_id, edge in state["edges"].items()
                    if edge.get("source_node_id") == node_id or edge.get("target_node_id") == node_id
                ]
                for edge_id in edge_ids:
                    state["edges"].pop(edge_id, None)
                return
            node_state = state["nodes"].get(node_id, {"node_id": node_id})
            node_state.update(payload)
            node_state["last_action"] = action
            node_state["last_event_id"] = event_id
            node_state["last_sequence_number"] = sequence_number
            state["nodes"][node_id] = node_state
            return

        if family == "edge":
            edge_id = payload["edge_id"]
            if action == "deleted":
                state["edges"].pop(edge_id, None)
                return
            edge_state = state["edges"].get(edge_id, {"edge_id": edge_id})
            edge_state.update(payload)
            edge_state["last_action"] = action
            edge_state["last_event_id"] = event_id
            edge_state["last_sequence_number"] = sequence_number
            state["edges"][edge_id] = edge_state
            return

        if family == "note":
            note_id = payload["note_id"]
            note_state = state["notes"].get(note_id, {"note_id": note_id})
            note_state["note_scope"] = payload["note_scope"]
            for field_name in (
                "title",
                "body",
                "format",
                "category",
                "linked_node_id",
                "source_ref",
                "created_at",
                "updated_at",
            ):
                if field_name in payload:
                    note_state[field_name] = payload.get(field_name)
            if "tags" in payload:
                note_state["tags"] = list(payload.get("tags", []))
            if action == "unlinked":
                note_state["linked_node_id"] = None
            note_state["deleted"] = action == "deleted"
            note_state["last_action"] = action
            note_state["last_event_id"] = event_id
            note_state["last_sequence_number"] = sequence_number
            state["notes"][note_id] = note_state
            return

        if family == "tool":
            tool_state = {
                "event_id": event_id,
                "created_at": created_at,
                "sequence_number": sequence_number,
                "receipt_id": receipt_id,
                **payload,
            }
            state["tool_activity"].append(tool_state)
            return

        if family == "snapshot":
            snapshot_state = {
                "event_id": event_id,
                "created_at": created_at,
                "sequence_number": sequence_number,
                "receipt_id": receipt_id,
                **payload,
            }
            state["snapshots"].append(snapshot_state)

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    first_receipt_id TEXT NOT NULL,
                    last_receipt_id TEXT NOT NULL,
                    last_schema_version TEXT NOT NULL,
                    event_count INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    source_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    first_receipt_id TEXT NOT NULL,
                    last_receipt_id TEXT NOT NULL,
                    latest_title TEXT,
                    latest_file_path TEXT,
                    lifecycle_status TEXT,
                    event_count INTEGER NOT NULL,
                    PRIMARY KEY (source_id, project_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    family TEXT NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    schema_version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    batch_event_index INTEGER NOT NULL,
                    UNIQUE(source_id, project_id, sequence_number)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    note_id TEXT NOT NULL,
                    note_scope TEXT NOT NULL,
                    action TEXT NOT NULL,
                    title TEXT,
                    body TEXT,
                    format TEXT,
                    category TEXT,
                    tags_json TEXT NOT NULL,
                    linked_node_id TEXT,
                    source_ref TEXT,
                    note_created_at TEXT,
                    note_updated_at TEXT,
                    is_deleted INTEGER NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_activity (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    action_kind TEXT NOT NULL,
                    context_scope TEXT NOT NULL,
                    surface TEXT NOT NULL,
                    result_summary TEXT,
                    result_status TEXT,
                    result_count INTEGER,
                    related_node_id TEXT,
                    target_ref TEXT,
                    command_ref TEXT,
                    artifact_refs_json TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    capture_kind TEXT NOT NULL,
                    node_count INTEGER,
                    edge_count INTEGER,
                    summary TEXT,
                    sequence_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS normalized_provenance (
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    batch_event_index INTEGER NOT NULL,
                    linked_at TEXT NOT NULL,
                    PRIMARY KEY (record_type, record_id, event_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_project_timeline
                ON events(source_id, project_id, sequence_number, created_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_notes_project_note
                ON notes(source_id, project_id, note_id, sequence_number)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tool_activity_project
                ON tool_activity(source_id, project_id, sequence_number)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_snapshots_project
                ON snapshots(source_id, project_id, sequence_number)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_provenance_record
                ON normalized_provenance(record_type, record_id, linked_at)
                """
            )
            connection.commit()

    @staticmethod
    def _project_record_id(source_id: str, project_id: str) -> str:
        return f"{source_id}:{project_id}"

    @staticmethod
    def _note_record_id(source_id: str, project_id: str, note_id: str) -> str:
        return f"{source_id}:{project_id}:{note_id}"

    @staticmethod
    def _snapshot_record_id(source_id: str, project_id: str, snapshot_id: str) -> str:
        return f"{source_id}:{project_id}:{snapshot_id}"
