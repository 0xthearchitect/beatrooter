from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class SessionMemory:
    target: str
    session_id: str
    started_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    ports: dict[str, dict[str, Any]] = field(default_factory=dict)
    services: dict[str, str] = field(default_factory=dict)
    web_paths: list[dict[str, Any]] = field(default_factory=list)
    vulnerabilities: list[dict[str, Any]] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    conversation: list[dict[str, str]] = field(default_factory=list)

    def add_note(self, note: str) -> None:
        self.notes.append(note)
        self.updated_at = _utc_now()

    def record_conversation(self, role: str, content: str) -> None:
        self.conversation.append({"role": role, "content": content})
        self.updated_at = _utc_now()

    def record_command(self, tool_name: str, command: list[str], risk: str) -> None:
        self.commands.append(
            {
                "timestamp": _utc_now(),
                "tool": tool_name,
                "command": command,
                "risk": risk,
            }
        )
        self.updated_at = _utc_now()

    def ingest_tool_result(self, result: dict[str, Any]) -> None:
        self.tool_results.append(result)
        parsed = result.get("parsed") or {}

        for host in parsed.get("hosts", []):
            for port in host.get("ports", []):
                key = f"{host.get('address')}:{port.get('port')}"
                self.ports[key] = port
                service_name = port.get("service")
                if service_name:
                    self.services[key] = service_name

        for path in parsed.get("paths", []):
            if path not in self.web_paths:
                self.web_paths.append(path)

        for finding in parsed.get("vulnerabilities", []):
            if finding not in self.vulnerabilities:
                self.vulnerabilities.append(finding)

        self.updated_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summarize(self) -> dict[str, Any]:
        services = [
            {
                "socket": socket,
                "service": service,
            }
            for socket, service in sorted(self.services.items())
        ]
        return {
            "target": self.target,
            "ports": list(self.ports.values()),
            "services": services,
            "web_paths": self.web_paths[-20:],
            "vulnerabilities": self.vulnerabilities[-20:],
            "recent_commands": self.commands[-10:],
            "notes": self.notes[-10:],
        }

    def save(self, directory: str | Path) -> Path:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / f"{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "SessionMemory":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**raw)

