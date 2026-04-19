from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from features.ndc.core.schema import NDCEvent, validate_ndc_event
from features.ndc.server.derived_documents import NDCDerivedDocumentPipeline
from features.ndc.server.governance import NDCGovernanceController, NDCSensitiveDataMinimizer
from features.ndc.server.normalized_store import NDCNormalizedStore, NDCNormalizedStoreError, NDCSequenceConflictError
from features.ndc.server.rollout import NDCRolloutReadinessController


class NDCRawIngestError(RuntimeError):
    """Raised when the raw ingest store cannot persist or classify a batch."""


class NDCEventConflictError(NDCRawIngestError):
    """Raised when an existing event id is replayed with different contents."""


@dataclass(frozen=True)
class IngestReceipt:
    receipt_id: str
    received_at: str
    accepted_count: int
    duplicate_count: int
    accepted_event_ids: tuple[str, ...]
    duplicate_event_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "received_at": self.received_at,
            "accepted_count": self.accepted_count,
            "duplicate_count": self.duplicate_count,
            "accepted_event_ids": list(self.accepted_event_ids),
            "duplicate_event_ids": list(self.duplicate_event_ids),
        }


class NDCRawIngestStore:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.batches_path = self.base_dir / "raw_ingest_batches.jsonl"
        self.network_metadata_path = self.base_dir / "network_observations.jsonl"
        self.index_path = self.base_dir / "raw_ingest_index.sqlite3"
        self.normalized_store = NDCNormalizedStore(self.base_dir / "normalized_store.sqlite3")
        self.minimizer = NDCSensitiveDataMinimizer()
        self.derived_pipeline = NDCDerivedDocumentPipeline(
            self.base_dir,
            normalized_store=self.normalized_store,
            minimizer=self.minimizer,
        )
        self.governance = NDCGovernanceController(
            self.base_dir,
            normalized_store=self.normalized_store,
            derived_pipeline=self.derived_pipeline,
        )
        self.rollout = NDCRolloutReadinessController(self.base_dir, governance=self.governance)
        self._init_db()

    def accept_batch(
        self,
        raw_events: list[dict[str, Any]],
        *,
        auth_key_id: str,
        public_ip: str | None,
        user_agent: str | None,
        request_metadata: dict[str, Any] | None = None,
    ) -> IngestReceipt:
        receipt_id = f"receipt-{uuid4()}"
        received_at = _utc_now()
        normalized_events = [validate_ndc_event(event) for event in raw_events]
        accepted_events: list[NDCEvent] = []
        duplicate_event_ids: list[str] = []

        with sqlite3.connect(self.index_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for event in normalized_events:
                    row = connection.execute(
                        """
                        SELECT content_hash
                        FROM ingested_events
                        WHERE event_id = ?
                        """,
                        (event.event_id,),
                    ).fetchone()
                    if row is not None:
                        existing_hash = str(row[0] or "")
                        if existing_hash != event.content_hash:
                            raise NDCEventConflictError(
                                f"event_id '{event.event_id}' already exists with a different content_hash."
                            )
                        duplicate_event_ids.append(event.event_id)
                        continue

                    connection.execute(
                        """
                        INSERT INTO ingested_events (
                            event_id,
                            content_hash,
                            source_id,
                            project_id,
                            sequence_number,
                            schema_version,
                            family,
                            action,
                            receipt_id,
                            received_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_id,
                            event.content_hash,
                            event.source_id,
                            event.project_id,
                            event.sequence_number,
                            event.schema_version,
                            event.family.value,
                            event.action,
                            receipt_id,
                            received_at,
                        ),
                    )
                    accepted_events.append(event)
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                message = str(exc).lower()
                if "ingested_events.source_id, ingested_events.project_id, ingested_events.sequence_number" in message:
                    raise NDCEventConflictError(
                        "source_id/project_id/sequence_number must be unique for accepted events."
                    ) from exc
                raise NDCRawIngestError(str(exc)) from exc

        accepted_event_ids = [event.event_id for event in accepted_events]
        receipt = IngestReceipt(
            receipt_id=receipt_id,
            received_at=received_at,
            accepted_count=len(accepted_events),
            duplicate_count=len(duplicate_event_ids),
            accepted_event_ids=tuple(accepted_event_ids),
            duplicate_event_ids=tuple(duplicate_event_ids),
        )
        try:
            self.normalized_store.apply_batch(
                accepted_events,
                receipt_id=receipt.receipt_id,
                received_at=receipt.received_at,
            )
        except (NDCSequenceConflictError, NDCNormalizedStoreError) as exc:
            raise NDCEventConflictError(str(exc)) from exc
        self._append_network_observation(
            receipt=receipt,
            auth_key_id=auth_key_id,
            public_ip=public_ip,
            user_agent=user_agent,
            request_metadata=request_metadata,
            request_event_count=len(normalized_events),
        )
        if accepted_events:
            self._append_batch_record(
                receipt=receipt,
                auth_key_id=auth_key_id,
                request_metadata=request_metadata,
                accepted_events=accepted_events,
            )
            for source_id, project_id in sorted(
                {
                    (event.source_id, event.project_id)
                    for event in accepted_events
                }
            ):
                try:
                    self.derived_pipeline.rebuild_project_documents(
                        project_id,
                        source_id=source_id,
                    )
                except Exception as exc:
                    self.derived_pipeline.record_failure(
                        source_id=source_id,
                        project_id=project_id,
                        error=exc,
                    )
        dashboard = self.governance.refresh_reports()
        self.rollout.refresh_review(dashboard)
        return receipt

    def seen_event_count(self) -> int:
        with sqlite3.connect(self.index_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM ingested_events").fetchone()
        return int(row[0] or 0)

    def recent_batches(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._read_jsonl_tail(self.batches_path, limit=max(1, int(limit)))
        return list(reversed(rows))

    def recent_network_observations(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._read_jsonl_tail(self.network_metadata_path, limit=max(1, int(limit)))
        return list(reversed(rows))

    def list_projects(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with sqlite3.connect(self.normalized_store.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT source_id, project_id, first_seen_at, last_seen_at, first_receipt_id,
                       last_receipt_id, latest_title, latest_file_path, lifecycle_status, event_count
                FROM projects
                ORDER BY last_seen_at DESC, source_id ASC, project_id ASC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_batches_for_project(
        self,
        source_id: str,
        project_id: str,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        matched: list[dict[str, Any]] = []
        for batch in reversed(self._read_jsonl_tail(self.batches_path, limit=500)):
            events = [
                event
                for event in batch.get("events", [])
                if event.get("source_id") == source_id and event.get("project_id") == project_id
            ]
            if not events:
                continue
            matched.append(
                {
                    "receipt_id": batch.get("receipt_id"),
                    "received_at": batch.get("received_at"),
                    "accepted_count": len(events),
                    "event_ids": [event.get("event_id") for event in events],
                    "families": sorted({str(event.get("family") or "") for event in events if event.get("family")}),
                }
            )
            if len(matched) >= max(1, int(limit)):
                break
        return matched

    def read_project_manifest(self, source_id: str, project_id: str) -> dict[str, Any] | None:
        manifest_path = self.base_dir / "derived_documents" / str(source_id) / str(project_id) / "manifest.json"
        if not manifest_path.exists():
            return None
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _append_batch_record(
        self,
        *,
        receipt: IngestReceipt,
        auth_key_id: str,
        request_metadata: dict[str, Any] | None,
        accepted_events: list[NDCEvent],
    ) -> None:
        record = {
            **receipt.to_dict(),
            "auth_key_id": auth_key_id,
            "request_metadata": dict(request_metadata or {}),
            "events": [event.to_dict() for event in accepted_events],
        }
        self._append_jsonl(self.batches_path, record)

    def _append_network_observation(
        self,
        *,
        receipt: IngestReceipt,
        auth_key_id: str,
        public_ip: str | None,
        user_agent: str | None,
        request_metadata: dict[str, Any] | None,
        request_event_count: int,
    ) -> None:
        record = {
            "receipt_id": receipt.receipt_id,
            "observed_at": receipt.received_at,
            "auth_key_id": auth_key_id,
            "public_ip": str(public_ip or "").strip() or None,
            "user_agent": str(user_agent or "").strip() or None,
            "request_event_count": int(request_event_count),
            "request_metadata": dict(request_metadata or {}),
        }
        self._append_jsonl(self.network_metadata_path, record)

    def _init_db(self) -> None:
        with sqlite3.connect(self.index_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingested_events (
                    event_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    schema_version TEXT NOT NULL,
                    family TEXT NOT NULL,
                    action TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ingested_events_source_project
                ON ingested_events(source_id, project_id, sequence_number)
                """
            )
            connection.commit()

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
            handle.write("\n")

    def _read_jsonl_tail(self, path: Path, *, limit: int) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        if limit <= 0:
            return rows
        return rows[-limit:]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
