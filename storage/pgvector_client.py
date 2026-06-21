"""pgvector-backed retrieval helper.

Embeddings are generated locally with sentence-transformers, then stored in the
same PostgreSQL table as the summary. No Chroma, Pinecone, or second vector DB.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from storage.postgres import get_connection


@lru_cache(maxsize=1)
def _embedding_model() -> SentenceTransformer:
    """Load the local embedding model once per process."""

    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """Convert text into a 384-dimensional vector."""

    vector = _embedding_model().encode(text, normalize_embeddings=True)
    return [float(value) for value in vector]


def find_related_context(article_text: str, limit: int = 3) -> str:
    """Find similar historical summaries for RAG context."""

    query_vector = "[" + ",".join(str(value) for value in embed_text(article_text[:4000])) + "]"
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT title, summary
                FROM summaries
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vector, limit),
            ).fetchall()
    except Exception:
        # First-run friendliness: RAG should not prevent summarization if the
        # database is empty, unavailable, or still being set up.
        return ""

    if not rows:
        return ""
    return "\n\n".join(f"[Related] {row['title']}: {row['summary']}" for row in rows)
