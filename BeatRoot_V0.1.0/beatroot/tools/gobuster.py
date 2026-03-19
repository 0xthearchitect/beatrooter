from __future__ import annotations

from typing import Any

from beatroot.parser.web_enum import parse_gobuster_stdout
from beatroot.tools.base import BaseTool, ToolExecutionResult


class GobusterTool(BaseTool):
    name = "gobuster"
    risk = "medium"
    description = "Run directory enumeration with gobuster."

    def run(
        self,
        url: str,
        wordlist: str,
        extra_args: list[str] | None = None,
        **_: Any,
    ) -> ToolExecutionResult:
        if not self.binary_exists("gobuster"):
            return ToolExecutionResult(
                tool_name=self.name,
                command=["gobuster"],
                success=False,
                exit_code=127,
                stdout="",
                stderr="gobuster is not installed or not in PATH.",
                risk=self.risk,
                error="missing_binary",
            )

        command = ["gobuster", "dir", "-u", url, "-w", wordlist, "-q"]
        if extra_args:
            command.extend(extra_args)

        exit_code, stdout, stderr = self.execute(command)
        parsed = parse_gobuster_stdout(stdout)
        return ToolExecutionResult(
            tool_name=self.name,
            command=command,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            parsed=parsed,
            risk=self.risk,
            metadata={"url": url, "wordlist": wordlist},
        )

