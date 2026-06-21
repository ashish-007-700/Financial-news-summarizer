"""Prompt for cheap article classification."""

CLASSIFY_PROMPT = """
Classify the financial article below.

Return this exact JSON shape:
{
  "article_type": "earnings|market_move|regulatory_filing|m_and_a|macro|press_release|other",
  "complexity": "low|medium|high",
  "contains_financial_data": true,
  "reason": "one short sentence"
}

Article:
{article_text}
"""

