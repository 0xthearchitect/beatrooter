from __future__ import annotations

import requests

from beatroot.config.models import LLMConfig
from beatroot.llm.base import LLMClient, LLMError


class ClaudeLLM(LLMClient):
    def __init__(self, config: LLMConfig):
        self.config = config

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.config.api_key:
            raise LLMError("Claude API key is required.")

        raw_base_url = self.config.base_url.strip()
        if not raw_base_url or raw_base_url == "http://localhost:11434/v1":
            base_url = "https://api.anthropic.com/v1"
        else:
            base_url = raw_base_url.rstrip("/")
        if base_url.endswith("/v1"):
            url = f"{base_url}/messages"
        else:
            url = f"{base_url}/v1/messages"

        try:
            response = requests.post(
                url,
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "max_tokens": 900,
                    "temperature": 0.2,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=self.config.timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f"Claude request failed: {exc}") from exc
        if not response.ok:
            raise LLMError(f"Claude request failed: {response.status_code} {response.text}")
        payload = response.json()
        content = payload.get("content", [])
        if not content:
            raise LLMError(f"Malformed Claude response: {payload}")
        first = content[0]
        if first.get("type") != "text":
            raise LLMError(f"Unexpected Claude content block: {payload}")
        return first["text"]
