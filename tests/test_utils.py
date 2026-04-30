"""
Unit tests for utility functions (no OpenAI calls required).

Run with:
    pytest tests/ -v
"""

import pytest
from app.utils.text_splitter import count_tokens, split_into_chunks
from app.utils.evaluator import evaluate_summary


# ---------------------------------------------------------------------------
# text_splitter tests
# ---------------------------------------------------------------------------

class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_short_string(self):
        assert count_tokens("Hello world") > 0

    def test_returns_int(self):
        result = count_tokens("The Federal Reserve raised rates.")
        assert isinstance(result, int)


class TestSplitIntoChunks:
    def test_short_text_returns_single_chunk(self):
        text = "Federal Reserve holds rates steady amid inflation concerns."
        chunks = split_into_chunks(text, max_tokens=500)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_into_multiple_chunks(self):
        # Create a text longer than 100 tokens
        long_text = ("Apple reported strong earnings this quarter. " * 30).strip()
        chunks = split_into_chunks(long_text, max_tokens=50)
        assert len(chunks) > 1

    def test_each_chunk_within_token_limit(self):
        long_text = "\n\n".join(
            [f"Paragraph {i}: The market moved significantly today due to economic data. " * 5
             for i in range(20)]
        )
        max_tokens = 200
        chunks = split_into_chunks(long_text, max_tokens=max_tokens)
        for chunk in chunks:
            assert count_tokens(chunk) <= max_tokens

    def test_content_preserved(self):
        """All words in the original should appear somewhere in the chunks."""
        text = "paragraph one.\n\nparagraph two.\n\nparagraph three."
        chunks = split_into_chunks(text, max_tokens=20)
        joined = " ".join(chunks)
        assert "paragraph one" in joined
        assert "paragraph two" in joined
        assert "paragraph three" in joined


# ---------------------------------------------------------------------------
# evaluator tests
# ---------------------------------------------------------------------------

class TestEvaluateSummary:
    SOURCE = (
        "Apple Inc reported revenue of $94.8 billion in Q2 2025, "
        "with EPS of $1.65 beating the consensus estimate of $1.61. "
        "The company announced a $110 billion share buyback. "
        "CEO Tim Cook highlighted growth in India and Southeast Asia."
    )

    def test_within_limit_true_for_short_summary(self):
        summary = "Apple beat earnings expectations with strong revenue and a large buyback."
        _, within_limit, _, _ = evaluate_summary(summary, self.SOURCE)
        assert within_limit is True

    def test_within_limit_false_for_long_summary(self):
        # Build a summary over 100 words
        long_summary = " ".join(["word"] * 110)
        _, within_limit, _, _ = evaluate_summary(long_summary, self.SOURCE)
        assert within_limit is False

    def test_word_count_accurate(self):
        summary = "Apple reported strong quarterly earnings exceeding analyst expectations."
        word_count, _, _, _ = evaluate_summary(summary, self.SOURCE)
        assert word_count == 8

    def test_low_risk_for_grounded_summary(self):
        summary = (
            "Apple reported revenue of $94.8 billion and EPS of $1.65, "
            "beating consensus. CEO Tim Cook noted growth in India."
        )
        _, _, risk, _ = evaluate_summary(summary, self.SOURCE)
        # Should be low since all figures appear in source
        assert risk in ("low", "medium")

    def test_flags_ungrounded_entity(self):
        # "Microsoft" and "Satya Nadella" are NOT in the source
        summary = "Microsoft CEO Satya Nadella announced strong earnings for Apple."
        _, _, _, flags = evaluate_summary(summary, self.SOURCE)
        # At least one flag should be raised for invented entities
        assert len(flags) >= 1

    def test_risk_levels_are_valid(self):
        summary = "Apple had great results."
        _, _, risk, _ = evaluate_summary(summary, self.SOURCE)
        assert risk in ("low", "medium", "high")


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
