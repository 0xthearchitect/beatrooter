from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterator

from beatroot.agent.models import AgentAction
from beatroot.agent.planner import Planner
from beatroot.memory import SessionMemory
from beatroot.tools.registry import ToolRegistry


class MessageType(Enum):
    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    RESULT = "result"
    ERROR = "error"


@dataclass(slots=True)
class AgentMessage:
    type: MessageType
    content: Any
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentBackend(ABC):
    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, prompt: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive_messages(self) -> Iterator[AgentMessage]:
        raise NotImplementedError

    @property
    @abstractmethod
    def session_id(self) -> str | None:
        raise NotImplementedError

    def supports_resume(self) -> bool:
        return False

    def resume(self, _session_id: str) -> bool:
        return False


class PlanningAgentBackend(AgentBackend):
    def __init__(
        self,
        planner: Planner,
        tool_registry: ToolRegistry,
        memory: SessionMemory,
        wordlist: str | None = None,
        scenario_context: str | None = None,
        scenario_only: bool = False,
        max_steps: int = 6,
        custom_instruction: str | None = None,
        approval_callback: Callable[[str, list[str], str], bool] | None = None,
    ):
        self.planner = planner
        self.tool_registry = tool_registry
        self.memory = memory
        self.wordlist = wordlist
        self.scenario_context = scenario_context
        self.scenario_only = scenario_only
        self.max_steps = max_steps
        self.custom_instruction = custom_instruction
        self.approval_callback = approval_callback
        self._prompt = ""
        self._pending_instruction: str | None = None

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def query(self, prompt: str) -> None:
        self._prompt = prompt
        self.memory.record_conversation("user", prompt)

    @property
    def session_id(self) -> str | None:
        return self.memory.session_id

    def inject_instruction(self, instruction: str) -> None:
        self._pending_instruction = instruction
        self.memory.record_conversation("user", instruction)

    def receive_messages(self) -> Iterator[AgentMessage]:
        for step in range(1, self.max_steps + 1):
            instruction = self._consume_instruction()
            plan = self.planner.plan(
                target=self.memory.target,
                wordlist=self.wordlist,
                scenario_context=self.scenario_context,
                scenario_only=self.scenario_only,
                custom_instruction=instruction,
            )
            text = (
                f"Step {step}\n"
                f"Summary: {plan.summary}\n"
                f"Reasoning: {plan.reasoning}\n"
                f"Planner: {plan.source}"
            )
            self.memory.record_conversation("assistant", text)
            yield AgentMessage(
                type=MessageType.TEXT,
                content=text,
                metadata={"step": step, "plan_source": plan.source},
            )

            if plan.action.type == "stop":
                yield AgentMessage(
                    type=MessageType.RESULT,
                    content={
                        "success": True,
                        "status": "completed",
                        "reason": plan.action.message or plan.summary,
                    },
                )
                return

            if plan.action.type == "ask_user":
                yield AgentMessage(
                    type=MessageType.RESULT,
                    content={
                        "success": True,
                        "status": "paused",
                        "reason": plan.action.message or plan.summary,
                    },
                )
                return

            if plan.action.type != "run_tool" or not plan.action.tool:
                yield AgentMessage(
                    type=MessageType.ERROR,
                    content=f"Unsupported action: {plan.action.type}",
                )
                return

            if self.scenario_only:
                yield AgentMessage(
                    type=MessageType.RESULT,
                    content={
                        "success": True,
                        "status": "paused",
                        "reason": "Scenario-only mode blocks all command execution.",
                    },
                )
                return

            preview = self._preview_command(plan.action)
            yield AgentMessage(
                type=MessageType.TOOL_START,
                content={"command": preview, "risk": plan.action.risk},
                tool_name=plan.action.tool,
                tool_args=plan.action.parameters,
                metadata={"command": preview, "risk": plan.action.risk},
            )

            if self.approval_callback is not None:
                approved = self.approval_callback(
                    plan.action.tool,
                    preview,
                    plan.action.risk,
                )
                if not approved:
                    yield AgentMessage(
                        type=MessageType.RESULT,
                        content={
                            "success": True,
                            "status": "paused",
                            "reason": f"Execution of {plan.action.tool} was not approved.",
                        },
                    )
                    return

            tool = self.tool_registry.get(plan.action.tool)
            self.memory.record_command(tool.name, preview, plan.action.risk)
            result = tool.run(**plan.action.parameters)
            self.memory.ingest_tool_result(result.to_dict())

            yield AgentMessage(
                type=MessageType.TOOL_RESULT,
                content=result.to_dict(),
                tool_name=tool.name,
                tool_args=plan.action.parameters,
            )

        yield AgentMessage(
            type=MessageType.RESULT,
            content={
                "success": True,
                "status": "completed",
                "reason": f"Reached max steps ({self.max_steps}).",
            },
        )

    def _consume_instruction(self) -> str | None:
        if self._pending_instruction:
            instruction = self._pending_instruction
            self._pending_instruction = None
            if self.custom_instruction:
                return f"{self.custom_instruction}\n\nOperator note: {instruction}"
            return instruction
        return self.custom_instruction

    def _preview_command(self, action: AgentAction) -> list[str]:
        if action.tool == "nmap":
            preview = ["nmap", "-Pn", "--open"]
            if action.parameters.get("version_detection", True):
                preview.append("-sV")
            if action.parameters.get("ports"):
                preview.extend(["-p", str(action.parameters["ports"])])
            else:
                preview.extend(["--top-ports", str(action.parameters.get("top_ports", 1000))])
            preview.extend(["-oG", "-", action.parameters["target"]])
            return preview
        if action.tool == "ffuf":
            url = action.parameters["url"]
            fuzz_url = url if "FUZZ" in url else f"{url.rstrip('/')}/FUZZ"
            return ["ffuf", "-u", fuzz_url, "-w", action.parameters["wordlist"], "-of", "json", "-o", "<tempfile>"]
        if action.tool == "gobuster":
            return ["gobuster", "dir", "-u", action.parameters["url"], "-w", action.parameters["wordlist"], "-q"]
        if action.tool == "generic_command":
            return list(action.parameters.get("command", []))
        return [action.tool or "unknown"]
