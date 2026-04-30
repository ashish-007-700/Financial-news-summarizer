"""
Pydantic models for request/response contracts.

Using strict Pydantic v2 models ensures FastAPI validates all I/O
and produces accurate OpenAPI documentation automatically.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class SummarizeRequest(BaseModel):
    article: str = Field(
        ...,
        min_length=50,
        description="Raw financial news article text. Must be at least 50 characters.",
        examples=["Federal Reserve signals potential rate cuts as inflation cools..."],
    )
    # Optional: caller can inject extra context to guide summarization
    extra_context: Optional[str] = Field(
        None,
        description="Optional extra context (e.g. sector focus) to guide the summary.",
    )


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class InvestorImplication(BaseModel):
    direction: str = Field(..., description="'bullish', 'bearish', or 'neutral'")
    rationale: str = Field(..., description="One-sentence rationale for the direction")


class EvaluationResult(BaseModel):
    word_count: int = Field(..., description="Number of words in the summary")
    within_limit: bool = Field(..., description="True if summary ≤ 100 words")
    hallucination_risk: str = Field(
        ..., description="'low', 'medium', or 'high' based on heuristic checks"
    )
    hallucination_flags: List[str] = Field(
        default_factory=list,
        description="List of phrases/entities that could not be grounded in the source",
    )


class SummarizeResponse(BaseModel):
    summary: str = Field(..., description="Concise summary (≤ 100 words)")
    key_financial_insights: List[str] = Field(
        ..., description="Bullet-point financial insights extracted from the article"
    )
    affected_companies_sectors: List[str] = Field(
        ..., description="Companies and/or market sectors mentioned or impacted"
    )
    investor_implications: InvestorImplication = Field(
        ..., description="High-level investor implication with direction and rationale"
    )
    rag_context_used: bool = Field(
        ..., description="Whether RAG context was retrieved and injected"
    )
    evaluation: EvaluationResult = Field(
        ..., description="Post-generation quality evaluation"
    )
