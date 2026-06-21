"""Central LLM routing configuration.

This is the only file where provider names and model names are allowed to live.
The processing layer asks for a task tier ("cheap" or "quality") and this
router decides which free-tier provider/model to try first, second, and third.
"""

from collections.abc import Callable

from dotenv import load_dotenv

from providers import gemini_client, groq_client, nvidia_client
from providers.exceptions import AllProvidersExhausted, ProviderConfigurationError, RateLimitError


load_dotenv()


ProviderFn = Callable[[str, str, str, float], str]


MODEL_CHAIN: dict[str, list[tuple[str, str]]] = {
    "cheap": [
        ("groq", "llama-3.1-8b-instant"),
    ],
    "quality": [
        ("groq", "llama-3.3-70b-versatile"),
        ("nvidia", "meta/llama-4-maverick-instruct"),
        ("gemini", "gemini-2.5-flash"),
    ],
}


PROVIDERS: dict[str, ProviderFn] = {
    "groq": groq_client.generate,
    "nvidia": nvidia_client.generate,
    "gemini": gemini_client.generate,
}


def call_llm_with_fallback(
    *,
    task_tier: str,
    system: str,
    prompt: str,
    temperature: float = 0,
) -> str:
    """Call the best available provider for a task tier.

    temperature is defaulted to 0 here so every caller gets deterministic
    behavior unless they explicitly pass the same value. The brief requires
    temperature 0 for every LLM call in this project.
    """

    if temperature != 0:
        raise ValueError("Financial extraction must use temperature=0.")

    chain = MODEL_CHAIN.get(task_tier)
    if not chain:
        raise ValueError(f"Unknown task tier: {task_tier}")

    failures: list[str] = []
    for provider_name, model in chain:
        provider = PROVIDERS[provider_name]
        try:
            return provider(system, prompt, model, temperature)
        except RateLimitError as exc:
            failures.append(f"{provider_name}:{model} rate limited: {exc}")
            continue
        except ProviderConfigurationError as exc:
            failures.append(f"{provider_name}:{model} not configured: {exc}")
            continue
        except Exception as exc:
            failures.append(f"{provider_name}:{model} failed: {exc}")
            continue

    raise AllProvidersExhausted("; ".join(failures))
