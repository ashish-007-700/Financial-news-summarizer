"""
Prompt templates for the Financial News Summarizer.

All prompts live here so they can be reviewed, versioned, and tested
independently of the pipeline logic.

Design decisions:
- System prompts are static strings passed as SystemMessage objects — this
  prevents LangChain from treating the JSON schema's curly braces as
  f-string template slots and raising a ValueError.
- Only the HumanMessage templates use {variables} since they receive
  dynamic content (article text, RAG context, etc.).
- Chunked-aggregation uses a lighter "merge" prompt to avoid re-hallucinating.
"""

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

# ---------------------------------------------------------------------------
# System prompt content — static strings (no template variables)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEXT = """You are a senior financial analyst and professional news summarizer.
Your job is to analyze financial news articles and return a structured JSON response.

STRICT RULES — follow every rule or the output will be rejected:
1. Only state facts that are explicitly mentioned in the article or provided context.
2. Do NOT invent company names, ticker symbols, statistics, or dates.
3. If information for a field is absent in the article, use an empty list [] or "N/A".
4. Keep the summary under 100 words — count carefully.
5. The investor_implications.direction must be exactly one of: "bullish", "bearish", "neutral".
6. Return ONLY valid JSON with the exact schema shown below — no markdown fences, no commentary.

OUTPUT SCHEMA:
{
  "summary": "<string, max 100 words>",
  "key_financial_insights": ["<insight 1>", "<insight 2>", ...],
  "affected_companies_sectors": ["<company or sector>", ...],
  "investor_implications": {
    "direction": "<bullish|bearish|neutral>",
    "rationale": "<one sentence>"
  }
}"""

CHUNK_SYSTEM_PROMPT_TEXT = """You are a financial analyst summarizing one segment of a longer article.
Extract key points only from this specific segment.
Return a plain text bullet list — no JSON yet.
Do NOT invent information. Only use what is in this segment."""

AGGREGATE_SYSTEM_PROMPT_TEXT = """You are a senior financial analyst.
You have been given bullet-point extracts from multiple segments of a long financial article.
Your job is to synthesize them into a single structured JSON response.

Follow the same STRICT RULES as before:
1. Only use information present in the provided bullets.
2. Keep the summary under 100 words.
3. direction must be exactly "bullish", "bearish", or "neutral".
4. Return ONLY valid JSON — no markdown, no commentary.

OUTPUT SCHEMA:
{
  "summary": "<string, max 100 words>",
  "key_financial_insights": ["<insight 1>", ...],
  "affected_companies_sectors": ["<company or sector>", ...],
  "investor_implications": {
    "direction": "<bullish|bearish|neutral>",
    "rationale": "<one sentence>"
  }
}"""

# ---------------------------------------------------------------------------
# Main summarization prompt (single article or merged chunk)
# ---------------------------------------------------------------------------

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=SYSTEM_PROMPT_TEXT),
        HumanMessagePromptTemplate.from_template(
            """RELEVANT BACKGROUND CONTEXT (from knowledge base — use only if helpful):
{rag_context}

---

ARTICLE TO ANALYZE:
{article_text}

{extra_context_block}

Now return the JSON response following the schema exactly."""
        ),
    ]
)

# ---------------------------------------------------------------------------
# Chunk-level summarization prompt (used for very long articles)
# ---------------------------------------------------------------------------

CHUNK_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=CHUNK_SYSTEM_PROMPT_TEXT),
        HumanMessagePromptTemplate.from_template(
            "ARTICLE SEGMENT:\n{chunk_text}\n\nExtract key financial points as bullets:"
        ),
    ]
)

# ---------------------------------------------------------------------------
# Aggregation prompt (merges bullet points from all chunks into final JSON)
# ---------------------------------------------------------------------------

AGGREGATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=AGGREGATE_SYSTEM_PROMPT_TEXT),
        HumanMessagePromptTemplate.from_template(
            """BACKGROUND CONTEXT (from knowledge base):
{rag_context}

---

EXTRACTED BULLET POINTS FROM ALL ARTICLE SEGMENTS:
{bullet_points}

{extra_context_block}

Now synthesize and return the final JSON:"""
        ),
    ]
)
