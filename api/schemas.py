"""Pydantic request and response models.

These models are the public contract for the API. The dashboard and any future
client can rely on this shape staying consistent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SingleArticleRequest(BaseModel):
    """Input body for POST /api/summarize."""

    article_text: str = Field(
        ...,
        min_length=200,
        description="Raw financial article text pasted by the user.",
    )


class Company(BaseModel):
    name: str
    ticker: str | None = None


class Metric(BaseModel):
    name: str
    value: str
    period: str | None = None


class FinancialSummary(BaseModel):
    """Shared response schema for feed items and single-article summaries."""

    id: int | None = None
    title: str
    url: str | None = None
    source: str
    article_type: str
    summary: str
    key_insights: list[str]
    companies: list[Company] | list[dict[str, Any]]
    metrics: list[Metric] | list[dict[str, Any]]
    sentiment: str
    investor_implication: str
    source_credibility: float
    hallucination_risk: str
    unsupported_claims: list[str] = []
    created_at: datetime | None = None


class FeedResponse(BaseModel):
    items: list[FinancialSummary]

