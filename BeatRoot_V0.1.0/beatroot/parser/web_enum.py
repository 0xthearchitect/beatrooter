from __future__ import annotations

import json
import re
from typing import Any


FFUF_LINE_RE = re.compile(
    r"^(?P<path>\S+)\s+\[Status:\s+(?P<status>\d+),\s+Size:\s+(?P<size>\d+),\s+Words:\s+(?P<words>\d+),\s+Lines:\s+(?P<lines>\d+)"
)
GOBUSTER_LINE_RE = re.compile(
    r"^(?P<path>/\S*)\s+\(Status:\s+(?P<status>\d+)\)(?:\s+\[Size:\s+(?P<size>\d+)\])?"
)


def _normalize_paths(paths: list[dict[str, Any]]) -> dict[str, Any]:
    return {"paths": paths}


def parse_ffuf_json(text: str) -> dict[str, Any]:
    payload = json.loads(text)
    results = payload.get("results", [])
    paths = [
        {
            "path": item.get("input", {}).get("FUZZ") or item.get("url"),
            "status": item.get("status"),
            "length": item.get("length"),
            "words": item.get("words"),
            "lines": item.get("lines"),
            "redirectlocation": item.get("redirectlocation"),
        }
        for item in results
    ]
    return _normalize_paths(paths)


def parse_ffuf_stdout(text: str) -> dict[str, Any]:
    paths: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = FFUF_LINE_RE.match(line.strip())
        if not match:
            continue
        paths.append(
            {
                "path": match.group("path"),
                "status": int(match.group("status")),
                "length": int(match.group("size")),
                "words": int(match.group("words")),
                "lines": int(match.group("lines")),
            }
        )
    return _normalize_paths(paths)


def parse_gobuster_stdout(text: str) -> dict[str, Any]:
    paths: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = GOBUSTER_LINE_RE.match(line.strip())
        if not match:
            continue
        size = match.group("size")
        paths.append(
            {
                "path": match.group("path"),
                "status": int(match.group("status")),
                "length": int(size) if size else None,
            }
        )
    return _normalize_paths(paths)
