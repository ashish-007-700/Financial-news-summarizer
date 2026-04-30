# Financial News Summarizer

A production-grade API that accepts raw financial news articles and returns structured JSON summaries enriched with key insights, affected companies/sectors, investor implications, and hallucination-risk scores. Powered by OpenRouter.

---

## Project Structure

```
financial-news-summarizer/
├── main.py                          # FastAPI app entry point
├── requirements.txt
├── .env.example                     # Copy to .env and fill in your key
├── example_request.py               # Runnable client demo
├── EXAMPLE_RESPONSE.md              # Sample request + response
│
├── app/
│   ├── models.py                    # Pydantic request/response schemas
│   │
│   ├── prompts/
│   │   └── financial_prompts.py     # All LangChain prompt templates
│   │
│   ├── routes/
│   │   └── summarize.py             # POST /api/v1/summarize endpoint
│   │
│   ├── services/
│   │   ├── summarization_service.py # Core pipeline (RAG → LLM → eval)
│   │   └── rag_service.py           # ChromaDB vector store + retrieval
│   │
│   └── utils/
│       ├── text_splitter.py         # Token counting + chunking
│       └── evaluator.py             # Hallucination heuristic + length check
│
└── tests/
    └── test_utils.py                # Unit tests (no OpenRouter key needed)
```

---

## Quick Start

### 1. Clone and set up environment

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your OpenRouter API key:

```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4o          # or anthropic/claude-3-haiku, google/gemini-pro
CHUNK_MAX_TOKENS=3000
```

### 3. Start the server

```bash
uvicorn main:app --reload
```

The API will be available at **http://localhost:8000**

### 4. Explore the interactive docs

Open **http://localhost:8000/docs** in your browser for the full Swagger UI.

---

## API Reference

### `POST /api/v1/summarize`

**Request body:**

```json
{
  "article": "Raw financial news article text (min 50 characters)",
  "extra_context": "Optional: additional guidance (e.g. 'focus on tech sector')"
}
```

**Response:**

```json
{
  "summary": "Concise summary ≤ 100 words",
  "key_financial_insights": ["Insight 1", "Insight 2"],
  "affected_companies_sectors": ["Apple Inc.", "Technology sector"],
  "investor_implications": {
    "direction": "bullish | bearish | neutral",
    "rationale": "One-sentence rationale"
  },
  "rag_context_used": true,
  "evaluation": {
    "word_count": 72,
    "within_limit": true,
    "hallucination_risk": "low | medium | high",
    "hallucination_flags": []
  }
}
```

**HTTP error codes:**

| Code | Meaning |
|------|---------|
| 400  | Empty or invalid article input |
| 422  | Request body schema validation failure |
| 429  | OpenRouter rate limit exceeded |
| 502  | OpenRouter API returned an error |
| 503  | Cannot reach OpenRouter (network issue) |
| 500  | Unexpected internal error |

### `GET /health`

Returns `{"status": "ok"}` — use for load-balancer health checks.

---

## Run the Example Client

```bash
python example_request.py
```

See `EXAMPLE_RESPONSE.md` for a full sample response.

---

## Run Tests

Tests cover text splitting and evaluation utilities and require **no OpenRouter key**.

```bash
pytest tests/ -v
```

---

## Architecture

```
POST /summarize
      │
      ▼
  Pydantic validation (models.py)
      │
      ▼
  RAGService.retrieve_context()        ← ChromaDB semantic search
      │
      ▼
  count_tokens(article)
      │
   ┌──┴──────────────┐
   │ ≤ 3000 tokens   │ > 3000 tokens
   ▼                 ▼
 Single-pass      Chunked pass
 LLM call         (chunk → bullets → aggregate)
   │                 │
   └────────┬────────┘
            ▼
     JSON extraction + retry
            │
            ▼
     evaluate_summary()        ← word count + hallucination heuristic
            │
            ▼
     SummarizeResponse (Pydantic)
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `temperature=0` for the LLM | Deterministic output is critical for financial data — reduces variance and hallucinations |
| Paragraph-then-sentence chunking | Preserves semantic coherence better than fixed-size character splits |
| Two-stage chunked pipeline (bullets → aggregate) | Avoids losing context; the aggregation step synthesizes across all segments |
| JSON retry with repair prompt | Handles edge cases where the model wraps output in markdown fences |
| Named entity + figure heuristic for hallucinations | Fast, zero-dependency check that catches the most dangerous hallucination pattern (fabricated numbers/names) |
| ChromaDB persistent client | Embeddings survive restarts; no re-seeding cost after first run |
| Local Embeddings for RAG | Cost-effective and offline default ChromaDB embeddings (all-MiniLM-L6-v2) |

---

## Extending the System

**Add your own documents to the RAG knowledge base:**

```python
from app.services.rag_service import RAGService

rag = RAGService()
rag.add_documents(
    texts=["Your financial document text here..."],
    ids=["my_doc_001"],
    metadatas=[{"topic": "your_topic"}]
)
```

**Change the model:**

Update `OPENROUTER_MODEL` in `.env`. The system supports any chat completion model available on OpenRouter.

---

## Requirements

- Python 3.10+
- OpenRouter API key
- ~200MB disk space for ChromaDB + embeddings cache
