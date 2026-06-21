"""End-to-end financial news processing pipeline.

This file is the one place where the whole article journey is visible:
dedup -> classify -> RAG -> summarize -> repair -> evaluate -> store.
Every helper imported here does one smaller job.
"""

from __future__ import annotations

import json
import re
from typing import Any

from evaluator.hallucination import evaluate_hallucination
from processing.chunker import should_chunk, split_article
from processing.classifier import classify_article
from processing.deduplicator import has_seen_url, mark_url_seen
from prompts.aggregate import AGGREGATE_PROMPT, CHUNK_FACT_PROMPT
from prompts.repair import REPAIR_PROMPT
from prompts.single_article import build_single_article_prompt
from prompts.summarize import SUMMARY_PROMPT, TYPE_HINTS
from prompts.system import SYSTEM_PROMPT
from providers.router import call_llm_with_fallback


DEFAULT_SUMMARY_FIELDS = {
    "title": "Untitled financial article",
    "url": None,
    "source": "unknown",
    "article_type": "other",
    "summary": "",
    "key_insights": [],
    "companies": [],
    "metrics": [],
    "sentiment": "neutral",
    "investor_implication": "No investor implication could be determined from the source text.",
    "source_credibility": 0.5,
}


def _extract_json(raw: str) -> dict[str, Any]:
    """Extract a JSON object from model output."""

    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise json.JSONDecodeError("No JSON object found", cleaned, 0)
    return json.loads(match.group(0))


def _repair_json(raw: str) -> dict[str, Any]:
    """Ask the cheap tier to repair malformed JSON without changing facts."""

    repaired = call_llm_with_fallback(
        task_tier="cheap",
        system=SYSTEM_PROMPT,
        prompt=REPAIR_PROMPT.format(broken_json=raw),
        temperature=0,
    )
    return _extract_json(repaired)


def _parse_or_repair(raw: str) -> dict[str, Any]:
    try:
        return _extract_json(raw)
    except json.JSONDecodeError:
        return _repair_json(raw)


def _normalize_summary(summary: dict[str, Any], article: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    """Fill optional/missing model fields with safe values.

    LLMs are instructed to follow the schema, but the API and database should
    still protect themselves against missing keys.
    """

    normalized = DEFAULT_SUMMARY_FIELDS | summary
    if not summary.get("title"):
        normalized["title"] = article.get("title") or DEFAULT_SUMMARY_FIELDS["title"]
    if not summary.get("url"):
        normalized["url"] = article.get("url")
    if not summary.get("source"):
        normalized["source"] = article.get("source", "unknown")
    if not summary.get("article_type"):
        normalized["article_type"] = classification.get("article_type", "other")
    if summary.get("source_credibility") is None:
        normalized["source_credibility"] = article.get("credibility_score", 0.5)
    normalized["source_credibility"] = float(normalized["source_credibility"])
    for list_key in ("key_insights", "companies", "metrics"):
        if not isinstance(normalized.get(list_key), list):
            normalized[list_key] = []
    return normalized


def _summarize_normal(article: dict[str, Any], classification: dict[str, Any], rag_context: str) -> dict[str, Any]:
    article_type = classification.get("article_type", "other")
    prompt = SUMMARY_PROMPT.format(
        type_hint=TYPE_HINTS.get(article_type, TYPE_HINTS["other"]),
        title=article.get("title", "Untitled financial article"),
        url=article.get("url"),
        source=article.get("source", "unknown"),
        credibility_score=article.get("credibility_score", 0.5),
        rag_context=rag_context or "No related historical context found.",
        article_text=article["body"],
    )
    raw = call_llm_with_fallback(
        task_tier="quality",
        system=SYSTEM_PROMPT,
        prompt=prompt,
        temperature=0,
    )
    return _normalize_summary(_parse_or_repair(raw), article, classification)


def _summarize_chunked(article: dict[str, Any], classification: dict[str, Any], rag_context: str) -> dict[str, Any]:
    chunks = split_article(article["body"])
    chunk_facts: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        facts = call_llm_with_fallback(
            task_tier="cheap",
            system=SYSTEM_PROMPT,
            prompt=CHUNK_FACT_PROMPT.format(chunk_text=chunk),
            temperature=0,
        )
        chunk_facts.append(f"Chunk {index}\n{facts}")

    raw = call_llm_with_fallback(
        task_tier="quality",
        system=SYSTEM_PROMPT,
        prompt=AGGREGATE_PROMPT.format(
            title=article.get("title", "Untitled financial article"),
            url=article.get("url"),
            source=article.get("source", "unknown"),
            article_type=classification.get("article_type", "other"),
            credibility_score=article.get("credibility_score", 0.5),
            rag_context=rag_context or "No related historical context found.",
            chunk_facts="\n\n".join(chunk_facts),
        ),
        temperature=0,
    )
    return _normalize_summary(_parse_or_repair(raw), article, classification)


def _attach_evaluation(summary: dict[str, Any], raw_article: str) -> dict[str, Any]:
    evaluation = evaluate_hallucination(summary, raw_article)
    summary["hallucination_risk"] = evaluation["hallucination_risk"]
    summary["unsupported_claims"] = evaluation["unsupported_claims"]
    return summary


def process_ingested_article(article: dict[str, Any]) -> dict[str, Any] | None:
    """Process one article from RSS or EDGAR.

    Returns None when the article was already seen.
    """

    url = article.get("url", "")
    if url and has_seen_url(url):
        return None

    classification = classify_article(article["body"])
    from storage.pgvector_client import embed_text, find_related_context
    from storage.postgres import insert_summary

    rag_context = find_related_context(article["body"])

    if should_chunk(article["body"], classification):
        summary = _summarize_chunked(article, classification, rag_context)
    else:
        summary = _summarize_normal(article, classification, rag_context)

    summary = _attach_evaluation(summary, article["body"])
    summary_id = insert_summary(summary, article["body"], embed_text(article["body"]))
    summary["id"] = summary_id

    if url:
        mark_url_seen(url)

    return summary


def process_single_article(article_text: str) -> dict[str, Any]:
    """Process user-pasted text through the same downstream machinery."""

    from storage.pgvector_client import embed_text, find_related_context
    from storage.postgres import insert_summary

    classification = classify_article(article_text)
    rag_context = find_related_context(article_text)
    article_type = classification.get("article_type", "other")

    article = {
        "title": "User submitted article",
        "url": None,
        "source": "single_article",
        "credibility_score": 0.50,
        "body": article_text,
    }

    if should_chunk(article_text, classification):
        summary = _summarize_chunked(article, classification, rag_context)
    else:
        raw = call_llm_with_fallback(
            task_tier="quality",
            system=SYSTEM_PROMPT,
            prompt=build_single_article_prompt(article_text, article_type, rag_context),
            temperature=0,
        )
        summary = _normalize_summary(_parse_or_repair(raw), article, classification)

    summary = _attach_evaluation(summary, article_text)
    summary_id = insert_summary(summary, article_text, embed_text(article_text))
    summary["id"] = summary_id
    return summary
