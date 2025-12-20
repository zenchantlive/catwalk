import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert

from app.models.analysis_cache import AnalysisCache

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_analysis(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached analysis result if it exists and is less than 1 week old.

        Args:
            repo_url: The normalized repository URL to check.

        Returns:
            Cached analysis data if found and valid, None otherwise.

        Note:
            This method does NOT commit the session. Transaction management
            is handled by the calling route/context manager.
        """
        try:
            stmt = select(AnalysisCache).where(AnalysisCache.repo_url == repo_url)
            result = await self.session.execute(stmt)
            cache_entry = result.scalar_one_or_none()

            if not cache_entry:
                logger.debug(f"Cache miss for {repo_url}")
                return None

            # Check if cache is older than 1 week
            one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

            if cache_entry.updated_at < one_week_ago:
                logger.info(f"Cache expired for {repo_url} (age: {datetime.now(timezone.utc) - cache_entry.updated_at})")
                return None

            logger.info(f"Cache hit for {repo_url} (age: {datetime.now(timezone.utc) - cache_entry.updated_at})")
            return cache_entry.data

        except Exception as e:
            logger.error(f"Error retrieving cache for {repo_url}: {e}", exc_info=True)
            # Do NOT rollback here - let the caller handle transaction state
            return None

    async def set_analysis(self, repo_url: str, data: Dict[str, Any]) -> None:
        """
        Save or update the analysis result in the cache.

        Args:
            repo_url: The normalized repository URL to cache.
            data: The analysis data to store.

        Note:
            This method does NOT commit the session. It only adds/updates the
            cache entry. The calling code (route handler) is responsible for
            committing the transaction.

        Raises:
            Exception: Re-raises any database errors for the caller to handle.
        """
        try:
            # Upsert logic: check if exists, then update or insert
            stmt = select(AnalysisCache).where(AnalysisCache.repo_url == repo_url)
            result = await self.session.execute(stmt)
            cache_entry = result.scalar_one_or_none()

            if cache_entry:
                # Update existing cache entry
                cache_entry.data = data
                cache_entry.updated_at = func.now()
                logger.info(f"Updated cache for {repo_url}")
            else:
                # Insert new cache entry
                cache_entry = AnalysisCache(repo_url=repo_url, data=data)
                self.session.add(cache_entry)
                logger.info(f"Created new cache entry for {repo_url}")

            # Flush to ensure the write is staged, but don't commit
            # The route handler will commit when the entire request succeeds
            await self.session.flush()

        except Exception as e:
            logger.error(f"Error setting cache for {repo_url}: {e}", exc_info=True)
            # Do NOT rollback here - let the caller decide transaction fate
            raise
