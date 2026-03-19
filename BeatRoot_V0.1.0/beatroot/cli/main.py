from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from beatroot.cli.console import Console
from beatroot.config import load_config
from beatroot.core import SessionStore, run_assessment
from beatroot.core.backend import AgentMessage, MessageType
from beatroot.llm import LLMError, build_llm_client
from beatroot.logging_utils import configure_logging

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beatroot",
        description="BeatRoot - local-first AI security assessment copilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  beatroot --target 10.10.11.234
  beatroot --target 10.10.11.234 --instruction "WordPress stack, focus on plugins"
  beatroot --target 10.10.11.234 --resume
  beatroot --target 10.10.11.234 --non-interactive --wordlist /usr/share/wordlists/dirb/common.txt
  beatroot --target internal-lab --scenario-json '{"nodes":[{"id":"web1","port":443}]}' --scenario-only
  cat scenario.json | beatroot --target internal-lab --scenario-stdin --scenario-only
        """,
    )
    parser.add_argument("-t", "--target", required=True, help="Target host, IP, or URL")
    parser.add_argument("-i", "--instruction", help="Additional operator context")
    parser.add_argument("-m", "--model", help="Override the configured model")
    parser.add_argument("-c", "--config", help="Path to config YAML file")
    parser.add_argument("-w", "--wordlist", help="Wordlist path for web enumeration")
    parser.add_argument("--scenario-file", help="Path to a JSON/text file with scenario evidence")
    parser.add_argument("--scenario-json", help="Inline JSON scenario context from BeatRooter")
    parser.add_argument(
        "--scenario-stdin",
        action="store_true",
        help="Read scenario context from STDIN (for BeatRooter process piping)",
    )
    parser.add_argument(
        "--scenario-only",
        action="store_true",
        help="Disable tool execution and respond only from provided scenario evidence",
    )
    parser.add_argument("--max-steps", type=int, help="Maximum agent steps")
    parser.add_argument(
        "-n",
        "--non-interactive",
        action="store_true",
        help="Run without prompts; high-risk actions are not auto-approved",
    )
    parser.add_argument("-r", "--resume", action="store_true", help="Resume latest session for target")
    parser.add_argument("--session-id", help="Resume a specific session by ID")
    parser.add_argument("--list-sessions", action="store_true", help="List sessions for target and exit")
    parser.add_argument("--raw", action="store_true", help="Show raw step streaming output")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser


def print_banner(console: Console) -> None:
    console.info("")


def render_message(console: Console, message: AgentMessage, raw: bool = False) -> None:
    if raw:
        console.info(f"[{message.type.value}] {message.content}")
        return

    if message.type == MessageType.TEXT:
        step = message.metadata.get("step", "?")
        console.section(f"Step {step}")
        for line in str(message.content).splitlines():
            console.event(line, level="info")
        return

    if message.type == MessageType.TOOL_START:
        command = " ".join(message.metadata.get("command", []))
        risk = message.metadata.get("risk", "low")
        console.event(f"Tool: {message.tool_name}", level="info")
        console.event(f"Risk: {risk}", level="info")
        console.event(f"Command: {command}", level="info")
        return

    if message.type == MessageType.TOOL_RESULT:
        result = message.content
        stderr = result.get("stderr", "").strip()
        if result.get("success"):
            console.event(f"{message.tool_name} completed.", level="success")
        else:
            console.event(
                f"{message.tool_name} failed: {stderr or result.get('error', 'unknown error')}",
                level="warn",
            )

        parsed = result.get("parsed") or {}
        hosts = parsed.get("hosts", [])
        paths = parsed.get("paths", [])
        if hosts:
            first = hosts[0]
            ports = ", ".join(
                f"{entry['port']}/{entry['protocol']} {entry['service']}"
                for entry in first.get("ports", [])
            )
            if ports:
                console.event(f"Services: {ports}", level="info")
        if paths:
            preview = ", ".join(
                f"{entry.get('path')} ({entry.get('status')})" for entry in paths[:10]
            )
            if preview:
                console.event(f"Paths: {preview}", level="info")
        return

    if message.type == MessageType.ERROR:
        console.error(str(message.content))
        return

    if message.type == MessageType.RESULT:
        reason = message.content.get("reason", "")
        if message.content.get("status") == "paused":
            console.event(reason or "Session paused.", level="warn")
        else:
            console.event(reason or "Session completed.", level="success")


def build_task(target: str, instruction: str | None) -> str:
    base = f"Assess the authorized target {target}. Start with reconnaissance and safe enumeration."
    if instruction:
        return f"{base}\n\nOperator context:\n{instruction}"
    return base


def load_scenario_context(
    path: str | None,
    inline_json: str | None,
    use_stdin: bool,
) -> str | None:
    if path:
        scenario_path = Path(path)
        if not scenario_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")
        return scenario_path.read_text(encoding="utf-8").strip() or None

    if inline_json:
        payload = json.loads(inline_json)
        return json.dumps(payload, indent=2, ensure_ascii=False)

    if use_stdin:
        return sys.stdin.read().strip() or None

    return None


def resolve_resume_session(target: str, resume: bool, session_id: str | None) -> str | None:
    if session_id:
        return session_id
    if not resume:
        return None
    store = SessionStore()
    latest = store.get_latest(target)
    return latest.session_id if latest else None


def approval_callback_factory(console: Console, non_interactive: bool, auto_approve: bool):
    def approve(tool_name: str, command: list[str], risk: str) -> bool:
        if tool_name == "generic_command":
            return console.confirm(
                "Generic commands require explicit approval. Execute?",
                default=False,
            )
        if auto_approve and risk != "high":
            return True
        if non_interactive:
            return risk not in {"high"}
        return console.confirm(
            f"Execute {' '.join(command)} ?",
            default=risk == "low",
        )

    return approve


def list_sessions(console: Console, target: str) -> int:
    store = SessionStore()
    sessions = store.list_sessions(target=target)
    if not sessions:
        console.info("No sessions found for this target.")
        return 0
    for session in sessions:
        updated_at = session.updated_at or session.created_at
        console.info(
            f"{session.session_id} | {session.status.value} | {updated_at} | {session.task}"
        )
    return 0


def main() -> int:
    args = build_parser().parse_args()
    console = Console(interactive=not args.non_interactive)
    print_banner(console)
    console.splash(args.target)

    if args.list_sessions:
        return list_sessions(console, args.target)

    config = load_config(args.config)
    if args.model:
        config.llm.model = args.model

    log_file = configure_logging(config.logging.level, config.logging.directory)
    LOGGER.info("Logging to %s", log_file)

    llm_client = None
    if config.agent.allow_llm_planning:
        try:
            llm_client = build_llm_client(config.llm)
        except LLMError as exc:
            LOGGER.warning("LLM disabled: %s", exc)

    resume_session_id = resolve_resume_session(args.target, args.resume, args.session_id)
    if args.resume and not resume_session_id:
        console.warn("No existing session found for this target; starting a new one.")

    task = build_task(args.target, args.instruction)
    try:
        scenario_context = load_scenario_context(
            args.scenario_file,
            args.scenario_json,
            args.scenario_stdin,
        )
    except (OSError, json.JSONDecodeError) as exc:
        console.error(str(exc))
        return 1

    scenario_only = args.scenario_only or config.scenario.enabled
    if scenario_only and not scenario_context:
        console.warn("Scenario-only mode enabled without scenario evidence; responses may be limited.")

    result = run_assessment(
        config=config,
        target=args.target,
        task=task,
        model=config.llm.model,
        llm_client=llm_client,
        wordlist=args.wordlist,
        scenario_context=scenario_context,
        scenario_only=scenario_only and config.scenario.enforce_read_only_context,
        max_steps=args.max_steps,
        custom_instruction=args.instruction,
        resume_session_id=resume_session_id,
        on_message=lambda message: render_message(console, message, raw=args.raw),
        approval_callback=approval_callback_factory(
            console,
            non_interactive=args.non_interactive,
            auto_approve=config.agent.auto_approve_safe_tools,
        ),
    )

    if result.get("success"):
        console.info(f"Session ID: {result.get('session_id', 'unknown')}")
        return 0

    console.error(result.get("error", "Unknown error"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
