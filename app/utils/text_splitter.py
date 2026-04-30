"""
Token counting and text chunking utilities.

We use tiktoken (OpenAI's tokenizer) to count tokens accurately so we never
exceed context limits. Chunking is done at paragraph boundaries first (to
preserve semantic coherence), then at sentence boundaries if a single
paragraph is still too large.
"""

import os
import re
from typing import List

import tiktoken

# Default model for token counting — cl100k_base covers gpt-4 / gpt-4o
_ENCODING_NAME = "cl100k_base"
_encoder = tiktoken.get_encoding(_ENCODING_NAME)

# Maximum tokens per chunk (loaded from env; default 3000 leaves buffer for
# system prompt + response within the model's context window)
CHUNK_MAX_TOKENS: int = int(os.getenv("CHUNK_MAX_TOKENS", 3000))


def count_tokens(text: str) -> int:
    """Return the number of tokens in *text* using the cl100k_base encoder."""
    return len(_encoder.encode(text))


def split_into_chunks(text: str, max_tokens: int = CHUNK_MAX_TOKENS) -> List[str]:
    """
    Split *text* into chunks that each fit within *max_tokens*.

    Strategy:
    1. Split on blank lines (paragraph boundaries).
    2. If a paragraph exceeds max_tokens, fall back to sentence splitting.
    3. Greedily pack paragraphs/sentences into chunks without exceeding the limit.

    Returns a list of chunk strings. If the entire text fits in one chunk,
    returns a single-element list.
    """
    if count_tokens(text) <= max_tokens:
        return [text]

    # Step 1: split on blank lines
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # Step 2: further split any paragraph that is itself too long
    segments: List[str] = []
    for para in paragraphs:
        if count_tokens(para) <= max_tokens:
            segments.append(para)
        else:
            # Sentence-level split as fallback
            sentences = re.split(r"(?<=[.!?])\s+", para)
            segments.extend(sentences)

    # Step 3: greedy packing
    chunks: List[str] = []
    current_parts: List[str] = []
    current_tokens = 0

    for seg in segments:
        seg_tokens = count_tokens(seg)
        if current_tokens + seg_tokens > max_tokens and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = [seg]
            current_tokens = seg_tokens
        else:
            current_parts.append(seg)
            current_tokens += seg_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks
