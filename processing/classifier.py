"""Article classification step."""

from __future__ import annotations

import json

from prompts.classify import CLASSIFY_PROMPT
from prompts.system import SYSTEM_PROMPT
from providers.router import call_llm_with_fallback


DEFAULT_CLASSIFICATION = {
    "article_type": "other",
    "complexity": "medium",
    "contains_financial_data": True,
    "reason": "Fallback classification used because parsing failed.",
}


def classify_article(article_text: str) -> dict:
    """Classify article type and complexity using the cheap LLM tier."""

    raw = call_llm_with_fallback(
        task_tier="cheap",
        system=SYSTEM_PROMPT,
        prompt=CLASSIFY_PROMPT.format(article_text=article_text[:6000]),
        temperature=0,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return DEFAULT_CLASSIFICATION.copy()

