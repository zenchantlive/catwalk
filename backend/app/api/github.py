"""
GitHub API endpoints for fetching repository information.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.github_service import get_github_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting constants
MAX_BATCH_SIZE = 50  # Maximum repositories per batch request
BATCH_DELAY_MS = 100  # Delay between individual requests in batch (milliseconds)


class GitHubStarResponse(BaseModel):
    """Response model for GitHub star count endpoint."""
    star_count: int
    formatted: str
    cached: bool
    last_updated: str
    owner: str
    repo: str


class GitHubBatchRequest(BaseModel):
    """Request model for batch GitHub operations."""
    repositories: List[str] = Field(
        ..., 
        max_length=MAX_BATCH_SIZE,
        description=f"List of GitHub URLs or owner/repo strings (max {MAX_BATCH_SIZE})"
    )


class GitHubBatchStarResponse(BaseModel):
    """Response model for batch GitHub star count endpoint."""
    results: Dict[str, Optional[GitHubStarResponse]]
    total_requested: int
    successful: int
    failed: int
    rate_limited: int = 0
    processing_time_ms: int


@router.get("/stars/{owner}/{repo}", response_model=GitHubStarResponse)
async def get_repository_stars(
    owner: str,
    repo: str
) -> GitHubStarResponse:
    """
    Get star count for a specific GitHub repository.
    
    Args:
        owner: Repository owner/organization name
        repo: Repository name
        
    Returns:
        GitHubStarResponse with star count and metadata
        
    Raises:
        HTTPException: If repository not found or API error occurs
    """
    try:
        github_service = get_github_service()
        
        # Get star count from service
        star_count = await github_service.get_repository_star_count(owner, repo)
        
        if star_count is None:
            raise HTTPException(
                status_code=404,
                detail=f"Repository {owner}/{repo} not found or inaccessible"
            )
        
        # Format the star count
        formatted_count = github_service.format_star_count(star_count)
        
        # Check if result was cached (simplified check - in real implementation
        # we'd need to track this in the service)
        # For now, we'll assume it's cached if we got a result quickly
        cached = True  # This would be determined by the service layer
        
        return GitHubStarResponse(
            star_count=star_count,
            formatted=formatted_count,
            cached=cached,
            last_updated=datetime.utcnow().isoformat(),
            owner=owner,
            repo=repo
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching stars for {owner}/{repo}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching repository information"
        )


@router.post("/stars/batch", response_model=GitHubBatchStarResponse)
async def get_batch_repository_stars(
    request: GitHubBatchRequest,
    concurrent: bool = Query(
        False, 
        description="Process repositories concurrently (faster but may hit rate limits)"
    )
) -> GitHubBatchStarResponse:
    """
    Get star counts for multiple GitHub repositories in a single request.
    
    This endpoint optimizes API usage by batching multiple requests and
    implementing rate limiting protection. It processes repositories with
    controlled delays to avoid hitting GitHub API rate limits.
    
    Args:
        request: GitHubBatchRequest containing list of repositories (max 50)
        concurrent: If True, process repositories concurrently (faster but riskier)
        
    Returns:
        GitHubBatchStarResponse with results for each repository
        
    Raises:
        HTTPException: If batch size exceeds limit or other validation errors
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate batch size
        if len(request.repositories) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size {len(request.repositories)} exceeds maximum of {MAX_BATCH_SIZE}"
            )
        
        github_service = get_github_service()
        
        if concurrent:
            # Process repositories concurrently for speed
            results = await _process_repositories_concurrent(
                request.repositories, github_service
            )
        else:
            # Process repositories sequentially with rate limiting
            results = await _process_repositories_sequential(
                request.repositories, github_service
            )
        
        # Calculate statistics
        successful = sum(1 for r in results.values() if r is not None)
        failed = len(results) - successful
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return GitHubBatchStarResponse(
            results=results,
            total_requested=len(request.repositories),
            successful=successful,
            failed=failed,
            rate_limited=0,  # Would need service-level tracking for accurate count
            processing_time_ms=processing_time_ms
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in batch star count request: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing batch request"
        )


async def _process_repositories_sequential(
    repositories: List[str], 
    github_service
) -> Dict[str, Optional[GitHubStarResponse]]:
    """
    Process repositories sequentially with rate limiting delays.
    
    Args:
        repositories: List of repository identifiers
        github_service: GitHub service instance
        
    Returns:
        Dictionary mapping repository identifiers to responses
    """
    results = {}
    
    for i, repo_identifier in enumerate(repositories):
        try:
            # Add delay between requests to avoid rate limiting
            if i > 0:
                await asyncio.sleep(BATCH_DELAY_MS / 1000.0)
            
            result = await _process_single_repository(repo_identifier, github_service)
            results[repo_identifier] = result
            
        except Exception as e:
            logger.error(f"Error processing repository {repo_identifier}: {e}")
            results[repo_identifier] = None
    
    return results


async def _process_repositories_concurrent(
    repositories: List[str], 
    github_service
) -> Dict[str, Optional[GitHubStarResponse]]:
    """
    Process repositories concurrently for faster processing.
    
    Note: This may hit rate limits more easily but is faster for cached results.
    
    Args:
        repositories: List of repository identifiers
        github_service: GitHub service instance
        
    Returns:
        Dictionary mapping repository identifiers to responses
    """
    # Create tasks for concurrent processing
    tasks = [
        _process_single_repository(repo_identifier, github_service)
        for repo_identifier in repositories
    ]
    
    # Execute all tasks concurrently
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Map results back to repository identifiers
    results = {}
    for repo_identifier, result in zip(repositories, results_list):
        if isinstance(result, Exception):
            logger.error(f"Error processing repository {repo_identifier}: {result}")
            results[repo_identifier] = None
        else:
            results[repo_identifier] = result
    
    return results


async def _process_single_repository(
    repo_identifier: str, 
    github_service
) -> Optional[GitHubStarResponse]:
    """
    Process a single repository to get its star count.
    
    Args:
        repo_identifier: Repository identifier (URL or owner/repo)
        github_service: GitHub service instance
        
    Returns:
        GitHubStarResponse if successful, None if failed
    """
    try:
        # Parse the repository identifier
        owner, repo = await _parse_repository_identifier(
            repo_identifier, github_service
        )
        
        if not owner or not repo:
            logger.warning(f"Invalid repository format: {repo_identifier}")
            return None
        
        # Get star count
        star_count = await github_service.get_repository_star_count(owner, repo)
        
        if star_count is not None:
            formatted_count = github_service.format_star_count(star_count)
            return GitHubStarResponse(
                star_count=star_count,
                formatted=formatted_count,
                cached=True,  # Service handles cache detection
                last_updated=datetime.utcnow().isoformat(),
                owner=owner,
                repo=repo
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing repository {repo_identifier}: {e}")
        return None


async def _parse_repository_identifier(
    repo_identifier: str, 
    github_service
) -> tuple[Optional[str], Optional[str]]:
    """
    Parse a repository identifier into owner and repo name.
    
    Supports formats:
    - "owner/repo"
    - "https://github.com/owner/repo"
    - Other GitHub URL formats
    
    Args:
        repo_identifier: Repository identifier string
        github_service: GitHub service instance
        
    Returns:
        Tuple of (owner, repo) or (None, None) if invalid
    """
    try:
        if "/" in repo_identifier and not repo_identifier.startswith("http"):
            # Format: "owner/repo"
            parts = repo_identifier.split("/", 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        else:
            # Assume it's a GitHub URL
            parsed = github_service.parse_github_url(repo_identifier)
            if parsed:
                return parsed
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error parsing repository identifier {repo_identifier}: {e}")
        return None, None


@router.get("/repository/{owner}/{repo}")
async def get_repository_info(
    owner: str,
    repo: str
) -> Dict:
    """
    Get comprehensive repository information from GitHub API.
    
    Args:
        owner: Repository owner/organization name
        repo: Repository name
        
    Returns:
        Dictionary with repository information including stars, description, etc.
        
    Raises:
        HTTPException: If repository not found or API error occurs
    """
    try:
        github_service = get_github_service()
        
        repo_info = await github_service.get_repository_info(owner, repo)
        
        if repo_info is None:
            raise HTTPException(
                status_code=404,
                detail=f"Repository {owner}/{repo} not found or inaccessible"
            )
        
        return repo_info
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching repository info for {owner}/{repo}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching repository information"
        )