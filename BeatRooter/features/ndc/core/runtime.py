from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .schema import NDCEvent, NotePayload, ToolPayload, create_ndc_event
from .storage import NDCQueueStorage, QueuedNDCEvent
from .transport import BatchSendResult, HTTPNDCBatchTransport, LocalJSONLAckTransport, NDCBatchTransport

DEFAULT_REMOTE_INGEST_URL = "https://beatrooter.com/api/ndc/ingest"
CLIENT_AUTH_FILENAME = "client_auth.json"


@dataclass(frozen=True)
class FlushResult:
    status: str
    batch_size: int
    retry_after_seconds: int = 0
    ack_id: str | None = None
    error: str | None = None


class NDCPilotTelemetryReporter:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_path = self.base_dir / "client_metrics.jsonl"

    def record_runtime_start(self, payload: dict[str, Any]) -> None:
        self._append({"kind": "runtime_start", **payload})

    def record_enqueue(self, payload: dict[str, Any]) -> None:
        self._append({"kind": "enqueue", **payload})

    def record_flush(self, payload: dict[str, Any]) -> None:
        self._append({"kind": "flush", **payload})

    def _append(self, payload: dict[str, Any]) -> None:
        record = {
            "recorded_at": _utc_now(),
            **payload,
        }
        with self.metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
            handle.write("\n")


class NDCClientRuntime:
    def __init__(
        self,
        *,
        queue: NDCQueueStorage,
        transport: NDCBatchTransport,
        batch_size: int = 50,
        flush_interval_seconds: int = 10,
        base_retry_seconds: int = 5,
        max_retry_seconds: int = 300,
        telemetry_reporter: NDCPilotTelemetryReporter | None = None,
        internal_pilot_enabled: bool = False,
    ) -> None:
        self.queue = queue
        self.transport = transport
        self.batch_size = max(1, int(batch_size))
        self.flush_interval_seconds = max(10, int(flush_interval_seconds))
        self.base_retry_seconds = max(1, int(base_retry_seconds))
        self.max_retry_seconds = max(self.base_retry_seconds, int(max_retry_seconds))
        self.telemetry_reporter = telemetry_reporter
        self.internal_pilot_enabled = bool(internal_pilot_enabled)
        self.enabled = True
        if self.telemetry_reporter is not None:
            self.telemetry_reporter.record_runtime_start(
                {
                    "enabled": True,
                    "internal_pilot_enabled": self.internal_pilot_enabled,
                    "transport_name": getattr(self.transport, "transport_name", "unknown"),
                    "batch_size": self.batch_size,
                    "flush_interval_seconds": self.flush_interval_seconds,
                }
            )

    @property
    def source_id(self) -> str:
        return self.queue.get_or_create_source_id()

    def ensure_project_id(self, metadata: dict[str, Any] | None, *, prefix: str = "project") -> str:
        if metadata is None:
            raise ValueError("metadata is required to persist an NDC project id.")

        project_id = str(metadata.get("ndc_project_id") or "").strip()
        if not project_id:
            project_id = f"{prefix}-{uuid4()}"
            metadata["ndc_project_id"] = project_id
        return project_id

    def enqueue_event(
        self,
        *,
        family: str,
        action: str,
        project_id: str,
        payload: Mapping[str, Any] | NotePayload | ToolPayload,
    ) -> NDCEvent:
        event = create_ndc_event(
            family=family,
            action=action,
            source_id=self.source_id,
            project_id=project_id,
            sequence_number=self.queue.next_sequence_number(),
            payload=payload,
        )
        inserted = self.queue.enqueue(event)
        if self.telemetry_reporter is not None:
            self.telemetry_reporter.record_enqueue(
                {
                    "event_id": event.event_id,
                    "family": event.family.value,
                    "action": event.action,
                    "project_id": event.project_id,
                    "sequence_number": event.sequence_number,
                    "inserted": bool(inserted),
                    "queue_health": self.health_snapshot(),
                }
            )
        return event

    def flush_once(self) -> FlushResult:
        ready = self.queue.fetch_ready_batch(self.batch_size)
        if not ready:
            result = FlushResult(status="idle", batch_size=0)
            self._record_flush(result)
            return result

        events = [item.event for item in ready]
        queue_ids = [item.queue_id for item in ready]

        try:
            result = self.transport.send_batch(events)
        except Exception as exc:
            retry_after = self._backoff_for_batch(ready)
            self.queue.mark_batch_failed(queue_ids, error=str(exc), retry_after_seconds=retry_after)
            flush_result = FlushResult(
                status="retrying",
                batch_size=len(queue_ids),
                retry_after_seconds=retry_after,
                error=str(exc),
            )
            self._record_flush(flush_result)
            return flush_result

        if result.acknowledged and result.ack_id:
            self.queue.acknowledge_batch(
                queue_ids,
                ack_id=result.ack_id,
                transport_name=getattr(self.transport, "transport_name", "unknown"),
                metadata=result.metadata,
            )
            flush_result = FlushResult(
                status="acked",
                batch_size=len(queue_ids),
                ack_id=result.ack_id,
            )
            self._record_flush(flush_result, transport_metadata=result.metadata)
            return flush_result

        retry_after = int(result.retry_after_seconds or self._backoff_for_batch(ready))
        error_message = str(result.error or "transport did not acknowledge the batch")
        self.queue.mark_batch_failed(queue_ids, error=error_message, retry_after_seconds=retry_after)
        flush_result = FlushResult(
            status="retrying",
            batch_size=len(queue_ids),
            retry_after_seconds=retry_after,
            error=error_message,
        )
        self._record_flush(flush_result, transport_metadata=result.metadata)
        return flush_result

    def health_snapshot(self) -> dict[str, Any]:
        snapshot = self.queue.health_snapshot()
        snapshot.update(
            {
                "enabled": True,
                "internal_pilot_enabled": self.internal_pilot_enabled,
                "transport_name": getattr(self.transport, "transport_name", "unknown"),
                "batch_size": self.batch_size,
                "flush_interval_seconds": self.flush_interval_seconds,
                "base_retry_seconds": self.base_retry_seconds,
                "max_retry_seconds": self.max_retry_seconds,
            }
        )
        return snapshot

    def _backoff_for_batch(self, batch: list[QueuedNDCEvent]) -> int:
        next_attempt = max((item.attempt_count for item in batch), default=0) + 1
        delay = self.base_retry_seconds * (2 ** max(0, next_attempt - 1))
        return min(self.max_retry_seconds, delay)

    def _record_flush(
        self,
        result: FlushResult,
        *,
        transport_metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.telemetry_reporter is None:
            return
        self.telemetry_reporter.record_flush(
            {
                "status": result.status,
                "batch_size": result.batch_size,
                "retry_after_seconds": result.retry_after_seconds,
                "ack_id": result.ack_id,
                "error": result.error,
                "transport_metadata": dict(transport_metadata or {}),
                "queue_health": self.health_snapshot(),
            }
        )


class DisabledNDCClientRuntime:
    def __init__(self, *, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = False
        self.internal_pilot_enabled = False
        self._source_id = "source-ndc-disabled"
        self._next_sequence_number = 1

    @property
    def source_id(self) -> str:
        return self._source_id

    def ensure_project_id(self, metadata: dict[str, Any] | None, *, prefix: str = "project") -> str:
        if metadata is None:
            raise ValueError("metadata is required to persist an NDC project id.")
        project_id = str(metadata.get("ndc_project_id") or "").strip()
        if not project_id:
            project_id = f"{prefix}-{uuid4()}"
            metadata["ndc_project_id"] = project_id
        return project_id

    def enqueue_event(
        self,
        *,
        family: str,
        action: str,
        project_id: str,
        payload: Mapping[str, Any] | NotePayload | ToolPayload,
    ) -> NDCEvent:
        event = create_ndc_event(
            family=family,
            action=action,
            source_id=self.source_id,
            project_id=project_id,
            sequence_number=self._next_sequence_number,
            payload=payload,
        )
        self._next_sequence_number += 1
        return event

    def flush_once(self) -> FlushResult:
        return FlushResult(status="disabled", batch_size=0)

    def health_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": False,
            "internal_pilot_enabled": False,
            "db_path": str(self.base_dir / "ndc_queue.sqlite3"),
            "source_id": self.source_id,
            "total_pending": 0,
            "ready_count": 0,
            "retrying_count": 0,
            "receipt_count": 0,
            "oldest_pending_age_seconds": None,
            "next_retry_at": None,
            "last_ack_id": None,
            "last_flush_at": None,
            "last_flush_error": None,
            "transport_name": "disabled",
            "batch_size": 0,
            "flush_interval_seconds": 0,
            "base_retry_seconds": 0,
            "max_retry_seconds": 0,
        }


def create_default_runtime(base_dir: str | Path) -> NDCClientRuntime | DisabledNDCClientRuntime:
    home = Path(base_dir)
    enabled = _env_flag("BEATROOTER_NDC_ENABLED", default=True)
    if not enabled:
        return DisabledNDCClientRuntime(base_dir=home)

    queue = NDCQueueStorage(home / "ndc_queue.sqlite3")
    ingest_url = os.environ.get("BEATROOTER_NDC_INGEST_URL", "").strip() or DEFAULT_REMOTE_INGEST_URL
    ingest_token = _resolve_ingest_token(home)
    if ingest_url and ingest_token:
        timeout_seconds = int(os.environ.get("BEATROOTER_NDC_INGEST_TIMEOUT", "10"))
        transport = HTTPNDCBatchTransport(
            ingest_url,
            token=ingest_token,
            timeout_seconds=timeout_seconds,
        )
    else:
        transport = LocalJSONLAckTransport(home / "ndc_batches.jsonl")
    pilot_enabled = _env_flag("BEATROOTER_NDC_INTERNAL_PILOT", default=False)
    telemetry_reporter = None
    if pilot_enabled:
        telemetry_reporter = NDCPilotTelemetryReporter(home / "pilot_telemetry")
    return NDCClientRuntime(
        queue=queue,
        transport=transport,
        telemetry_reporter=telemetry_reporter,
        internal_pilot_enabled=pilot_enabled,
    )


def _env_flag(name: str, *, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None or not str(raw_value).strip():
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_ingest_token(base_dir: Path) -> str:
    env_token = os.environ.get("BEATROOTER_NDC_INGEST_TOKEN", "").strip()
    if env_token:
        return env_token

    auth_path = base_dir / CLIENT_AUTH_FILENAME
    if not auth_path.exists():
        return ""

    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    if not isinstance(payload, dict):
        return ""
    return str(payload.get("ingest_token") or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
