from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from .schema import NDCEvent, NDCEventFamily, validate_ndc_event


@dataclass(frozen=True)
class QueuedNDCEvent:
    queue_id: int
    event: NDCEvent
    enqueued_at: str
    available_at: str
    attempt_count: int
    last_attempt_at: str | None
    last_error: str | None


class NDCQueueStorage:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def enqueue(self, event: NDCEvent) -> bool:
        now = _utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO queue_events (
                    event_id,
                    source_id,
                    project_id,
                    family,
                    action,
                    created_at,
                    schema_version,
                    content_hash,
                    sequence_number,
                    payload_json,
                    enqueued_at,
                    available_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.source_id,
                    event.project_id,
                    event.family.value,
                    event.action,
                    event.created_at,
                    event.schema_version,
                    event.content_hash,
                    event.sequence_number,
                    json.dumps(event.payload, sort_keys=True, ensure_ascii=True),
                    now,
                    now,
                ),
            )
            inserted = cursor.rowcount > 0
            connection.commit()
            return inserted

    def get_or_create_source_id(self) -> str:
        existing = self.get_state("source_id")
        if existing:
            return existing

        source_id = f"source-{uuid4()}"
        self.set_state("source_id", source_id)
        return source_id

    def next_sequence_number(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT value FROM queue_state WHERE key = ?",
                ("next_sequence_number",),
            )
            row = cursor.fetchone()
            current = int(row[0]) if row else 1
            connection.execute(
                """
                INSERT INTO queue_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("next_sequence_number", str(current + 1)),
            )
            connection.commit()
            return current

    def fetch_ready_batch(self, limit: int) -> list[QueuedNDCEvent]:
        now = _utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    queue_id,
                    event_id,
                    source_id,
                    project_id,
                    family,
                    action,
                    created_at,
                    schema_version,
                    content_hash,
                    sequence_number,
                    payload_json,
                    enqueued_at,
                    available_at,
                    attempt_count,
                    last_attempt_at,
                    last_error
                FROM queue_events
                WHERE available_at <= ?
                ORDER BY sequence_number ASC, queue_id ASC
                LIMIT ?
                """,
                (now, int(limit)),
            )
            rows = cursor.fetchall()

        ready: list[QueuedNDCEvent] = []
        for row in rows:
            payload = {
                "family": row["family"],
                "action": row["action"],
                "event_id": row["event_id"],
                "source_id": row["source_id"],
                "project_id": row["project_id"],
                "created_at": row["created_at"],
                "schema_version": row["schema_version"],
                "payload": json.loads(row["payload_json"]),
                "content_hash": row["content_hash"],
                "sequence_number": row["sequence_number"],
            }
            ready.append(
                QueuedNDCEvent(
                    queue_id=row["queue_id"],
                    event=validate_ndc_event(payload),
                    enqueued_at=row["enqueued_at"],
                    available_at=row["available_at"],
                    attempt_count=row["attempt_count"],
                    last_attempt_at=row["last_attempt_at"],
                    last_error=row["last_error"],
                )
            )
        return ready

    def acknowledge_batch(
        self,
        queue_ids: list[int],
        *,
        ack_id: str,
        transport_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not queue_ids:
            return

        metadata_json = json.dumps(metadata or {}, sort_keys=True, ensure_ascii=True)
        placeholders = ", ".join("?" for _ in queue_ids)
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO queue_receipts (
                    ack_id,
                    received_at,
                    event_count,
                    transport_name,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (ack_id, now, len(queue_ids), transport_name, metadata_json),
            )
            connection.execute(
                f"DELETE FROM queue_events WHERE queue_id IN ({placeholders})",
                queue_ids,
            )
            connection.execute(
                """
                INSERT INTO queue_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("last_ack_id", ack_id),
            )
            connection.execute(
                """
                INSERT INTO queue_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("last_flush_at", now),
            )
            connection.execute(
                """
                INSERT INTO queue_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("last_flush_error", ""),
            )
            connection.commit()

    def mark_batch_failed(
        self,
        queue_ids: list[int],
        *,
        error: str,
        retry_after_seconds: int,
    ) -> None:
        if not queue_ids:
            return

        now = _utc_now()
        retry_at = _utc_after_seconds(retry_after_seconds)
        placeholders = ", ".join("?" for _ in queue_ids)
        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE queue_events
                SET
                    attempt_count = attempt_count + 1,
                    last_attempt_at = ?,
                    available_at = ?,
                    last_error = ?
                WHERE queue_id IN ({placeholders})
                """,
                [now, retry_at, error, *queue_ids],
            )
            connection.execute(
                """
                INSERT INTO queue_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("last_flush_at", now),
            )
            connection.execute(
                """
                INSERT INTO queue_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("last_flush_error", error),
            )
            connection.commit()

    def health_snapshot(self) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as connection:
            total_pending = connection.execute(
                "SELECT COUNT(*) FROM queue_events"
            ).fetchone()[0]
            ready_count = connection.execute(
                "SELECT COUNT(*) FROM queue_events WHERE available_at <= ?",
                (now,),
            ).fetchone()[0]
            retrying_count = connection.execute(
                "SELECT COUNT(*) FROM queue_events WHERE attempt_count > 0",
            ).fetchone()[0]
            oldest_row = connection.execute(
                "SELECT enqueued_at FROM queue_events ORDER BY enqueued_at ASC LIMIT 1"
            ).fetchone()
            next_retry_row = connection.execute(
                """
                SELECT available_at
                FROM queue_events
                WHERE available_at > ?
                ORDER BY available_at ASC
                LIMIT 1
                """,
                (now,),
            ).fetchone()
            receipt_count = connection.execute(
                "SELECT COUNT(*) FROM queue_receipts"
            ).fetchone()[0]

        oldest_pending_age_seconds = None
        if oldest_row is not None:
            oldest_pending_age_seconds = int(
                max(
                    0.0,
                    (
                        _parse_utc(now) - _parse_utc(oldest_row[0])
                    ).total_seconds(),
                )
            )

        return {
            "db_path": str(self.db_path),
            "source_id": self.get_or_create_source_id(),
            "total_pending": int(total_pending),
            "ready_count": int(ready_count),
            "retrying_count": int(retrying_count),
            "receipt_count": int(receipt_count),
            "oldest_pending_age_seconds": oldest_pending_age_seconds,
            "next_retry_at": next_retry_row[0] if next_retry_row is not None else None,
            "last_ack_id": self.get_state("last_ack_id"),
            "last_flush_at": self.get_state("last_flush_at"),
            "last_flush_error": self.get_state("last_flush_error"),
        }

    def get_state(self, key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM queue_state WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def set_state(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO queue_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            connection.commit()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_events (
                    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    source_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    family TEXT NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    enqueued_at TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TEXT,
                    last_error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_events_available
                ON queue_events (available_at, queue_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_events_sequence
                ON queue_events (sequence_number, queue_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_receipts (
                    ack_id TEXT PRIMARY KEY,
                    received_at TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    transport_name TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.commit()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_after_seconds(seconds: int) -> str:
    target = _parse_utc(_utc_now()).timestamp() + max(0, int(seconds))
    return datetime.fromtimestamp(target, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
