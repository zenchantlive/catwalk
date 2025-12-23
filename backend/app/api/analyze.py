from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.services.analysis import AnalysisService # type: ignore
from app.services.cache import CacheService # type: ignore
from app.utils.url_helpers import normalize_github_url
from app.models.user import User
from app.core.auth import get_current_user
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
    force: bool = False  # If True, bypass cache and force re-analysis

class AnalyzeResponse(BaseModel):
    status: str
    data: dict | None = None
    error: str | None = None

@router.post("", response_model=AnalyzeResponse)
async def analyze_repository(
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    cache_service: CacheService = Depends(get_cache_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger analysis of a GitHub repository.

    This endpoint checks the cache first, then performs analysis if needed.
    Results are cached for 1 week to avoid redundant API calls.

    Requires authentication - uses user's OpenRouter API key.
    """
    # DEBUG: Log incoming request
    logger.debug(f"[ANALYZE] Received request from user {current_user.id}")
    logger.debug(f"[ANALYZE] Request data: repo_url={request.repo_url}, force={request.force}")

    # CRITICAL: Normalize the URL to ensure consistent cache keys
    # This prevents cache misses due to trailing slashes, case differences, etc.
    raw_url = request.repo_url
    normalized_url = normalize_github_url(raw_url)

    logger.debug(f"Analyzing repository: {raw_url} for user {current_user.id}")
    if raw_url != normalized_url:
        logger.debug(f"  Normalized to: {normalized_url}")

    # Check cache first (using normalized URL), unless force=True
    cached_result = None
    if not request.force:
        cached_result = await cache_service.get_analysis(normalized_url)
        if cached_result:
            logger.info(f"Cache hit for {normalized_url}")
            return AnalyzeResponse(status="cached", data=cached_result)
    else:
        logger.info(f"Force re-analysis requested for {normalized_url}, bypassing cache")

    # Cache miss - perform analysis (with user's API key)
    logger.info(f"Cache miss for {normalized_url}, performing analysis...")
    
    try:
        try:
            result = await analysis_service.analyze_repo(
                repo_url=raw_url,
                user_id=current_user.id,
                db=db
            )
        except Exception as e:
            logger.error(f"Unexpected analysis error for {raw_url}: {e}")
            return AnalyzeResponse(status="failed", error="Internal analysis error")
    except ValueError as e:
        # User doesn't have OpenRouter key
        logger.error(f"Analysis failed for {raw_url}: {str(e)}")
        return AnalyzeResponse(status="failed", error=str(e))

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


@router.delete("/cache")
async def clear_analysis_cache(
    repo_url: str = Query(..., description="The GitHub repository URL to clear from cache"),
    current_user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear the cached analysis for a specific repository URL.
    
    NOTE: The cache is global and keyed by normalized repository URL.
    This action affects all users who might analyze this repository.
    
    This is useful when you want to force a fresh analysis without
    waiting for the cache to expire (1 week).
    """
    normalized_url = normalize_github_url(repo_url)
    logger.info(f"Clearing cache for {normalized_url} (requested by user {current_user.id})")
    
    try:
        # Delete from cache
        from app.models.analysis_cache import AnalysisCache
        from sqlalchemy import delete
        
        stmt = delete(AnalysisCache).where(AnalysisCache.repo_url == normalized_url)
        result = await db.execute(stmt)
        await db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Successfully cleared cache for {normalized_url}")
            return {"status": "success", "message": f"Cache cleared for {normalized_url}"}
        else:
            logger.info(f"No cache entry found for {normalized_url}")
            return {"status": "success", "message": f"No cache entry found for {normalized_url}"}
    
    except Exception as e:
        logger.error(f"Error clearing cache for {normalized_url}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to clear cache due to an internal error")
