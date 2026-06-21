"""FastAPI entry point.

Run locally with:
    uvicorn api.main:app --reload
"""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api.schemas import FeedResponse, FinancialSummary, SingleArticleRequest
from processing.pipeline import process_single_article
from storage.postgres import fetch_recent_summaries, init_db


app = FastAPI(
    title="Financial News Aggregator",
    description="Aggregates, summarizes, evaluates, and serves financial news intelligence.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    """Create tables if PostgreSQL is available."""

    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "financial-news-aggregator"}


@app.get("/api/feed", response_model=FeedResponse)
def get_feed(limit: int = 25) -> FeedResponse:
    """Return recent processed articles for the live dashboard."""

    return FeedResponse(items=fetch_recent_summaries(limit=limit))


@app.post("/api/summarize", response_model=FinancialSummary)
def summarize_single_article(request: SingleArticleRequest) -> FinancialSummary:
    """Summarize one pasted article using the same pipeline as ingestion."""

    try:
        return FinancialSummary(**process_single_article(request.article_text))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
