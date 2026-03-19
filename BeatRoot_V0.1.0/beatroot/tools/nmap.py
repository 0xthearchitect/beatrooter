from __future__ import annotations

from typing import Any

from beatroot.parser.nmap import parse_nmap_grepable_output
from beatroot.tools.base import BaseTool, ToolExecutionResult


class NmapTool(BaseTool):
    name = "nmap"
    risk = "medium"
    description = "Run a bounded nmap reconnaissance scan."

    def run(
        self,
        target: str,
        top_ports: int = 1000,
        ports: str | None = None,
        version_detection: bool = True,
        extra_args: list[str] | None = None,
        **_: Any,
    ) -> ToolExecutionResult:
        if not self.binary_exists("nmap"):
            return ToolExecutionResult(
                tool_name=self.name,
                command=["nmap"],
                success=False,
                exit_code=127,
                stdout="",
                stderr="nmap is not installed or not in PATH.",
                risk=self.risk,
                error="missing_binary",
            )

        command = ["nmap", "-Pn", "--open"]
        if version_detection:
            command.append("-sV")
        if ports:
            command.extend(["-p", ports])
        else:
            command.extend(["--top-ports", str(top_ports)])
        command.extend(["-oG", "-", target])
        if extra_args:
            command.extend(extra_args)

        exit_code, stdout, stderr = self.execute(command)
        parsed = parse_nmap_grepable_output(stdout)
        return ToolExecutionResult(
            tool_name=self.name,
            command=command,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            parsed=parsed,
            risk=self.risk,
            metadata={"target": target},
        )

