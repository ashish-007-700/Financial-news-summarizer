from processing.pipeline import _extract_json, _normalize_summary


def test_extract_json_handles_markdown_fences():
    raw = '```json\n{"summary": "ok"}\n```'

    assert _extract_json(raw) == {"summary": "ok"}


def test_normalize_summary_fills_required_defaults():
    article = {
        "title": "Market update",
        "url": "https://example.com/article",
        "source": "Example",
        "credibility_score": 0.8,
    }
    classification = {"article_type": "macro"}

    normalized = _normalize_summary({"summary": "Stocks moved."}, article, classification)

    assert normalized["title"] == "Market update"
    assert normalized["article_type"] == "macro"
    assert normalized["source_credibility"] == 0.8
    assert normalized["key_insights"] == []
