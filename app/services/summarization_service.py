"""
Core summarization service.

Orchestrates the full pipeline:
  1. Input validation
  2. RAG context retrieval
  3. Chunking (if article is too long)
  4. LLM call(s) via LangChain
  5. JSON parsing with retry
  6. Post-generation evaluation

Design decisions:
- We use LangChain's LCEL (pipe operator) for clean, composable chains.
- JSON is extracted from the raw LLM output via a dedicated parser that
  handles minor formatting issues (e.g. model wrapping JSON in ```json blocks).
- A single retry is attempted if JSON parsing fails the first time.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from app.prompts.financial_prompts import (
    AGGREGATE_PROMPT,
    CHUNK_PROMPT,
    SUMMARIZE_PROMPT,
)
from app.services.rag_service import RAGService
from app.utils.evaluator import evaluate_summary
from app.utils.text_splitter import CHUNK_MAX_TOKENS, count_tokens, split_into_chunks

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> Dict[str, Any]:
    """
    Parse JSON from raw LLM output.

    Handles cases where the model wraps JSON in markdown code fences.
    Raises ValueError if no valid JSON object is found.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    # Find the outermost JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM output:\n{raw[:500]}")
    return json.loads(match.group())


def _build_extra_context_block(extra_context: Optional[str]) -> str:
    if extra_context:
        return f"\nADDITIONAL CONTEXT PROVIDED BY CALLER:\n{extra_context}"
    return ""


# ---------------------------------------------------------------------------
# SummarizationService
# ---------------------------------------------------------------------------

class SummarizationService:
    """Handles end-to-end summarization of financial news articles."""

    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENROUTER_API_KEY is not set in the environment.")

        model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

        # temperature=0 for deterministic, factual output — critical for finance
        self._llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            max_tokens=1500,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        self._rag = RAGService()

        # Build LCEL chains once and reuse
        self._summarize_chain = SUMMARIZE_PROMPT | self._llm
        self._chunk_chain = CHUNK_PROMPT | self._llm
        self._aggregate_chain = AGGREGATE_PROMPT | self._llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def summarize(
        self,
        article: str,
        extra_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Summarize a financial news article.

        Returns a dict matching the SummarizeResponse schema.
        Raises ValueError for empty/invalid input.
        Raises RuntimeError for LLM or parsing failures.
        """
        article = article.strip()
        if not article:
            raise ValueError("Article text is empty after stripping whitespace.")

        # 1. Retrieve RAG context using the first 512 chars as the query
        rag_context = self._rag.retrieve_context(query=article[:512])
        rag_used = bool(rag_context)

        extra_block = _build_extra_context_block(extra_context)

        # 2. Decide: single-pass or chunked summarization
        token_count = count_tokens(article)
        if token_count <= CHUNK_MAX_TOKENS:
            structured = await self._single_pass(article, rag_context, extra_block)
        else:
            logger.info(
                f"Article has {token_count} tokens — using chunked summarization."
            )
            structured = await self._chunked_pass(article, rag_context, extra_block)

        # 3. Post-generation evaluation
        summary_text = structured.get("summary", "")
        word_count, within_limit, h_risk, h_flags = evaluate_summary(
            summary=summary_text,
            source_article=article,
        )

        return {
            "summary": summary_text,
            "key_financial_insights": structured.get("key_financial_insights", []),
            "affected_companies_sectors": structured.get("affected_companies_sectors", []),
            "investor_implications": structured.get(
                "investor_implications",
                {"direction": "neutral", "rationale": "N/A"},
            ),
            "rag_context_used": rag_used,
            "evaluation": {
                "word_count": word_count,
                "within_limit": within_limit,
                "hallucination_risk": h_risk,
                "hallucination_flags": h_flags,
            },
        }

    # ------------------------------------------------------------------
    # Internal pipeline steps
    # ------------------------------------------------------------------

    async def _single_pass(
        self, article: str, rag_context: str, extra_block: str
    ) -> Dict[str, Any]:
        """One LLM call for articles that fit within the token limit."""
        response = await self._summarize_chain.ainvoke(
            {
                "rag_context": rag_context or "No additional context available.",
                "article_text": article,
                "extra_context_block": extra_block,
            }
        )
        return self._parse_with_retry(response.content, article, rag_context, extra_block)

    async def _chunked_pass(
        self, article: str, rag_context: str, extra_block: str
    ) -> Dict[str, Any]:
        """
        Multi-step pipeline for long articles:
        1. Split article into chunks.
        2. Extract bullet points from each chunk independently.
        3. Aggregate all bullet points into the final JSON.
        """
        chunks = split_into_chunks(article)
        logger.info(f"Split article into {len(chunks)} chunk(s).")

        bullet_lists = []
        for i, chunk in enumerate(chunks):
            try:
                resp = await self._chunk_chain.ainvoke({"chunk_text": chunk})
                bullet_lists.append(f"--- Segment {i+1} ---\n{resp.content.strip()}")
            except Exception as e:
                logger.warning(f"Chunk {i+1} extraction failed: {e}. Skipping.")

        if not bullet_lists:
            raise RuntimeError("All chunk extractions failed — cannot produce a summary.")

        all_bullets = "\n\n".join(bullet_lists)

        # Aggregate
        agg_response = await self._aggregate_chain.ainvoke(
            {
                "rag_context": rag_context or "No additional context available.",
                "bullet_points": all_bullets,
                "extra_context_block": extra_block,
            }
        )
        return _extract_json(agg_response.content)

    def _parse_with_retry(
        self,
        raw: str,
        article: str,
        rag_context: str,
        extra_block: str,
    ) -> Dict[str, Any]:
        """
        Try to parse the LLM output as JSON.
        On failure, make a synchronous retry with an explicit correction prompt.
        """
        try:
            return _extract_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"JSON parse failed on first attempt: {e}. Raw output:\n{raw[:300]}")
            # Synchronous retry — append the malformed output and ask the model to fix it
            from langchain_core.messages import HumanMessage, SystemMessage
            fix_messages = [
                SystemMessage(content="You are a JSON repair assistant. Fix the JSON below so it matches the required schema exactly. Return ONLY valid JSON — no markdown."),
                HumanMessage(content=f"BROKEN JSON:\n{raw}\n\nFix it and return only valid JSON:"),
            ]
            fixed_resp = self._llm.invoke(fix_messages)
            try:
                return _extract_json(fixed_resp.content)
            except Exception as e2:
                raise RuntimeError(
                    f"LLM returned invalid JSON after retry. Last error: {e2}\nOutput: {fixed_resp.content[:500]}"
                ) from e2
