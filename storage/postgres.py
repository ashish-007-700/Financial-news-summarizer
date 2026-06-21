"""PostgreSQL persistence layer.

The project uses one summaries table for both automated RSS/EDGAR articles and
single-article submissions. That is the database version of the "one schema"
principle from the brief.
"""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row


CREATE_SUMMARIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS summaries (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    source TEXT NOT NULL,
    article_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_insights JSONB NOT NULL DEFAULT '[]',
    companies JSONB NOT NULL DEFAULT '[]',
    metrics JSONB NOT NULL DEFAULT '[]',
    sentiment TEXT NOT NULL,
    investor_implication TEXT NOT NULL,
    hallucination_risk TEXT NOT NULL,
    unsupported_claims JSONB NOT NULL DEFAULT '[]',
    source_credibility DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    raw_article TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_VECTOR_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS summaries_embedding_idx
ON summaries USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
"""


def get_connection() -> psycopg.Connection:
    """Open a PostgreSQL connection using DATABASE_URL."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set.")
    return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=5)


def init_db() -> None:
    """Create the summaries table.

    The code tries to enable pgvector automatically. If your PostgreSQL user is
    not allowed to create extensions, run `CREATE EXTENSION vector;` manually as
    a database owner and then start the app again.
    """

    with get_connection() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.execute(CREATE_SUMMARIES_TABLE_SQL)
        conn.execute(CREATE_VECTOR_INDEX_SQL)
        conn.commit()


def _json(value: Any) -> str:
    """Serialize Python lists/dicts for JSONB columns."""

    return json.dumps(value or [])


def _vector_literal(embedding: list[float] | None) -> str | None:
    """Convert a Python vector into pgvector's text literal format."""

    if embedding is None:
        return None
    return "[" + ",".join(str(value) for value in embedding) + "]"


def insert_summary(summary: dict[str, Any], raw_article: str, embedding: list[float] | None = None) -> int:
    """Insert one processed summary and return its database id."""

    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO summaries (
                title, url, source, article_type, summary, key_insights,
                companies, metrics, sentiment, investor_implication,
                hallucination_risk, unsupported_claims, source_credibility,
                raw_article, embedding
            )
            VALUES (
                %(title)s, %(url)s, %(source)s, %(article_type)s, %(summary)s,
                %(key_insights)s::jsonb, %(companies)s::jsonb, %(metrics)s::jsonb,
                %(sentiment)s, %(investor_implication)s, %(hallucination_risk)s,
                %(unsupported_claims)s::jsonb, %(source_credibility)s,
                %(raw_article)s, %(embedding)s::vector
            )
            RETURNING id
            """,
            {
                **summary,
                "key_insights": _json(summary.get("key_insights")),
                "companies": _json(summary.get("companies")),
                "metrics": _json(summary.get("metrics")),
                "unsupported_claims": _json(summary.get("unsupported_claims")),
                "raw_article": raw_article,
                "embedding": _vector_literal(embedding),
            },
        ).fetchone()
        conn.commit()
        return int(row["id"])


def fetch_recent_summaries(limit: int = 25) -> list[dict[str, Any]]:
    """Return the newest summaries for the dashboard feed."""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, url, source, article_type, summary, key_insights,
                   companies, metrics, sentiment, investor_implication,
                   hallucination_risk, unsupported_claims, source_credibility,
                   created_at
            FROM summaries
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return list(rows)
