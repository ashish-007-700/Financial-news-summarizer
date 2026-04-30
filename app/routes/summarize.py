"""
FastAPI route for POST /summarize.

All error cases are mapped to appropriate HTTP status codes:
- 400: empty input / validation error
- 422: Pydantic validation failure (handled automatically by FastAPI)
- 429: OpenRouter rate-limit
- 503: OpenRouter API unavailable
- 500: unexpected internal errors
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from openai import APIConnectionError, APIStatusError, RateLimitError

from app.models import SummarizeRequest, SummarizeResponse
from app.services.summarization_service import SummarizationService

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy singleton — initialized on first request so startup errors surface cleanly
_service: Optional[SummarizationService] = None


def get_service() -> SummarizationService:
    global _service
    if _service is None:
        _service = SummarizationService()
    return _service


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Summarize a financial news article",
    description=(
        "Accepts raw financial news article text and returns a structured JSON "
        "containing a ≤100-word summary, key insights, affected companies/sectors, "
        "investor implications, and a hallucination-risk evaluation."
    ),
)
async def summarize_article(request: SummarizeRequest):
    """
    POST /api/v1/summarize

    Body:
    - article (str, required): Raw financial news text (min 50 chars).
    - extra_context (str, optional): Additional context to guide the summary.
    """
    try:
        result = await get_service().summarize(
            article=request.article,
            extra_context=request.extra_context,
        )
        return SummarizeResponse(**result)

    except ValueError as e:
        # Empty input or validation logic failure
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except RateLimitError as e:
        logger.warning(f"OpenRouter rate limit hit: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OpenRouter rate limit reached. Please wait and retry.",
        )

    except APIConnectionError as e:
        logger.error(f"OpenRouter connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot reach the OpenRouter API. Check your network or API status.",
        )

    except APIStatusError as e:
        logger.error(f"OpenRouter API error {e.status_code}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenRouter API returned an error: {e.message}",
        )

    except RuntimeError as e:
        logger.error(f"Summarization runtime error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        logger.exception(f"Unexpected error during summarization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )
