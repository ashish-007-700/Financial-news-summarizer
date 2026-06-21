"""Prompts for long documents that must be chunked first."""

CHUNK_FACT_PROMPT = """
Extract only factual financial bullets from this document chunk.
Do not summarize broadly. Do not invent missing values.

Chunk:
{chunk_text}

Return bullet points only.
"""


AGGREGATE_PROMPT = """
Combine the chunk-level facts below into the same FinancialSummary JSON schema
used for normal articles. Deduplicate repeated facts and keep only supported
claims.

Source metadata:
- title: {title}
- url: {url}
- source: {source}
- article_type: {article_type}
- credibility_score: {credibility_score}

Related historical context:
{rag_context}

Chunk facts:
{chunk_facts}

Return JSON only using the same schema as the normal summarization prompt.
"""

