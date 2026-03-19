from __future__ import annotations

import json
from typing import Any


def normalize_scenario_context(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        value = raw.strip()
        return value or None
    if isinstance(raw, (dict, list)):
        return json.dumps(raw, indent=2, ensure_ascii=False)
    return str(raw)
