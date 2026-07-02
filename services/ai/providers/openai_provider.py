"""OpenAI provider — GPT-4o, GPT-4o-mini, etc."""

import json
import requests
from typing import Optional
from services.ai.prompts import build_prompt

OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider:
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL

    def complete(self, action: str, selected_text: str,
                 full_document: Optional[str] = None, tone: Optional[str] = None,
                 timeout: int = 30) -> dict:
        system_prompt, user_prompt = build_prompt(action, selected_text, full_document, tone)

        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        return {
            "originalText": selected_text,
            "suggestedText": result.get("suggestedText", ""),
            "explanation": result.get("explanation", ""),
            "action": action,
            "provider": "openai",
        }
