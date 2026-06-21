"""Long-document chunking helper."""

from __future__ import annotations

from langchain_text_splitters import TokenTextSplitter


MAX_CHARS_WITHOUT_CHUNKING = 12_000


def should_chunk(article_text: str, classification: dict) -> bool:
    """Decide whether the article should use the long-document path."""

    return classification.get("complexity") == "high" or len(article_text) > MAX_CHARS_WITHOUT_CHUNKING


def split_article(article_text: str) -> list[str]:
    """Split text into overlapping token chunks.

    Overlap helps preserve context when a sentence or financial table is split
    near a boundary.
    """

    splitter = TokenTextSplitter(chunk_size=2500, chunk_overlap=250)
    return splitter.split_text(article_text)

