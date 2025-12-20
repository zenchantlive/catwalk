"""
URL normalization utilities for consistent cache keys.

This module provides functions to normalize GitHub repository URLs to ensure
consistent cache key generation regardless of URL variations (trailing slashes,
case differences, etc.).
"""
from urllib.parse import urlparse, urlunparse


def normalize_github_url(url: str) -> str:
    """
    Normalize a GitHub repository URL to a consistent format.

    This ensures that the following URLs are treated as identical:
    - https://github.com/user/repo
    - https://github.com/user/repo/
    - https://GitHub.com/user/repo
    - HTTPS://GITHUB.COM/USER/REPO

    Args:
        url: The GitHub repository URL to normalize.

    Returns:
        A normalized URL in lowercase with no trailing slash.

    Examples:
        >>> normalize_github_url("https://GitHub.com/User/Repo/")
        'https://github.com/user/repo'

        >>> normalize_github_url("HTTPS://GITHUB.COM/USER/REPO")
        'https://github.com/user/repo'
    """
    # Parse the URL into components
    parsed = urlparse(url)

    # Normalize:
    # 1. Scheme to lowercase (https)
    # 2. Netloc (domain) to lowercase (github.com)
    # 3. Path to lowercase and strip trailing slash
    normalized_scheme = parsed.scheme.lower()
    normalized_netloc = parsed.netloc.lower()
    normalized_path = parsed.path.lower().rstrip("/")

    # Reconstruct the URL without query params or fragments
    # (GitHub repo URLs shouldn't have these for caching purposes)
    normalized = urlunparse((
        normalized_scheme,
        normalized_netloc,
        normalized_path,
        "",  # params
        "",  # query
        ""   # fragment
    ))

    return normalized
