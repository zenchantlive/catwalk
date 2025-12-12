from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.analysis import AnalysisService # type: ignore
from app.services.cache import CacheService # type: ignore

router = APIRouter()

# Dependency for AnalysisService
def get_analysis_service():
    return AnalysisService()

# Dependency for CacheService
def get_cache_service():
    return CacheService()

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
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Trigger analysis of a GitHub repository.
    """
    repo_url = request.repo_url
    
    # Check cache first
    cached_result = await cache_service.get_analysis(repo_url)
    if cached_result:
        return AnalyzeResponse(status="cached", data=cached_result)

    # Perform analysis
    result = await analysis_service.analyze_repo(repo_url)
    
    if "error" in result:
        return AnalyzeResponse(status="failed", error=result["error"])
        
    # Cache and return result
    await cache_service.set_analysis(repo_url, result)
    return AnalyzeResponse(status="success", data=result)
