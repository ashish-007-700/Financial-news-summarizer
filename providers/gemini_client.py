"""Google Gemini provider adapter."""

import os

from google import genai
from google.genai import types

from providers.exceptions import ProviderConfigurationError, RateLimitError


def generate(system: str, prompt: str, model: str, temperature: float = 0) -> str:
    """Generate text using Google AI Studio / Gemini."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ProviderConfigurationError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
            ),
        )
    except Exception as exc:
        if "rate" in str(exc).lower() or "quota" in str(exc).lower():
            raise RateLimitError(str(exc)) from exc
        raise

    return response.text or ""
