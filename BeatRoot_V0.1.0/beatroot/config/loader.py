from __future__ import annotations

from pathlib import Path
from typing import Any

from beatroot.config.models import AppConfig


def _strip_comment(line: str) -> str:
    if "#" not in line:
        return line.rstrip()
    quote: str | None = None
    result: list[str] = []
    for char in line:
        if char in {'"', "'"}:
            quote = None if quote == char else char
        if char == "#" and quote is None:
            break
        result.append(char)
    return "".join(result).rstrip()


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"null", "none"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.isdigit():
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _parse_block(lines: list[tuple[int, str]], start: int, indent: int):
    if start >= len(lines):
        return {}, start

    is_list = lines[start][1].startswith("- ")
    if is_list:
        items: list[Any] = []
        index = start
        while index < len(lines):
            current_indent, content = lines[index]
            if current_indent < indent:
                break
            if current_indent != indent or not content.startswith("- "):
                break
            payload = content[2:].strip()
            if payload:
                items.append(_parse_scalar(payload))
                index += 1
                continue
            if index + 1 < len(lines) and lines[index + 1][0] > indent:
                nested, index = _parse_block(lines, index + 1, lines[index + 1][0])
                items.append(nested)
            else:
                items.append(None)
                index += 1
        return items, index

    mapping: dict[str, Any] = {}
    index = start
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent:
            break
        if ":" not in content:
            raise ValueError(f"Invalid config line: {content}")
        key, raw_value = content.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            mapping[key] = _parse_scalar(raw_value)
            index += 1
            continue
        if index + 1 < len(lines) and lines[index + 1][0] > indent:
            nested, index = _parse_block(lines, index + 1, lines[index + 1][0])
            mapping[key] = nested
            continue
        mapping[key] = {}
        index += 1
    return mapping, index


def parse_yaml_like(text: str) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        cleaned = _strip_comment(raw_line)
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        lines.append((indent, cleaned.strip()))

    if not lines:
        return {}
    parsed, _ = _parse_block(lines, 0, lines[0][0])
    if not isinstance(parsed, dict):
        raise ValueError("Top-level config must be a mapping")
    return parsed


def load_config(path: str | Path | None = None) -> AppConfig:
    if path is None:
        return AppConfig()
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Config file not found: {path_obj}")
    raw_text = path_obj.read_text(encoding="utf-8")
    parsed = parse_yaml_like(raw_text)
    return AppConfig.from_dict(parsed)

