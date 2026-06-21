"""Prompt helper for user-pasted articles.

Single-article mode still returns the same schema. The only difference is that
source metadata is weaker because the user pasted text directly.
"""

from prompts.summarize import SUMMARY_PROMPT, TYPE_HINTS


def build_single_article_prompt(article_text: str, article_type: str, rag_context: str) -> str:
    """Build a normal summary prompt with generic metadata."""

    return SUMMARY_PROMPT.format(
        type_hint=TYPE_HINTS.get(article_type, TYPE_HINTS["other"]),
        title="User submitted article",
        url=None,
        source="single_article",
        credibility_score=0.50,
        rag_context=rag_context or "No related historical context found.",
        article_text=article_text,
    )

