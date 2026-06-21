# Financial News Aggregator

This project is a financial news intelligence platform. It fetches trusted
financial news, deduplicates repeated stories, classifies each article, routes
LLM calls through a free-tier fallback chain, checks summaries for hallucinated
financial facts, stores results in PostgreSQL with pgvector, and serves both a
live feed and a single-article summarizer.

## Architecture

The most important idea is:

**one schema, one pipeline, one database table, two entry points.**

Automated RSS/SEC articles and manually pasted articles enter the system from
different places, but both use the same classification, summarization,
evaluation, and storage logic.

## Folder Guide

- `ingestion/`: Fetches raw articles from RSS feeds and SEC EDGAR.
- `processing/`: Orchestrates deduplication, classification, RAG, LLM calls,
  JSON repair, hallucination evaluation, and storage.
- `prompts/`: Provider-agnostic prompt templates.
- `providers/`: The only place that imports Groq, NVIDIA, or Gemini SDKs.
- `evaluator/`: Checks whether claimed numbers, tickers, and companies appear
  in the source article.
- `storage/`: PostgreSQL, pgvector, and Redis access.
- `scheduler/`: Celery worker and Celery Beat schedule.
- `api/`: FastAPI endpoints for `/api/feed` and `/api/summarize`.
- `dashboard/`: Streamlit dashboards for feed and single-article usage.

## Manual Setup

1. Install and start PostgreSQL.
2. Create the database and enable pgvector:

```sql
CREATE DATABASE financial_news_aggregator;
\c financial_news_aggregator
CREATE EXTENSION vector;
```

3. Install and start Redis. `redis-cli ping` should return `PONG`.
4. Create free API keys for Groq, NVIDIA NIM, and Google AI Studio.
5. Copy `.env.example` to `.env` and fill in all values.
6. Create and activate a virtual environment.
7. Install dependencies:

```bash
pip install -r requirements.txt
```

8. Check your local setup:

```bash
python setup_check.py
```

If this script prints `MISSING`, that item still needs your manual setup.

## Run The API

```bash
uvicorn api.main:app --reload
```

Open `http://localhost:8000/docs` for the API docs.

## Run Background Jobs

In one terminal:

```bash
celery -A scheduler.worker.celery_app worker --loglevel=info
```

In another terminal:

```bash
celery -A scheduler.worker.celery_app beat --loglevel=info
```

## Run Dashboards

```bash
streamlit run dashboard/feed.py
```

or:

```bash
streamlit run dashboard/single.py
```

## Run Tests

The tests cover the pieces that do not require live provider calls or running
databases:

```bash
pytest
```

## Model Routing

All LLM calls go through `providers/router.py`.

- Cheap tasks: classification, chunk fact extraction, JSON repair.
- Quality tasks: full summarization and long-document aggregation.

This design lets the system survive free-tier rate limits by trying the next
provider in the configured chain.

## What You Must Do Manually

I cannot create these for you from code:

- Create real free API keys for Groq, NVIDIA NIM, and Google AI Studio.
- Put those keys into `.env`.
- Install and run PostgreSQL.
- Create the database and enable `pgvector` if your DB user cannot do it.
- Install and run Redis.
- Optionally choose real SEC company CIKs in `SEC_TRACKED_CIKS`.

Once those are done, the API, worker, scheduler, and dashboards are wired to run.
