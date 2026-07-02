"""Ollama provider — local model inference (requires Ollama installed)."""

import json
import re
import requests
from typing import Optional
from services.ai.prompts import build_prompt

OLLAMA_API_BASE = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"


class OllamaProvider:
    def __init__(self, api_key: str = "", model: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = base_url or OLLAMA_API_BASE
        self.model = model or DEFAULT_MODEL

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.ok
        except Exception:
            return False

    def complete(self, action: str, selected_text: str,
                 full_document: Optional[str] = None, tone: Optional[str] = None,
                 timeout: int = 60) -> dict:
        if not self.is_available():
            raise ConnectionError(
                "Ollama is not running. Please install and start Ollama from https://ollama.ai"
            )
        system_prompt, user_prompt = build_prompt(action, selected_text, full_document, tone)

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "stream": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            raise ValueError("Could not parse JSON from Ollama response")
        result = json.loads(json_match.group())
        return {
            "originalText": selected_text,
            "suggestedText": result.get("suggestedText", ""),
            "explanation": result.get("explanation", ""),
            "action": action,
            "provider": "ollama",
        }
