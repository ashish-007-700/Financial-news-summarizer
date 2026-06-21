"""Universal summarization prompt for normal-length articles."""

TYPE_HINTS = {
    "earnings": "Focus on revenue, EPS, guidance, margins, and management outlook.",
    "market_move": "Focus on the catalyst, affected securities, price moves, and investor reaction.",
    "regulatory_filing": "Focus on filing type, disclosed risks, material changes, and dates.",
    "m_and_a": "Focus on buyer, target, deal value, financing, approval risks, and expected timing.",
    "macro": "Focus on economic data, policy implications, rates, inflation, and sector impact.",
    "press_release": "Extract facts but flag promotional or self-reported claims cautiously.",
    "other": "Extract only clearly stated financial facts and avoid speculation.",
}


SUMMARY_PROMPT = """
Use the article, source metadata, and optional RAG context to produce the shared
FinancialSummary JSON schema.

Article type hint:
{type_hint}

Source metadata:
- title: {title}
- url: {url}
- source: {source}
- credibility_score: {credibility_score}

Related historical context:
{rag_context}

Article text:
{article_text}

Return this exact JSON shape:
{
  "title": "string",
  "url": "string or null",
  "source": "string",
  "article_type": "string",
  "summary": "under 120 words",
  "key_insights": ["fact 1", "fact 2"],
  "companies": [{"name": "Company Name", "ticker": "TICKER or null"}],
  "metrics": [{"name": "metric name", "value": "verbatim value", "period": "period or null"}],
  "sentiment": "bullish|bearish|neutral|mixed",
  "investor_implication": "one practical sentence",
  "source_credibility": 0.0
}
"""

