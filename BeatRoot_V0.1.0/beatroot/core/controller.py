from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Callable

from beatroot.config.models import AppConfig
from beatroot.core.backend import AgentBackend, AgentMessage, MessageType
from beatroot.core.session import SessionStatus, SessionStore
from beatroot.memory import SessionMemory


class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class AgentController:
    def __init__(
        self,
        config: AppConfig,
        backend: AgentBackend,
        session_store: SessionStore | None = None,
        on_message: Callable[[AgentMessage], None] | None = None,
    ):
        self.config = config
        self.backend = backend
        self.sessions = session_store or SessionStore()
        self.on_message = on_message
        self._state = AgentState.IDLE
        self._stop_requested = False

    @property
    def state(self) -> AgentState:
        return self._state

    def stop(self) -> bool:
        self._stop_requested = True
        return True

    def inject(self, instruction: str) -> bool:
        if hasattr(self.backend, "inject_instruction"):
            self.backend.inject_instruction(instruction)
            self.sessions.add_instruction(instruction)
            return True
        return False

    def run(
        self,
        target: str,
        task: str,
        model: str,
        memory: SessionMemory,
        resume_session_id: str | None = None,
    ) -> dict[str, Any]:
        if resume_session_id:
            session = self.sessions.load(resume_session_id)
            if session is None:
                return {"success": False, "error": f"Session {resume_session_id} not found"}
        elif self.sessions.current and self.sessions.current.session_id == memory.session_id:
            session = self.sessions.current
        else:
            session = self.sessions.create(
                target=target,
                task=task,
                model=model,
                session_id=memory.session_id,
            )

        self._state = AgentState.RUNNING
        self.sessions.update_status(SessionStatus.RUNNING)
        memory.save(self.config.memory.directory)

        output_parts: list[str] = []
        tool_results: list[dict[str, Any]] = []

        try:
            self.backend.connect()
            self.backend.query(task)

            for message in self.backend.receive_messages():
                if self._stop_requested:
                    self._state = AgentState.PAUSED
                    self.sessions.update_status(SessionStatus.PAUSED)
                    break

                if self.on_message:
                    self.on_message(message)

                if message.type == MessageType.TEXT:
                    output_parts.append(str(message.content))
                elif message.type == MessageType.TOOL_START and message.tool_name:
                    self.sessions.record_tool(message.tool_name, message.tool_args or {})
                elif message.type == MessageType.TOOL_RESULT:
                    tool_results.append(message.content)
                    memory.save(self.config.memory.directory)
                elif message.type == MessageType.ERROR:
                    self._state = AgentState.ERROR
                    self.sessions.set_error(str(message.content))
                    self.backend.disconnect()
                    return {"success": False, "error": str(message.content)}
                elif message.type == MessageType.RESULT:
                    status = message.content.get("status")
                    if status == "paused":
                        self._state = AgentState.PAUSED
                        self.sessions.update_status(SessionStatus.PAUSED)
                    else:
                        self._state = AgentState.COMPLETED
                        self.sessions.update_status(SessionStatus.COMPLETED)
                    self.backend.disconnect()
                    return {
                        "success": True,
                        "output": "\n\n".join(output_parts),
                        "tool_results": tool_results,
                        "session_id": session.session_id,
                        "status": status,
                        "reason": message.content.get("reason", ""),
                    }

            self.backend.disconnect()
            return {
                "success": True,
                "output": "\n\n".join(output_parts),
                "tool_results": tool_results,
                "session_id": session.session_id,
                "status": self._state.value,
                "reason": "",
            }
        except Exception as exc:
            self._state = AgentState.ERROR
            self.sessions.set_error(str(exc))
            self.backend.disconnect()
            return {"success": False, "error": str(exc)}


def load_memory_for_session(config: AppConfig, target: str, session_id: str) -> SessionMemory:
    path = Path(config.memory.directory) / f"{session_id}.json"
    if path.exists():
        return SessionMemory.load(path)
    return SessionMemory(target=target, session_id=session_id)
