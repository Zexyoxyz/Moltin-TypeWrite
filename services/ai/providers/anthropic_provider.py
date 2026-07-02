"""Anthropic (Claude) provider."""

import json
import re
import requests
from typing import Optional
from services.ai.prompts import build_prompt

ANTHROPIC_API_BASE = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-3-5-haiku-20241022"


class AnthropicProvider:
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL

    def complete(self, action: str, selected_text: str,
                 full_document: Optional[str] = None, tone: Optional[str] = None,
                 timeout: int = 30) -> dict:
        system_prompt, user_prompt = build_prompt(action, selected_text, full_document, tone)

        response = requests.post(
            f"{ANTHROPIC_API_BASE}/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": 2048,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = next(b["text"] for b in data["content"] if b["type"] == "text")
        # Strip possible markdown code fences
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*$", "", text).strip()
        result = json.loads(text)
        return {
            "originalText": selected_text,
            "suggestedText": result.get("suggestedText", ""),
            "explanation": result.get("explanation", ""),
            "action": action,
            "provider": "anthropic",
        }
