"""NVIDIA NIM provider adapter.

NVIDIA NIM exposes an OpenAI-compatible endpoint, so the official `openai`
Python client can be reused here without calling OpenAI's paid API.
"""

import os

from openai import OpenAI

from providers.exceptions import ProviderConfigurationError, RateLimitError


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def generate(system: str, prompt: str, model: str, temperature: float = 0) -> str:
    """Generate text through NVIDIA's OpenAI-compatible NIM endpoint."""

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ProviderConfigurationError("NVIDIA_API_KEY is not set.")

    client = OpenAI(api_key=api_key, base_url=NVIDIA_BASE_URL)
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
