from __future__ import annotations

from beatroot.config.models import LLMConfig
from beatroot.llm.base import LLMClient, LLMError
from beatroot.llm.claude import ClaudeLLM
from beatroot.llm.openai_compatible import OpenAICompatibleLLM


def build_llm_client(config: LLMConfig) -> LLMClient:
    provider = config.provider.lower()
    if provider in {"ollama", "openai", "openai-compatible"}:
        return OpenAICompatibleLLM(config)
    if provider == "claude":
        return ClaudeLLM(config)
    raise LLMError(f"Unsupported LLM provider: {config.provider}")

