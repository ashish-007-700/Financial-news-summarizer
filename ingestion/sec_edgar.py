"""SEC EDGAR ingestion.

SEC EDGAR is not handled as a normal RSS feed because it exposes JSON APIs and
requires a clear User-Agent. The SEC can rate-limit or block vague clients, so
the value must include your name/email in `.env`.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ingestion.feed_configs import SEC_EDGAR_CREDIBILITY_SCORE


SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE_BASE_URL = "https://www.sec.gov/Archives/edgar/data"


def _strip_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


async def _fetch_filing_text(client: httpx.AsyncClient, cik: str, accession: str, primary_document: str) -> str:
    """Download the primary filing document text from SEC archives."""

    if not primary_document:
        return ""

    accession_no_dashes = accession.replace("-", "")
    url = f"{SEC_ARCHIVE_BASE_URL}/{int(cik)}/{accession_no_dashes}/{primary_document}"
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError:
        return ""

    content_type = response.headers.get("content-type", "")
    if "html" in content_type.lower():
        return _strip_html(response.text)
    return response.text


async def fetch_company_filings(cik: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch recent SEC filings for a company CIK.

    cik must be the 10-digit zero-padded CIK string, for example Apple is
    "0000320193". This helper returns article-like dictionaries so filings can
    enter the same processing pipeline as RSS articles.
    """

    user_agent = os.getenv("SEC_EDGAR_USER_AGENT")
    if not user_agent:
        raise RuntimeError("SEC_EDGAR_USER_AGENT is required for SEC EDGAR requests.")

    url = SEC_SUBMISSIONS_URL.format(cik=cik.zfill(10))
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": user_agent}) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])[:limit]
    accession_numbers = recent.get("accessionNumber", [])[:limit]
    filing_dates = recent.get("filingDate", [])[:limit]
    primary_documents = recent.get("primaryDocument", [])[:limit]

    articles: list[dict[str, Any]] = []
    company_name = data.get("name", "Unknown SEC registrant")

    for form, accession, filing_date, primary_document in zip(
        forms, accession_numbers, filing_dates, primary_documents
    ):
        title = f"{company_name} filed {form}"
        filing_text = await _fetch_filing_text(client, cik, accession, primary_document)
        articles.append(
            {
                "title": title,
                "url": (
                    f"{SEC_ARCHIVE_BASE_URL}/{int(cik)}/"
                    f"{accession.replace('-', '')}/{primary_document}"
                ),
                "published_at": datetime.fromisoformat(filing_date).replace(tzinfo=timezone.utc),
                "source": "SEC EDGAR",
                "source_category": "regulatory_filing",
                "credibility_score": SEC_EDGAR_CREDIBILITY_SCORE,
                "body": filing_text
                or f"{title}. Accession number: {accession}. Filing date: {filing_date}.",
            }
        )

    return articles
