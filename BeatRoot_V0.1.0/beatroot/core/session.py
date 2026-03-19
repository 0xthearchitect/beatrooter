from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class SessionStatus(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass(slots=True)
class SessionInfo:
    session_id: str
    target: str
    created_at: str
    status: SessionStatus = SessionStatus.RUNNING
    updated_at: str | None = None
    task: str = ""
    user_instructions: list[str] = field(default_factory=list)
    tool_history: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "target": self.target,
            "created_at": self.created_at,
            "status": self.status.value,
            "updated_at": self.updated_at,
            "task": self.task,
            "user_instructions": self.user_instructions,
            "tool_history": self.tool_history,
            "model": self.model,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionInfo":
        return cls(
            session_id=data["session_id"],
            target=data["target"],
            created_at=data["created_at"],
            status=SessionStatus(data["status"]),
            updated_at=data.get("updated_at"),
            task=data.get("task", ""),
            user_instructions=data.get("user_instructions", []),
            tool_history=data.get("tool_history", []),
            model=data.get("model", ""),
            last_error=data.get("last_error"),
        )


class SessionStore:
    DEFAULT_DIR = Path(".beatroot/controller_sessions")

    def __init__(self, sessions_dir: str | Path | None = None):
        self._sessions_dir = Path(sessions_dir or self.DEFAULT_DIR)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current: SessionInfo | None = None

    @property
    def current(self) -> SessionInfo | None:
        return self._current

    def create(
        self,
        target: str,
        task: str,
        model: str,
        session_id: str | None = None,
    ) -> SessionInfo:
        session = SessionInfo(
            session_id=session_id or uuid4().hex[:8],
            target=target,
            created_at=datetime.now(UTC).isoformat(),
            task=task,
            model=model,
        )
        self._current = session
        self.save()
        return session

    def save(self) -> None:
        if self._current is None:
            return
        self._current.updated_at = datetime.now(UTC).isoformat()
        path = self._sessions_dir / f"{self._current.session_id}.json"
        path.write_text(json.dumps(self._current.to_dict(), indent=2), encoding="utf-8")

    def load(self, session_id: str) -> SessionInfo | None:
        path = self._sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            self._current = SessionInfo.from_dict(
                json.loads(path.read_text(encoding="utf-8"))
            )
            return self._current
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def list_sessions(self, target: str | None = None) -> list[SessionInfo]:
        sessions: list[SessionInfo] = []
        for path in self._sessions_dir.glob("*.json"):
            try:
                session = SessionInfo.from_dict(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            if target is None or session.target == target:
                sessions.append(session)
        return sorted(
            sessions,
            key=lambda item: item.updated_at or item.created_at,
            reverse=True,
        )

    def get_latest(self, target: str | None = None) -> SessionInfo | None:
        sessions = self.list_sessions(target=target)
        return sessions[0] if sessions else None

    def update_status(self, status: SessionStatus) -> None:
        if self._current is None:
            return
        self._current.status = status
        self.save()

    def add_instruction(self, instruction: str) -> None:
        if self._current is None:
            return
        self._current.user_instructions.append(instruction)
        self.save()

    def record_tool(self, tool_name: str, args: dict[str, Any]) -> None:
        if self._current is None:
            return
        self._current.tool_history.append({"tool": tool_name, "args": args})
        self.save()

    def set_error(self, error: str) -> None:
        if self._current is None:
            return
        self._current.last_error = error
        self._current.status = SessionStatus.ERROR
        self.save()
