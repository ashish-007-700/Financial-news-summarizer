"""
Main FastAPI application entry point.

Registers all routes and configures middleware.
On startup, seeds the ChromaDB vector store with sample financial documents
so that RAG context is available immediately.
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before any other imports that read env vars
load_dotenv()

from app.routes import summarize
from app.services.rag_service import RAGService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seed RAG store once at startup; clean up on shutdown if needed."""
    rag = RAGService()
    rag.seed_sample_documents()
    yield


app = FastAPI(
    title="Financial News Summarizer",
    description=(
        "Production-grade API that takes raw financial news articles and returns "
        "structured JSON summaries with key insights, affected companies, "
        "investor implications, and hallucination-detection scores."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins in development; lock down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summarize.router, prefix="/api/v1", tags=["Summarization"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "financial-news-summarizer"}
