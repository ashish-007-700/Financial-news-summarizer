"""
Example client script demonstrating how to call the Financial News Summarizer API.

Usage:
    python example_request.py

Make sure the API server is running:
    uvicorn main:app --reload
"""

import json
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# ---------------------------------------------------------------------------
# Example 1: Short article — single-pass summarization
# ---------------------------------------------------------------------------

EXAMPLE_ARTICLE_SHORT = """
Federal Reserve Chair Jerome Powell signaled Wednesday that the central bank is 
likely to hold interest rates steady in the near term, citing persistent inflation 
pressures despite slowing economic growth. The Fed funds rate currently stands at 
5.25%-5.50%, its highest level in 23 years.

Markets reacted sharply, with the S&P 500 dropping 1.2% and the Nasdaq falling 
1.8% following the announcement. Treasury yields rose, with the 10-year yield 
climbing to 4.65%.

Bank stocks — particularly JPMorgan Chase (JPM) and Goldman Sachs (GS) — bucked 
the trend, rising 0.8% and 1.1% respectively, as higher-for-longer rates boost 
net interest margins.

Economists now see a reduced probability of rate cuts before Q3 2025, with futures 
markets pricing in only one 25 basis point reduction by year-end.
"""

# ---------------------------------------------------------------------------
# Example 2: With extra context
# ---------------------------------------------------------------------------

EXAMPLE_ARTICLE_WITH_CONTEXT = """
Apple Inc. reported fiscal Q2 2025 earnings that beat Wall Street expectations on 
both revenue and earnings per share. Revenue came in at $94.8 billion, up 5% 
year-over-year, driven by record Services revenue of $26.6 billion. EPS of $1.65 
surpassed the analyst consensus of $1.61.

iPhone revenue was $46.0 billion, roughly flat versus the prior year, while Mac 
and iPad revenue surprised to the upside. CEO Tim Cook highlighted strong growth 
in emerging markets, particularly India and Southeast Asia.

The company announced a $110 billion share buyback authorization and raised its 
quarterly dividend by 4% to $0.25 per share. Apple's guidance for Q3 2025 
projects revenue growth of 4-6%, which was largely in line with expectations.

Shares rose 2.3% in after-hours trading following the report.
"""


def make_request(article: str, extra_context: str = None) -> dict:
    payload = {"article": article}
    if extra_context:
        payload["extra_context"] = extra_context

    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{BASE_URL}/summarize", json=payload)
        response.raise_for_status()
        return response.json()


def main():
    print("=" * 70)
    print("EXAMPLE 1: Federal Reserve Rate Decision")
    print("=" * 70)
    try:
        result = make_request(EXAMPLE_ARTICLE_SHORT)
        print(json.dumps(result, indent=2))
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        print("ERROR: Could not connect to the API. Is the server running?")
        print("Run: uvicorn main:app --reload")
        return

    print("\n" + "=" * 70)
    print("EXAMPLE 2: Apple Earnings — with extra context")
    print("=" * 70)
    try:
        result = make_request(
            EXAMPLE_ARTICLE_WITH_CONTEXT,
            extra_context="Focus on implications for long-term technology sector investors.",
        )
        print(json.dumps(result, indent=2))
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error {e.response.status_code}: {e.response.text}")


if __name__ == "__main__":
    main()
