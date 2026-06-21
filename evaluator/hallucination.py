"""Simple anti-hallucination evaluator.

This evaluator is intentionally transparent. It does not try to be a perfect
fact-checker; it checks the most dangerous finance mistakes: invented numbers,
percentages, tickers, and named organizations.
"""

from __future__ import annotations

import json
import re
from typing import Any


MONEY_OR_PERCENT_RE = re.compile(
    r"(\$[0-9][0-9,]*(?:\.[0-9]+)?\s?(?:million|billion|m|bn|b)?|[0-9]+(?:\.[0-9]+)?%)",
    re.IGNORECASE,
)
TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
COMPANY_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*)*\s+(?:Inc|Corp|Corporation|Ltd|PLC|LLC|Co)\.?\b"
)


def _flatten_text(value: Any) -> str:
    """Turn nested JSON into one searchable string."""

    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    return json.dumps(value, default=str)


def _claims_from_summary(summary_json: dict[str, Any]) -> set[str]:
    text = _flatten_text(summary_json)
    claims = set(MONEY_OR_PERCENT_RE.findall(text))
    claims.update(COMPANY_RE.findall(text))
    claims.update(ticker for ticker in TICKER_RE.findall(text) if len(ticker) > 1)
    return {claim.strip() for claim in claims if claim.strip()}


def evaluate_hallucination(summary_json: dict[str, Any], source_text: str) -> dict[str, Any]:
    """Return risk level plus unsupported claims.

    A claim is considered supported only if it appears verbatim in the original
    article. This strict rule is easy to understand and useful for a student
    project, though a production system could add fuzzy matching later.
    """

    source_lower = source_text.lower()
    unsupported = [
        claim for claim in sorted(_claims_from_summary(summary_json)) if claim.lower() not in source_lower
    ]

    if not unsupported:
        risk = "low"
    elif len(unsupported) <= 2:
        risk = "medium"
    else:
        risk = "high"

    return {
        "hallucination_risk": risk,
        "unsupported_claims": unsupported,
    }

