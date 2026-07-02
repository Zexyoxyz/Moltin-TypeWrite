"""Google Gemini provider."""

import json
import requests
from typing import Optional
from services.ai.prompts import build_prompt

GEMINI_API_BASE = "https://generativelanguage.googleapis.com"
DEFAULT_MODEL = "gemini-1.5-flash"


class GeminiProvider:
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL

    def complete(self, action: str, selected_text: str,
                 full_document: Optional[str] = None, tone: Optional[str] = None,
                 timeout: int = 30) -> dict:
        system_prompt, user_prompt = build_prompt(action, selected_text, full_document, tone)
        url = f"{GEMINI_API_BASE}/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json",
                },
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
        return {
            "originalText": selected_text,
            "suggestedText": result.get("suggestedText", ""),
            "explanation": result.get("explanation", ""),
            "action": action,
            "provider": "gemini",
        }
