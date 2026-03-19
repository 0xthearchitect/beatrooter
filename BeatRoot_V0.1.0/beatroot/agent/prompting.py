from __future__ import annotations

import json

from beatroot.prompts.pentesting import get_assessment_prompt

SYSTEM_PROMPT = f"{get_assessment_prompt()}\n\nReturn exactly one JSON object and nothing else."


def build_planning_prompt(
    target: str,
    memory_summary: dict,
    available_tools: dict[str, str],
    wordlist: str | None,
    custom_instruction: str | None = None,
) -> str:
    tool_descriptions = "\n".join(
        f"- {name}: {description}" for name, description in available_tools.items()
    )
    return f"""
Target: {target}
Operator context: {custom_instruction or "none"}

Session summary:
{json.dumps(memory_summary, indent=2)}

Available tools:
{tool_descriptions}

Wordlist configured: {wordlist or "none"}

Choose the single best next step for authorized reconnaissance or enumeration only.

Response schema:
{{
  "summary": "short summary of the current situation",
  "reasoning": "brief step-by-step explanation",
  "action": {{
    "type": "run_tool" | "ask_user" | "stop",
    "tool": "nmap" | "ffuf" | "gobuster" | "generic_command" | null,
    "parameters": {{}},
    "message": "question or stop reason",
    "risk": "low" | "medium" | "high"
  }}
}}
""".strip()
