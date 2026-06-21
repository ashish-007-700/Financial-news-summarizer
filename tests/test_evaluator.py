from evaluator.hallucination import evaluate_hallucination


def test_evaluator_marks_supported_numbers_low_risk():
    article = "Acme Corp reported revenue of $5.2 billion and shares rose 4%."
    summary = {
        "summary": "Acme Corp revenue was $5.2 billion and shares rose 4%.",
        "companies": [{"name": "Acme Corp", "ticker": None}],
        "metrics": [{"name": "revenue", "value": "$5.2 billion", "period": None}],
    }

    result = evaluate_hallucination(summary, article)

    assert result["hallucination_risk"] == "low"
    assert result["unsupported_claims"] == []


def test_evaluator_flags_unsupported_financial_claims():
    article = "Acme Corp reported revenue growth."
    summary = {"summary": "Acme Corp reported $9 billion in revenue and shares rose 12%."}

    result = evaluate_hallucination(summary, article)

    assert result["hallucination_risk"] in {"medium", "high"}
    assert "$9 billion" in result["unsupported_claims"]
    assert "12%" in result["unsupported_claims"]

