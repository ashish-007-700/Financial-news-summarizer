# Project Walkthrough

This file explains every source file in the rebuilt project. Read it beside the
code when you want to understand how the system fits together.

## Root Files

- `.env.example`: Safe template showing every environment variable the project
  expects. Copy it to `.env` and fill in real values.
- `requirements.txt`: Python packages needed by the API, scheduler, providers,
  database layer, embeddings, and dashboards.
- `README.md`: Setup and run instructions.
- `PROJECT_WALKTHROUGH.md`: This learning guide.
- `setup_check.py`: A small diagnostic script that checks environment variables,
  Redis, and PostgreSQL/pgvector readiness.

## `ingestion/`

- `__init__.py`: Marks the folder as a Python package.
- `feed_configs.py`: Stores RSS feed URLs, polling intervals, source category,
  and credibility scores. It is data-only so feed settings are easy to change.
- `rss_poller.py`: Downloads RSS XML, parses entries with `feedparser`, and
  normalizes each item into a dictionary.
- `article_fetcher.py`: Follows RSS article links and extracts readable page
  text. RSS summaries are used as fallback when a publisher blocks fetching.
- `sec_edgar.py`: Fetches SEC filing metadata from EDGAR JSON APIs using the
  required `SEC_EDGAR_USER_AGENT`, then attempts to download primary filing text.

## `providers/`

- `__init__.py`: Marks provider code as a package.
- `exceptions.py`: Defines provider fallback exceptions.
- `groq_client.py`: Wraps Groq's SDK behind a shared `generate()` function.
- `nvidia_client.py`: Wraps NVIDIA NIM using the OpenAI-compatible client.
- `gemini_client.py`: Wraps Google Gemini / AI Studio.
- `router.py`: Holds all model names and fallback order. Other folders call
  `call_llm_with_fallback()` and never import provider SDKs directly.

## `prompts/`

- `__init__.py`: Marks prompt templates as a package.
- `system.py`: Shared non-negotiable LLM rules used by every call.
- `classify.py`: Prompt for cheap article classification.
- `summarize.py`: Universal summary prompt plus article-type hints.
- `aggregate.py`: Long-document prompts for chunk extraction and final merge.
- `repair.py`: JSON repair prompt used when model output is malformed.
- `single_article.py`: Builds the same summary prompt for pasted user text.

## `processing/`

- `__init__.py`: Marks processing code as a package.
- `deduplicator.py`: MD5-hashes article URLs and checks Redis before any LLM
  call, saving cost and avoiding repeated stories.
- `classifier.py`: Uses the cheap model tier to classify type and complexity.
- `chunker.py`: Splits long/high-complexity documents using LangChain.
- `pipeline.py`: The main conductor. It performs classification, RAG lookup,
  summarization, repair, hallucination evaluation, embedding, and storage.

## `evaluator/`

- `__init__.py`: Marks evaluator code as a package.
- `hallucination.py`: Extracts numbers, percentages, tickers, and company names
  from the model output and checks whether they appear in the source article.

## `storage/`

- `__init__.py`: Marks storage code as a package.
- `redis_client.py`: Creates Redis clients and shares the Redis URL with Celery.
- `postgres.py`: Creates and writes to the single `summaries` table.
- `pgvector_client.py`: Generates local embeddings and searches related
  historical summaries using pgvector inside PostgreSQL.

## `scheduler/`

- `__init__.py`: Marks scheduler code as a package.
- `worker.py`: Configures Celery tasks and Celery Beat schedules for RSS and
  SEC EDGAR polling.

## `api/`

- `__init__.py`: Marks API code as a package.
- `schemas.py`: Pydantic request/response models. This is the shared contract
  for feed mode and single-article mode.
- `main.py`: FastAPI app exposing `/api/feed`, `/api/summarize`, and `/health`.

## `dashboard/`

- `__init__.py`: Marks dashboard code as a package.
- `feed.py`: Streamlit live feed UI that reads from `/api/feed`.
- `single.py`: Streamlit pasted-article UI that posts to `/api/summarize`.

## `tests/`

- `test_article_fetcher.py`: Verifies HTML extraction keeps article text and
  removes scripts.
- `test_evaluator.py`: Verifies supported claims are low risk and invented
  numbers/percentages are flagged.
- `test_router.py`: Verifies provider fallback and the temperature guard.
- `test_pipeline_helpers.py`: Verifies JSON extraction and schema normalization.
