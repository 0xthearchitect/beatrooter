from __future__ import annotations

from dataclasses import dataclass, field

from beatroot.config.models import AppConfig
from beatroot.tools.base import BaseTool
from beatroot.tools.command import GenericCommandTool
from beatroot.tools.ffuf import FfufTool
from beatroot.tools.gobuster import GobusterTool
from beatroot.tools.nmap import NmapTool


@dataclass
class ToolRegistry:
    tools: dict[str, BaseTool] = field(default_factory=dict)

    def register(self, tool: BaseTool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self.tools:
            raise KeyError(f"Unknown tool: {name}")
        return self.tools[name]

    def available_tools(self) -> dict[str, str]:
        return {name: tool.description for name, tool in self.tools.items()}


def build_tool_registry(config: AppConfig) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(NmapTool())
    registry.register(FfufTool())
    registry.register(GobusterTool())
    registry.register(GenericCommandTool(config.safety))
    return registry

