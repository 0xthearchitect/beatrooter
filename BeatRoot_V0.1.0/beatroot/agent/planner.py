from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from beatroot.agent.models import AgentAction, AgentPlan
from beatroot.agent.prompting import SYSTEM_PROMPT, build_planning_prompt
from beatroot.config.models import AppConfig
from beatroot.llm.base import LLMClient, LLMError
from beatroot.memory.session import SessionMemory
from beatroot.tools.registry import ToolRegistry

LOGGER = logging.getLogger(__name__)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in planner response.")
    return json.loads(text[start : end + 1])


def discover_wordlist(config: AppConfig) -> str | None:
    if config.tool_defaults.web_wordlist:
        candidate = Path(config.tool_defaults.web_wordlist)
        if candidate.exists():
            return str(candidate)

    common_paths = [
        "/usr/share/wordlists/dirb/common.txt",
        "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
        "/usr/share/seclists/Discovery/Web-Content/common.txt",
    ]
    for candidate in common_paths:
        if Path(candidate).exists():
            return candidate
    return None


def _wordlist_exists(path: str | None) -> bool:
    if not path:
        return False
    candidate = Path(path)
    return candidate.exists() and candidate.is_file()


class Planner:
    def __init__(
        self,
        config: AppConfig,
        memory: SessionMemory,
        tool_registry: ToolRegistry,
        llm_client: LLMClient | None = None,
    ):
        self.config = config
        self.memory = memory
        self.tool_registry = tool_registry
        self.llm_client = llm_client

    def plan(
        self,
        target: str,
        wordlist: str | None = None,
        scenario_context: str | None = None,
        scenario_only: bool = False,
        custom_instruction: str | None = None,
    ) -> AgentPlan:
        if self.config.agent.allow_llm_planning and self.llm_client is not None:
            try:
                return self._plan_with_llm(
                    target,
                    wordlist,
                    scenario_context,
                    scenario_only,
                    custom_instruction,
                )
            except (LLMError, ValueError, json.JSONDecodeError) as exc:
                LOGGER.warning("Falling back to heuristic planning: %s", exc)
        return self._heuristic_plan(target, wordlist, scenario_context, scenario_only)

    def _plan_with_llm(
        self,
        target: str,
        wordlist: str | None,
        scenario_context: str | None,
        scenario_only: bool,
        custom_instruction: str | None,
    ) -> AgentPlan:
        prompt = build_planning_prompt(
            target=target,
            memory_summary=self.memory.summarize(),
            available_tools=self.tool_registry.available_tools(),
            wordlist=wordlist,
            scenario_context=scenario_context,
            scenario_only=scenario_only,
            custom_instruction=custom_instruction,
        )
        response_text = self.llm_client.complete(SYSTEM_PROMPT, prompt)
        payload = _extract_json_object(response_text)
        action_payload = payload.get("action", {})
        action = AgentAction(
            type=action_payload.get("type", "ask_user"),
            tool=action_payload.get("tool"),
            parameters=action_payload.get("parameters") or {},
            message=action_payload.get("message", ""),
            risk=action_payload.get("risk", "low"),
        )
        return AgentPlan(
            summary=payload.get("summary", "Planner response received."),
            reasoning=payload.get("reasoning", "No reasoning provided."),
            action=action,
            source="llm",
        )

    def _heuristic_plan(
        self,
        target: str,
        wordlist: str | None,
        scenario_context: str | None,
        scenario_only: bool,
    ) -> AgentPlan:
        if scenario_only:
            return AgentPlan(
                summary="Scenario mode is active with command execution disabled.",
                reasoning="Use only the provided scenario evidence and ask the operator for more context when evidence is missing.",
                action=AgentAction(
                    type="ask_user",
                    message=(
                        "Read-only scenario mode active. Share more scenario details "
                        "or disable scenario-only mode to allow tool execution."
                    ),
                    risk="low",
                ),
                source="heuristic",
            )

        if not any(command["tool"] == "nmap" for command in self.memory.commands):
            return AgentPlan(
                summary="No reconnaissance data is available yet.",
                reasoning="Start with a bounded nmap scan to identify reachable services before attempting any targeted enumeration.",
                action=AgentAction(
                    type="run_tool",
                    tool="nmap",
                    parameters={
                        "target": target,
                        "top_ports": self.config.tool_defaults.nmap_top_ports,
                        "version_detection": True,
                    },
                    message="Run a bounded nmap version scan.",
                    risk="medium",
                ),
                source="heuristic",
            )

        http_candidates = []
        for port in self.memory.ports.values():
            service = (port.get("service") or "").lower()
            port_number = port.get("port")
            if "http" in service or port_number in {80, 443, 8000, 8080, 8443}:
                http_candidates.append(port)

        if http_candidates and not self.memory.web_paths:
            missing_wordlist_error = self._detect_missing_wordlist_error()
            if missing_wordlist_error:
                return AgentPlan(
                    summary="Web enumeration could not continue because the configured wordlist file was not found.",
                    reasoning="The last directory-enumeration command failed due to a missing wordlist file. Re-running the same command would repeat the failure.",
                    action=AgentAction(
                        type="ask_user",
                        message=(
                            "Set a valid wordlist path with --wordlist or config.tool_defaults.web_wordlist, "
                            f"then retry. Last error: {missing_wordlist_error}"
                        ),
                        risk="low",
                    ),
                    source="heuristic",
                )

            wildcard_error = self._detect_gobuster_wildcard_error()
            if wildcard_error:
                failed_url = wildcard_error.get("url", "")
                can_retry_with_https = failed_url.startswith("http://") and any(
                    candidate.get("port") in {443, 8443}
                    or "https" in (candidate.get("service") or "").lower()
                    for candidate in http_candidates
                )
                if not can_retry_with_https:
                    stderr = wildcard_error.get("stderr", "")
                    return AgentPlan(
                        summary="Web enumeration paused because wildcard responses were detected.",
                        reasoning="Gobuster reported that non-existing paths look valid under the current matching options, so repeating the same command is unlikely to produce useful results.",
                        action=AgentAction(
                            type="ask_user",
                            message=(
                                "Retry with adjusted gobuster options (for example excluding a status code/length or enabling wildcard mode), "
                                f"then continue. Last error: {stderr}"
                            ),
                            risk="low",
                        ),
                        source="heuristic",
                    )

            if wordlist and not _wordlist_exists(wordlist):
                return AgentPlan(
                    summary="The configured web wordlist path is invalid.",
                    reasoning="Web enumeration needs a readable wordlist file, but the configured path does not exist.",
                    action=AgentAction(
                        type="ask_user",
                        message=(
                            f"Wordlist file not found: {wordlist}. "
                            "Provide a valid path with --wordlist or config.tool_defaults.web_wordlist."
                        ),
                        risk="low",
                    ),
                    source="heuristic",
                )

            if not wordlist:
                return AgentPlan(
                    summary="A web service was discovered, but no wordlist is configured.",
                    reasoning="Web enumeration is a reasonable next step, but it needs a wordlist path for ffuf or gobuster.",
                    action=AgentAction(
                        type="ask_user",
                        message="Provide a web wordlist path with --wordlist or config.tool_defaults.web_wordlist to continue enumeration.",
                        risk="low",
                    ),
                    source="heuristic",
                )

            primary = self._select_primary_web_candidate(http_candidates)
            scheme = "https" if primary.get("port") in {443, 8443} else "http"
            url = f"{scheme}://{target}"
            if primary.get("port") not in {80, 443}:
                url = f"{url}:{primary.get('port')}"
            ffuf_tool = self.tool_registry.get("ffuf")
            gobuster_tool = self.tool_registry.get("gobuster")
            if ffuf_tool.binary_exists("ffuf"):
                chosen_tool = "ffuf"
            elif gobuster_tool.binary_exists("gobuster"):
                chosen_tool = "gobuster"
            else:
                return AgentPlan(
                    summary="A web service was discovered, but no web enumeration tool is installed.",
                    reasoning="Either ffuf or gobuster is needed for the next automated step.",
                    action=AgentAction(
                        type="ask_user",
                        message="Install ffuf or gobuster, or continue with manual inspection.",
                        risk="low",
                    ),
                    source="heuristic",
                )
            if self._already_ran_web_enum_without_findings(chosen_tool, url, wordlist):
                return AgentPlan(
                    summary="Web content discovery completed without new paths.",
                    reasoning="The last directory-enumeration run with the same target and wordlist finished successfully and returned no paths, so repeating it is unlikely to add value.",
                    action=AgentAction(
                        type="stop",
                        message="No additional web paths were discovered in the latest enumeration pass.",
                        risk="low",
                    ),
                    source="heuristic",
                )
            return AgentPlan(
                summary="A web service is present and ready for content discovery.",
                reasoning="Run a directory enumeration pass to identify application paths that can guide further manual analysis.",
                action=AgentAction(
                    type="run_tool",
                    tool=chosen_tool,
                    parameters={"url": url, "wordlist": wordlist},
                    message=f"Run {chosen_tool} for directory enumeration.",
                    risk="medium",
                ),
                source="heuristic",
            )

        return AgentPlan(
            summary="Current enumeration pass is complete.",
            reasoning="The tool has captured the currently available service inventory. Further action should be selected manually based on authorization scope and findings.",
            action=AgentAction(
                type="stop",
                message="No additional safe automated enumeration step is obvious from the current findings.",
                risk="low",
            ),
            source="heuristic",
        )

    def _detect_missing_wordlist_error(self) -> str | None:
        for result in reversed(self.memory.tool_results):
            tool_name = (result.get("tool_name") or "").lower()
            if tool_name not in {"gobuster", "ffuf"}:
                continue
            if result.get("success", True):
                continue
            stderr = (result.get("stderr") or "").strip()
            lowered = stderr.lower()
            if "wordlist" in lowered and (
                "no such file or directory" in lowered
                or "cannot find" in lowered
                or "does not exist" in lowered
            ):
                return stderr
        return None

    def _detect_gobuster_wildcard_error(self) -> dict[str, str] | None:
        for result in reversed(self.memory.tool_results):
            if (result.get("tool_name") or "").lower() != "gobuster":
                continue
            if result.get("success", True):
                continue
            stderr = (result.get("stderr") or "").strip()
            lowered = stderr.lower()
            if (
                "non existing urls" in lowered
                and "exclude the response length or the status code" in lowered
            ):
                metadata = result.get("metadata") or {}
                return {
                    "stderr": stderr,
                    "url": str(metadata.get("url") or ""),
                }
        return None

    def _select_primary_web_candidate(self, http_candidates: list[dict[str, Any]]) -> dict[str, Any]:
        def score(candidate: dict[str, Any]) -> tuple[int, int]:
            port = int(candidate.get("port") or 0)
            service = (candidate.get("service") or "").lower()
            if port in {443, 8443} or "https" in service:
                return (0, port)
            if "http" in service or port in {80, 8000, 8080}:
                return (1, port)
            return (2, port)

        return sorted(http_candidates, key=score)[0]

    def _already_ran_web_enum_without_findings(
        self,
        tool_name: str,
        url: str,
        wordlist: str | None,
    ) -> bool:
        if not wordlist:
            return False
        expected_url = url if tool_name == "gobuster" else f"{url.rstrip('/')}/FUZZ"
        for result in reversed(self.memory.tool_results):
            if (result.get("tool_name") or "").lower() != tool_name.lower():
                continue
            if not result.get("success", False):
                continue
            metadata = result.get("metadata") or {}
            if str(metadata.get("url") or "") != expected_url:
                continue
            if str(metadata.get("wordlist") or "") != wordlist:
                continue
            parsed = result.get("parsed") or {}
            if not parsed.get("paths"):
                return True
            return False
        return False
