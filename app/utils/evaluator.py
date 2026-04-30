"""
Post-generation evaluation utilities.

Two checks are performed after every summarization:

1. **Length constraint** — the summary must be ≤ 100 words.
2. **Hallucination heuristic** — we look for named entities (capitalized multi-word
   phrases, percentages, dollar figures, dates) in the summary that do NOT appear
   in the original article. These are flagged as potential hallucinations.

This is intentionally lightweight (no external NER model) to keep the system
dependency-free and fast. For production, replace or augment with an NLI model
(e.g., cross-encoder/nli-deberta-v3-base) for entailment-based grounding.
"""

import re
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_count(text: str) -> int:
    return len(text.split())


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for loose matching."""
    return re.sub(r"[^a-z0-9\s]", "", text.lower())


def _extract_candidate_entities(summary: str) -> List[str]:
    """
    Extract candidate entities from the summary that we will try to ground.

    We look for:
    - Capitalized multi-word phrases (likely named entities)
    - Dollar / percentage figures
    - Year-like numbers
    """
    candidates: List[str] = []

    # Capitalized sequences (Named Entity heuristic)
    caps_pattern = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", summary)
    candidates.extend(caps_pattern)

    # Single capitalised words that look like tickers or orgs (all-caps, 2-5 chars)
    ticker_pattern = re.findall(r"\b([A-Z]{2,5})\b", summary)
    candidates.extend(ticker_pattern)

    # Monetary values: $5.2B, $300 million, etc.
    money_pattern = re.findall(r"\$[\d.,]+\s*(?:billion|million|trillion|B|M|T)?", summary, re.IGNORECASE)
    candidates.extend(money_pattern)

    # Percentages: 3.5%, 12 percent
    pct_pattern = re.findall(r"\d+\.?\d*\s*(?:%|percent)", summary, re.IGNORECASE)
    candidates.extend(pct_pattern)

    # Four-digit years
    year_pattern = re.findall(r"\b(20\d{2}|19\d{2})\b", summary)
    candidates.extend(year_pattern)

    return list(set(candidates))


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------

def evaluate_summary(
    summary: str,
    source_article: str,
    max_words: int = 100,
) -> Tuple[int, bool, str, List[str]]:
    """
    Evaluate the generated summary against quality constraints.

    Args:
        summary:        The LLM-generated summary string.
        source_article: The original article text used for grounding checks.
        max_words:      Maximum allowed word count (default 100).

    Returns:
        Tuple of (word_count, within_limit, hallucination_risk, hallucination_flags)
        where hallucination_risk is 'low' | 'medium' | 'high'.
    """
    word_count = _word_count(summary)
    within_limit = word_count <= max_words

    # Grounding check
    normalized_article = _normalize(source_article)
    candidates = _extract_candidate_entities(summary)
    flags: List[str] = []

    for entity in candidates:
        normalized_entity = _normalize(entity)
        # Skip very short tokens — they are too common to be meaningful signals
        if len(normalized_entity) < 3:
            continue
        if normalized_entity not in normalized_article:
            flags.append(entity)

    # Risk tiers
    if len(flags) == 0:
        risk = "low"
    elif len(flags) <= 2:
        risk = "medium"
    else:
        risk = "high"

    return word_count, within_limit, risk, flags
