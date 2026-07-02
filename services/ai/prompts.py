"""
AI prompt templates for all supported writing actions.
Each prompt instructs the model to return strict JSON:
  { "suggestedText": "...", "explanation": "..." }
"""

from typing import Optional


SYSTEM_BASE = """You are an expert writing assistant embedded in Moltin TypeWriter, a knowledge management application.
Your responses MUST always be valid JSON in this exact format:
{"suggestedText": "<your improved text>", "explanation": "<a clear explanation of what you changed and why>"}
Return ONLY the JSON object. Do NOT wrap it in markdown code blocks or add any other text."""


def build_prompt(
    action: str,
    selected_text: str,
    full_document: Optional[str] = None,
    tone: Optional[str] = None,
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for the given action.
    """
    doc_ctx = ""
    if full_document:
        snippet = full_document[:2000]
        doc_ctx = f"\n\nFull document context (for reference only):\n{snippet}"

    prompts = {
        "grammar": (
            SYSTEM_BASE,
            f"Fix all grammar errors in the text below. Preserve meaning and style exactly."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "spelling": (
            SYSTEM_BASE,
            f"Fix all spelling mistakes in the text below. Preserve formatting and intent."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "restructure": (
            SYSTEM_BASE,
            f"Restructure the text below to improve logical flow and readability. Keep all core information."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "clarity": (
            SYSTEM_BASE,
            f"Improve the clarity of the text below. Remove ambiguity, simplify complex sentences, be more direct."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "tone": (
            SYSTEM_BASE,
            f"Rewrite the text below in a {tone or 'professional'} tone. Keep all information, adapt the language."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "rephrase": (
            SYSTEM_BASE,
            f"Rephrase the text below using different words and sentence structures while keeping the exact same meaning."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "expand": (
            SYSTEM_BASE,
            f"Expand the following brief text into a well-developed paragraph. Add context, examples, and detail."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "summarise": (
            SYSTEM_BASE,
            f"Create a concise, accurate summary of the text below. Capture all key points in as few words as possible."
            f"{doc_ctx}\n\nText:\n{selected_text}",
        ),
        "brainstorm": (
            SYSTEM_BASE.replace(
                '"suggestedText": "<your improved text>"',
                '"suggestedText": "<a formatted numbered list of ideas>"',
            ),
            f"Generate 5-8 creative and diverse brainstorming ideas related to the topic/text below. Format as a numbered markdown list."
            f"{doc_ctx}\n\nTopic:\n{selected_text}",
        ),
        "autocomplete": (
            """You are an intelligent autocomplete assistant in a markdown note-taking app.
Return ONLY valid JSON: {"suggestedText": "<continuation only, not the original>", "explanation": "Autocomplete suggestion"}
Write a natural continuation of 1-3 sentences.""",
            f"Continue the following text naturally:\n{selected_text}",
        ),
        "style-check": (
            SYSTEM_BASE.replace(
                '"suggestedText": "<your improved text>"',
                '"suggestedText": "<the full revised document>"',
            ),
            f"Review and improve style consistency in the document. Fix: inconsistent tense, mixed formality, repetitive structures, unclear transitions.\n\nDocument:\n{selected_text}",
        ),
        "explain": (
            SYSTEM_BASE.replace(
                '"suggestedText": "<your improved text>"',
                '"suggestedText": "<unchanged — same as input>"',
            ).replace(
                '"explanation": "<a clear explanation of what you changed and why>"',
                '"explanation": "<detailed analysis: strengths, weaknesses, and specific actionable suggestions>"',
            ),
            f"Analyse the text below and provide detailed, constructive feedback.\n\nText:\n{selected_text}",
        ),
    }

    if action not in prompts:
        return SYSTEM_BASE, f"Improve the following text:\n{selected_text}"

    return prompts[action]
