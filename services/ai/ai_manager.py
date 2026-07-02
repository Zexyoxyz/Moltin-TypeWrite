"""
AI Manager — routes requests to the correct provider.
Handles API key decryption and provider instantiation.
"""

from typing import Optional
from config.crypto import decrypt
from config.settings import SettingsManager

from services.ai.providers.groq_provider import GroqProvider
from services.ai.providers.openai_provider import OpenAIProvider
from services.ai.providers.anthropic_provider import AnthropicProvider
from services.ai.providers.gemini_provider import GeminiProvider
from services.ai.providers.ollama_provider import OllamaProvider


class AIManager:
    def __init__(self, settings: SettingsManager):
        self.settings = settings

    def _resolve_key(self, provider: str) -> str:
        """Decrypts and returns the API key for the given provider."""
        encrypted_keys = self.settings.get("encrypted_keys", {})
        encrypted = encrypted_keys.get(provider)

        if encrypted:
            decrypted = decrypt(encrypted)
            if decrypted:
                return decrypted


        raise ValueError(
            f"No API key configured for '{provider}'. "
            "Please add your API key in Settings → AI Providers."
        )

    def _create_provider(self, provider: str):
        """Instantiates the appropriate provider."""
        key = self._resolve_key(provider)
        match provider:
            case "groq":
                return GroqProvider(key)
            case "openai":
                return OpenAIProvider(key)
            case "anthropic":
                return AnthropicProvider(key)
            case "gemini":
                return GeminiProvider(key)
            case "ollama":
                return OllamaProvider(key)
            case _:
                raise ValueError(f"Unknown provider: {provider}")

    def request(
        self,
        action: str,
        selected_text: str,
        full_document: Optional[str] = None,
        tone: Optional[str] = None,
    ) -> dict:
        """Submit an AI writing request and return a suggestion dict."""
        provider = self.settings.get("ai_provider", "groq")
        instance = self._create_provider(provider)
        return instance.complete(action, selected_text, full_document, tone)

    def get_active_provider(self) -> str:
        return self.settings.get("ai_provider", "groq")

    def get_available_providers(self) -> list[str]:
        """Returns providers that have keys configured (groq is always available)."""
        all_providers = ["groq", "openai", "anthropic", "gemini", "ollama"]
        keys = self.settings.get("encrypted_keys", {})
        return [
            p for p in all_providers
            if p == "groq" or p in keys
        ]
