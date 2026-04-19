from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4
import requests

from .schema import NDCEvent


@dataclass(frozen=True)
class BatchSendResult:
    acknowledged: bool
    ack_id: str | None = None
    retry_after_seconds: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class NDCBatchTransport(Protocol):
    transport_name: str

    def send_batch(self, events: list[NDCEvent]) -> BatchSendResult:
        ...


class LocalJSONLAckTransport:
    transport_name = "local_jsonl_ack"

    def __init__(self, outbox_path: str | Path) -> None:
        self.outbox_path = Path(outbox_path)
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)

    def send_batch(self, events: list[NDCEvent]) -> BatchSendResult:
        ack_id = f"ack-{uuid4()}"
        received_at = _utc_now()
        record = {
            "ack_id": ack_id,
            "received_at": received_at,
            "event_count": len(events),
            "events": [event.to_dict() for event in events],
        }
        with self.outbox_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
            handle.write("\n")

        return BatchSendResult(
            acknowledged=True,
            ack_id=ack_id,
            metadata={
                "outbox_path": str(self.outbox_path),
                "received_at": received_at,
                "event_count": len(events),
            },
        )


class HTTPNDCBatchTransport:
    transport_name = "http_ingest"

    def __init__(
        self,
        ingest_url: str,
        *,
        token: str,
        timeout_seconds: int = 10,
        session: requests.Session | None = None,
    ) -> None:
        self.ingest_url = str(ingest_url or "").strip()
        self.token = str(token or "").strip()
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.session = session or requests.Session()
        if not self.ingest_url:
            raise ValueError("ingest_url is required.")
        if not self.token:
            raise ValueError("token is required.")

    def send_batch(self, events: list[NDCEvent]) -> BatchSendResult:
        payload = {
            "event_count": len(events),
            "events": [event.to_dict() for event in events],
        }
        response = self.session.post(
            self.ingest_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "BeatRooter-NDC/1.0",
            },
            timeout=self.timeout_seconds,
        )

        retry_after_header = response.headers.get("Retry-After")
        retry_after_seconds = int(retry_after_header) if str(retry_after_header or "").isdigit() else None

        try:
            body = response.json()
        except ValueError:
            body = {"detail": response.text[:500]}

        if 200 <= response.status_code < 300:
            return BatchSendResult(
                acknowledged=True,
                ack_id=str(body.get("ack_id") or body.get("receipt_id") or f"ack-{uuid4()}"),
                metadata={
                    "status_code": response.status_code,
                    "response": body,
                },
            )

        if response.status_code in {400, 409, 422}:
            return BatchSendResult(
                acknowledged=True,
                ack_id=f"reject-{uuid4()}",
                metadata={
                    "status_code": response.status_code,
                    "response": body,
                    "rejected": True,
                },
            )

        return BatchSendResult(
            acknowledged=False,
            retry_after_seconds=retry_after_seconds,
            error=str(body.get("detail") or body.get("error") or f"http {response.status_code}"),
            metadata={
                "status_code": response.status_code,
                "response": body,
            },
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
