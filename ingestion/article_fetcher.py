"""Fetch readable text from an article URL.

RSS feeds often include only a short teaser. This helper follows the article
link and extracts paragraph text from the page so the LLM receives the full
story whenever the publisher allows normal HTTP access.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
import httpx


DEFAULT_HEADERS = {
    "User-Agent": "FinancialNewsAggregator/1.0 (+student project; contact configured by owner)"
}


def html_to_text(html: str) -> str:
    """Convert HTML into readable paragraph text.

    This keeps the implementation understandable: remove non-content tags,
    gather paragraph/list/table-cell text, and join longer fragments.
    """

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    candidates: list[str] = []
    for tag in soup.find_all(["p", "li", "td"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if len(text) >= 40:
            candidates.append(text)

    return "\n\n".join(candidates)


async def fetch_article_text(url: str) -> str:
    """Download an article page and return readable text.

    Some publishers block scraping or require JavaScript. In those cases this
    function returns an empty string so RSS summaries can be used as fallback.
    """

    if not url:
        return ""

    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError:
        return ""

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type.lower():
        return response.text.strip()

    return html_to_text(response.text)
