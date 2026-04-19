from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from typing import Any

from .raw_ingest import NDCEventConflictError, NDCRawIngestError, NDCRawIngestStore


class NDCAuthenticationError(RuntimeError):
    """Raised when the request does not include valid NDC ingest credentials."""


class NDCRequestValidationError(RuntimeError):
    """Raised when the ingest request envelope is malformed."""


@dataclass(frozen=True)
class AuthContext:
    key_id: str


@dataclass(frozen=True)
class IngestHTTPResponse:
    status_code: int
    payload: dict[str, Any]
    headers: dict[str, str] | None = None


class StaticTokenAuth:
    def __init__(self, tokens: dict[str, str]) -> None:
        self.tokens = {str(token): str(key_id) for token, key_id in tokens.items() if str(token).strip()}
        if not self.tokens:
            raise ValueError("At least one static ingest token is required.")

    def authenticate(self, authorization_header: str | None) -> AuthContext:
        raw_header = str(authorization_header or "").strip()
        if not raw_header.startswith("Bearer "):
            raise NDCAuthenticationError("Missing Bearer token.")
        token = raw_header[len("Bearer ") :].strip()
        key_id = self.tokens.get(token)
        if not key_id:
            raise NDCAuthenticationError("Invalid ingest token.")
        return AuthContext(key_id=key_id)


class NDCIngestAPI:
    ingest_path = "/api/ndc/ingest"
    health_path = "/api/ndc/health"
    debug_summary_path = "/api/ndc/debug/summary"
    debug_batches_path = "/api/ndc/debug/batches"

    def __init__(self, store: NDCRawIngestStore, *, auth: StaticTokenAuth) -> None:
        self.store = store
        self.auth = auth

    def handle_request(
        self,
        *,
        method: str,
        path: str,
        headers: dict[str, str] | None,
        body: bytes,
        client_ip: str | None = None,
    ) -> IngestHTTPResponse:
        headers = {str(key): str(value) for key, value in (headers or {}).items()}
        request_path, query_params = self._split_path_and_query(path)

        if request_path == self.health_path:
            if method.upper() != "GET":
                return self._response(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
            return self._response(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "ndc_ingest",
                    "seen_event_count": self.store.seen_event_count(),
                },
            )

        if request_path in {self.debug_summary_path, self.debug_batches_path}:
            if method.upper() != "GET":
                return self._response(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
            try:
                auth_context = self.auth.authenticate(headers.get("Authorization"))
            except NDCAuthenticationError as exc:
                return self._response(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized", "detail": str(exc)})
            if request_path == self.debug_summary_path:
                return self._response(HTTPStatus.OK, self._build_debug_summary(auth_context.key_id))
            limit = self._parse_limit(query_params.get("limit"))
            return self._response(HTTPStatus.OK, self._build_debug_batches(auth_context.key_id, limit=limit))

        if request_path != self.ingest_path:
            return self._response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        if method.upper() != "POST":
            return self._response(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})

        try:
            auth_context = self.auth.authenticate(headers.get("Authorization"))
        except NDCAuthenticationError as exc:
            return self._response(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized", "detail": str(exc)})

        try:
            request_payload = self._parse_request_payload(body)
            receipt = self.store.accept_batch(
                request_payload["events"],
                auth_key_id=auth_context.key_id,
                public_ip=client_ip,
                user_agent=headers.get("User-Agent"),
                request_metadata=request_payload.get("request_metadata"),
            )
        except json.JSONDecodeError as exc:
            return self._response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "detail": str(exc)})
        except NDCRequestValidationError as exc:
            return self._response(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "detail": str(exc)})
        except NDCEventConflictError as exc:
            return self._response(HTTPStatus.CONFLICT, {"error": "event_conflict", "detail": str(exc)})
        except NDCRawIngestError as exc:
            return self._response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "ingest_failure", "detail": str(exc)})
        except Exception as exc:
            return self._response(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "invalid_event", "detail": str(exc)})

        payload = {
            "status": "accepted",
            "ack_id": receipt.receipt_id,
            **receipt.to_dict(),
        }
        return self._response(HTTPStatus.ACCEPTED, payload)

    def _parse_request_payload(self, body: bytes) -> dict[str, Any]:
        decoded = json.loads(body.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise NDCRequestValidationError("Request body must be a JSON object.")

        events = decoded.get("events")
        if not isinstance(events, list) or not events:
            raise NDCRequestValidationError("Request body must include a non-empty 'events' list.")

        request_metadata = decoded.get("request_metadata", {})
        if request_metadata is None:
            request_metadata = {}
        if not isinstance(request_metadata, dict):
            raise NDCRequestValidationError("'request_metadata' must be an object when provided.")

        if "event_count" in decoded and int(decoded["event_count"]) != len(events):
            raise NDCRequestValidationError("'event_count' must match the number of supplied events.")

        return {"events": events, "request_metadata": request_metadata}

    def _response(self, status: HTTPStatus, payload: dict[str, Any]) -> IngestHTTPResponse:
        return IngestHTTPResponse(
            status_code=int(status),
            payload=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    def _build_debug_summary(self, auth_key_id: str) -> dict[str, Any]:
        dashboard = self.store.governance.build_dashboard()
        pilot_review = self.store.rollout.build_pilot_review(dashboard)
        return {
            "status": "ok",
            "auth_key_id": auth_key_id,
            "paths": {
                "ingest": self.ingest_path,
                "health": self.health_path,
                "debug_summary": self.debug_summary_path,
                "debug_batches": self.debug_batches_path,
            },
            "server_home": str(self.store.base_dir),
            "seen_event_count": self.store.seen_event_count(),
            "dashboard": dashboard,
            "pilot_review": pilot_review,
        }

    def _build_debug_batches(self, auth_key_id: str, *, limit: int) -> dict[str, Any]:
        return {
            "status": "ok",
            "auth_key_id": auth_key_id,
            "limit": limit,
            "recent_batches": self.store.recent_batches(limit=limit),
            "recent_network_observations": self.store.recent_network_observations(limit=limit),
        }

    def _split_path_and_query(self, raw_path: str) -> tuple[str, dict[str, str]]:
        path_text = str(raw_path or "")
        if "?" not in path_text:
            return path_text, {}
        path_part, query_string = path_text.split("?", 1)
        params: dict[str, str] = {}
        for fragment in query_string.split("&"):
            if not fragment:
                continue
            if "=" in fragment:
                key, value = fragment.split("=", 1)
            else:
                key, value = fragment, ""
            params[str(key)] = str(value)
        return path_part, params

    def _parse_limit(self, raw_value: str | None) -> int:
        if raw_value is None or not str(raw_value).strip():
            return 10
        return max(1, min(100, int(raw_value)))


class NDCIngestHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "NDCIngest/1.0"

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_PUT(self) -> None:  # noqa: N802
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _handle(self) -> None:
        app = getattr(self.server, "ndc_ingest_app", None)
        if app is None:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "NDC ingest app not configured.")
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(content_length) if content_length > 0 else b""
        response = app.handle_request(
            method=self.command,
            path=self.path,
            headers={key: value for key, value in self.headers.items()},
            body=body,
            client_ip=self.client_address[0] if self.client_address else None,
        )
        encoded = json.dumps(response.payload, ensure_ascii=True, sort_keys=True).encode("utf-8")

        self.send_response(response.status_code)
        for key, value in (response.headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def build_ingest_http_server(
    host: str,
    port: int,
    *,
    store: NDCRawIngestStore,
    auth: StaticTokenAuth,
) -> ThreadingHTTPServer:
    app = NDCIngestAPI(store, auth=auth)
    server = ThreadingHTTPServer((host, int(port)), NDCIngestHTTPRequestHandler)
    server.ndc_ingest_app = app
    return server


def create_default_ingest_server() -> ThreadingHTTPServer:
    raw_base_dir = os.environ.get("BEATROOTER_NDC_INGEST_HOME", "").strip()
    base_dir = Path(raw_base_dir).expanduser() if raw_base_dir else None
    if base_dir is None:
        base_dir = Path.home() / ".beatrooter" / "ndc_server"
    store = NDCRawIngestStore(base_dir)
    token = os.environ.get("BEATROOTER_NDC_INGEST_TOKEN", "").strip()
    if not token:
        raise ValueError("BEATROOTER_NDC_INGEST_TOKEN is required to start the ingest server.")
    host = os.environ.get("BEATROOTER_NDC_INGEST_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("BEATROOTER_NDC_INGEST_PORT", "8787"))
    return build_ingest_http_server(host, port, store=store, auth=StaticTokenAuth({token: "default"}))


if __name__ == "__main__":
    server = create_default_ingest_server()
    try:
        server.serve_forever()
    finally:
        server.server_close()
