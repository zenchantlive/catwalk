from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.analysis import AnalysisService # type: ignore
from app.services.cache import CacheService # type: ignore
from app.utils.url_helpers import normalize_github_url
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Dependency for AnalysisService
def get_analysis_service():
    return AnalysisService()

# Dependency for CacheService
def get_cache_service(db: AsyncSession = Depends(get_db)):
    return CacheService(db)

class AnalyzeRequest(BaseModel):
    repo_url: str

class AnalyzeResponse(BaseModel):
    status: str
    data: dict | None = None
    error: str | None = None

@router.post("", response_model=AnalyzeResponse)
async def analyze_repository(
    request: AnalyzeRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    cache_service: CacheService = Depends(get_cache_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger analysis of a GitHub repository.

    This endpoint checks the cache first, then performs analysis if needed.
    Results are cached for 1 week to avoid redundant API calls.
    """
    # CRITICAL: Normalize the URL to ensure consistent cache keys
    # This prevents cache misses due to trailing slashes, case differences, etc.
    raw_url = request.repo_url
    normalized_url = normalize_github_url(raw_url)

    logger.info(f"Analyzing repository: {raw_url}")
    if raw_url != normalized_url:
        logger.info(f"  Normalized to: {normalized_url}")

    # Check cache first (using normalized URL)
    cached_result = await cache_service.get_analysis(normalized_url)
    if cached_result:
        logger.info(f"Cache hit for {normalized_url}")
        return AnalyzeResponse(status="cached", data=cached_result)

    # Cache miss - perform analysis
    logger.info(f"Cache miss for {normalized_url}, performing analysis...")
    result = await analysis_service.analyze_repo(raw_url)

    if "error" in result:
        logger.error(f"Analysis failed for {raw_url}: {result['error']}")
        # Don't cache errors
        return AnalyzeResponse(status="failed", error=result["error"])

    # Cache the successful result
    try:
        await cache_service.set_analysis(normalized_url, result)
        # Commit the cache write
        await db.commit()
        logger.info(f"Successfully cached analysis for {normalized_url}")
    except Exception as e:
        # If caching fails, log but don't fail the request
        logger.error(f"Failed to cache analysis for {normalized_url}: {e}", exc_info=True)
        await db.rollback()
        # Continue anyway - we have the analysis result

    return AnalyzeResponse(status="success", data=result)
