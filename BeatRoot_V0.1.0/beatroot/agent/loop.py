from __future__ import annotations

import logging
from datetime import UTC, datetime

from beatroot.agent.models import AgentPlan
from beatroot.agent.planner import Planner, discover_wordlist
from beatroot.config.models import AppConfig
from beatroot.memory.session import SessionMemory
from beatroot.tools.base import ToolExecutionResult
from beatroot.tools.registry import ToolRegistry

LOGGER = logging.getLogger(__name__)


class AssessmentAgent:
    def __init__(
        self,
        config: AppConfig,
        planner: Planner,
        tool_registry: ToolRegistry,
        memory: SessionMemory,
        console,
    ):
        self.config = config
        self.planner = planner
        self.tool_registry = tool_registry
        self.memory = memory
        self.console = console

    def run(
        self,
        target: str,
        wordlist: str | None = None,
        max_steps: int | None = None,
    ) -> SessionMemory:
        steps = max_steps or self.config.agent.max_steps
        resolved_wordlist = wordlist or discover_wordlist(self.config)

        self.console.banner(
            f"BeatRoot session {self.memory.session_id} for target {target}"
        )
        self.console.info("Authorized use only. Commands will be shown before execution.")

        for step in range(1, steps + 1):
            plan = self.planner.plan(target, wordlist=resolved_wordlist)
            self._show_plan(step, plan)

            action_type = plan.action.type
            if action_type == "stop":
                self.memory.add_note(plan.action.message or plan.summary)
                self.memory.save(self.config.memory.directory)
                self.console.success(plan.action.message or "Stopping assessment loop.")
                break

            if action_type == "ask_user":
                self.memory.add_note(plan.action.message or plan.summary)
                self.memory.save(self.config.memory.directory)
                self.console.warn(plan.action.message or "Operator input required.")
                break

            if action_type != "run_tool" or not plan.action.tool:
                self.console.error(f"Unsupported planner action: {action_type}")
                break

            should_run = self._confirm_action(plan)
            if not should_run:
                self.memory.add_note(f"Skipped action: {plan.action.message or plan.summary}")
                self.memory.save(self.config.memory.directory)
                self.console.warn("Action skipped by policy or operator choice.")
                break

            result = self._execute_plan(plan)
            self._handle_result(result)

        return self.memory

    def _show_plan(self, step: int, plan: AgentPlan) -> None:
        self.console.section(f"Step {step}")
        self.console.info(f"Summary: {plan.summary}")
        if self.config.agent.show_reasoning:
            self.console.info(f"Reasoning: {plan.reasoning}")
        self.console.info(f"Planner source: {plan.source}")
        if plan.action.type == "run_tool" and plan.action.tool:
            tool = self.tool_registry.get(plan.action.tool)
            preview = self._preview_command(plan)
            self.console.info(f"Next tool: {tool.name}")
            self.console.info(f"Command: {' '.join(preview)}")

    def _preview_command(self, plan: AgentPlan) -> list[str]:
        tool_name = plan.action.tool
        if tool_name == "nmap":
            params = plan.action.parameters
            preview = ["nmap", "-Pn", "--open"]
            if params.get("version_detection", True):
                preview.append("-sV")
            if params.get("ports"):
                preview.extend(["-p", str(params["ports"])])
            else:
                preview.extend(["--top-ports", str(params.get("top_ports", 1000))])
            preview.extend(["-oG", "-", params["target"]])
            return preview
        if tool_name == "ffuf":
            params = plan.action.parameters
            url = params["url"] if "FUZZ" in params["url"] else f"{params['url'].rstrip('/')}/FUZZ"
            return ["ffuf", "-u", url, "-w", params["wordlist"], "-of", "json", "-o", "<tempfile>"]
        if tool_name == "gobuster":
            params = plan.action.parameters
            return ["gobuster", "dir", "-u", params["url"], "-w", params["wordlist"], "-q"]
        if tool_name == "generic_command":
            return plan.action.parameters.get("command", [])
        return [tool_name or "unknown"]

    def _confirm_action(self, plan: AgentPlan) -> bool:
        tool_name = plan.action.tool or ""
        risk = plan.action.risk

        if tool_name == "generic_command":
            return self.console.confirm(
                "Generic commands require explicit approval. Execute this command?",
                default=False,
            )

        if self.config.agent.auto_approve_safe_tools:
            return True

        if tool_name in self.config.safety.require_confirmation_for or risk in {"medium", "high"}:
            return self.console.confirm(
                f"Execute {tool_name} with risk level {risk}?",
                default=not self.console.interactive and risk != "high",
            )
        return True

    def _execute_plan(self, plan: AgentPlan) -> ToolExecutionResult:
        tool = self.tool_registry.get(plan.action.tool or "")
        self.memory.record_command(tool.name, self._preview_command(plan), plan.action.risk)
        result = tool.run(**plan.action.parameters)
        self.memory.ingest_tool_result(result.to_dict())
        self.memory.save(self.config.memory.directory)
        return result

    def _handle_result(self, result: ToolExecutionResult) -> None:
        if result.success:
            self.console.success(
                f"{result.tool_name} completed with exit code {result.exit_code}."
            )
        else:
            self.console.warn(
                f"{result.tool_name} finished with exit code {result.exit_code}: {result.stderr.strip() or result.error or 'unknown error'}"
            )

        summary = result.parsed or {}
        hosts = summary.get("hosts", [])
        paths = summary.get("paths", [])
        if hosts:
            host = hosts[0]
            ports = ", ".join(
                f"{entry['port']}/{entry['protocol']} {entry['service']}"
                for entry in host.get("ports", [])
            )
            self.console.info(f"Discovered services: {ports or 'none'}")
        if paths:
            preview = ", ".join(
                f"{entry.get('path')} ({entry.get('status')})" for entry in paths[:10]
            )
            self.console.info(f"Discovered paths: {preview}")


def new_session_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

