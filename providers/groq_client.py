"""Groq provider adapter.

Only provider modules import provider SDKs. Other project layers call
providers.router.call_llm_with_fallback() instead.
"""

import os

from groq import Groq

from providers.exceptions import ProviderConfigurationError, RateLimitError


def generate(system: str, prompt: str, model: str, temperature: float = 0) -> str:
    """Generate text using Groq's chat-completions API."""

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ProviderConfigurationError("GROQ_API_KEY is not set.")

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:
        if "rate" in str(exc).lower() or "quota" in str(exc).lower():
            raise RateLimitError(str(exc)) from exc
        raise

    return response.choices[0].message.content or ""
