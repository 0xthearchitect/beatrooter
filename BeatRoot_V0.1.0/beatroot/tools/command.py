from __future__ import annotations

from typing import Any

from beatroot.config.models import SafetyConfig
from beatroot.tools.base import BaseTool, ToolExecutionResult


class GenericCommandTool(BaseTool):
    name = "generic_command"
    risk = "high"
    description = "Run an explicitly approved generic command."

    def __init__(self, safety: SafetyConfig):
        self.safety = safety

    def _validate(self, command: list[str]) -> str | None:
        if not self.safety.allow_generic_command_execution:
            return "Generic command execution is disabled by configuration."
        if not command:
            return "Command cannot be empty."
        joined = " ".join(command).lower()
        for keyword in self.safety.blocked_keywords:
            if keyword.lower() in joined:
                return f"Blocked keyword detected in command: {keyword}"
        prefix = command[0]
        if prefix not in self.safety.allowed_command_prefixes:
            return f"Command prefix is not allowlisted: {prefix}"
        return None

    def run(self, command: list[str], **_: Any) -> ToolExecutionResult:
        validation_error = self._validate(command)
        if validation_error is not None:
            return ToolExecutionResult(
                tool_name=self.name,
                command=command,
                success=False,
                exit_code=1,
                stdout="",
                stderr=validation_error,
                risk=self.risk,
                error="blocked_command",
            )
        if not self.binary_exists(command[0]):
            return ToolExecutionResult(
                tool_name=self.name,
                command=command,
                success=False,
                exit_code=127,
                stdout="",
                stderr=f"{command[0]} is not installed or not in PATH.",
                risk=self.risk,
                error="missing_binary",
            )
        exit_code, stdout, stderr = self.execute(command)
        return ToolExecutionResult(
            tool_name=self.name,
            command=command,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            risk=self.risk,
            metadata={"generic_command": True},
        )

