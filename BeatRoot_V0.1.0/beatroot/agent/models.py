from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentAction:
    type: str
    tool: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    risk: str = "low"


@dataclass(slots=True)
class AgentPlan:
    summary: str
    reasoning: str
    action: AgentAction
    source: str = "heuristic"

