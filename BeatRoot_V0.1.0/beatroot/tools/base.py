from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolExecutionResult:
    tool_name: str
    command: list[str]
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    parsed: dict[str, Any] = field(default_factory=dict)
    risk: str = "low"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseTool(ABC):
    name: str = "tool"
    risk: str = "low"
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolExecutionResult:
        raise NotImplementedError

    def binary_exists(self, binary_name: str) -> bool:
        return shutil.which(binary_name) is not None

    def execute(self, command: list[str]) -> tuple[int, str, str]:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.returncode, completed.stdout, completed.stderr

