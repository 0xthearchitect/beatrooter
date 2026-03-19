from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from beatroot.parser.web_enum import parse_ffuf_json, parse_ffuf_stdout
from beatroot.tools.base import BaseTool, ToolExecutionResult


class FfufTool(BaseTool):
    name = "ffuf"
    risk = "medium"
    description = "Run directory enumeration with ffuf."

    def run(
        self,
        url: str,
        wordlist: str,
        extra_args: list[str] | None = None,
        **_: Any,
    ) -> ToolExecutionResult:
        if not self.binary_exists("ffuf"):
            return ToolExecutionResult(
                tool_name=self.name,
                command=["ffuf"],
                success=False,
                exit_code=127,
                stdout="",
                stderr="ffuf is not installed or not in PATH.",
                risk=self.risk,
                error="missing_binary",
            )

        tmp_file = tempfile.NamedTemporaryFile(prefix="beatroot-ffuf-", suffix=".json", delete=False)
        tmp_path = Path(tmp_file.name)
        tmp_file.close()

        fuzz_url = url if "FUZZ" in url else f"{url.rstrip('/')}/FUZZ"
        command = ["ffuf", "-u", fuzz_url, "-w", wordlist, "-of", "json", "-o", str(tmp_path)]
        if extra_args:
            command.extend(extra_args)

        exit_code, stdout, stderr = self.execute(command)

        parsed: dict[str, Any]
        if tmp_path.exists() and tmp_path.stat().st_size > 0:
            parsed = parse_ffuf_json(tmp_path.read_text(encoding="utf-8"))
        else:
            parsed = parse_ffuf_stdout(stdout)

        tmp_path.unlink(missing_ok=True)
        return ToolExecutionResult(
            tool_name=self.name,
            command=command,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            parsed=parsed,
            risk=self.risk,
            metadata={"url": fuzz_url, "wordlist": wordlist},
        )

