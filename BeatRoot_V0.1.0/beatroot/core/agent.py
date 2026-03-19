from __future__ import annotations

from typing import Callable

from beatroot.agent.planner import Planner
from beatroot.config.models import AppConfig
from beatroot.core.backend import AgentMessage, PlanningAgentBackend
from beatroot.core.controller import AgentController, load_memory_for_session
from beatroot.core.session import SessionStore
from beatroot.llm.base import LLMClient
from beatroot.memory import SessionMemory
from beatroot.tools.registry import build_tool_registry


def run_assessment(
    config: AppConfig,
    target: str,
    task: str,
    model: str,
    llm_client: LLMClient | None = None,
    wordlist: str | None = None,
    max_steps: int | None = None,
    custom_instruction: str | None = None,
    resume_session_id: str | None = None,
    on_message: Callable[[AgentMessage], None] | None = None,
    approval_callback: Callable[[str, list[str], str], bool] | None = None,
) -> dict:
    session_store = SessionStore()
    memory: SessionMemory
    if resume_session_id:
        memory = load_memory_for_session(config, target, resume_session_id)
    else:
        session = session_store.create(target, task, model)
        memory = SessionMemory(target=target, session_id=session.session_id)

    tool_registry = build_tool_registry(config)
    planner = Planner(
        config=config,
        memory=memory,
        tool_registry=tool_registry,
        llm_client=llm_client,
    )
    backend = PlanningAgentBackend(
        planner=planner,
        tool_registry=tool_registry,
        memory=memory,
        wordlist=wordlist,
        max_steps=max_steps or config.agent.max_steps,
        custom_instruction=custom_instruction,
        approval_callback=approval_callback,
    )
    controller = AgentController(
        config=config,
        backend=backend,
        session_store=session_store,
        on_message=on_message,
    )
    return controller.run(
        target=target,
        task=task,
        model=model,
        memory=memory,
        resume_session_id=resume_session_id,
    )
