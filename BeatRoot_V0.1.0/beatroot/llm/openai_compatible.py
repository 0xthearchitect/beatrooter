from __future__ import annotations

import requests

from beatroot.config.models import LLMConfig
from beatroot.llm.base import LLMClient, LLMError


class OpenAICompatibleLLM(LLMClient):
    def __init__(self, config: LLMConfig):
        self.config = config

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        try:
            response = requests.post(
                url,
                headers=headers,
                json={
                    "model": self.config.model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=self.config.timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc
        if not response.ok:
            raise LLMError(
                f"OpenAI-compatible request failed: {response.status_code} {response.text}"
            )
        payload = response.json()
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Malformed OpenAI-compatible response: {payload}") from exc
