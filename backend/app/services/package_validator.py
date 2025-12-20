"""
Package Validator Service

Validates that npm and Python packages exist in their respective registries
before attempting deployment. This prevents deployment failures due to
non-existent or misspelled package names.
"""

import httpx
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class PackageValidator:
    """Service for validating package existence in npm and PyPI registries"""

    def __init__(self):
        # Initialize with reasonable timeout for registry checks
        # 5 seconds should be enough for registry API calls
        self.timeout = 5.0

    async def validate_npm_package(self, package: str) -> Dict[str, Any]:
        """
        Check if an npm package exists in the npm registry.

        Args:
            package: Package name (e.g., '@user/package' or 'package-name')

        Returns:
            Dict with validation result:
            {
                "valid": bool,
                "error": str | None,
                "version": str | None
            }
        """
        # Validate package name is not empty
        if not package or not package.strip():
            error_msg = "Package name cannot be empty"
            logger.warning(error_msg)
            return {
                "valid": False,
                "error": error_msg,
                "version": None
            }

        # URL encode scoped packages: @user/package → @user%2Fpackage
        # This is required for npm registry API URLs
        encoded_package = package.replace("/", "%2F")
        url = f"https://registry.npmjs.org/{encoded_package}"

        logger.info(f"Validating npm package: {package}")
        logger.debug(f"npm registry URL: {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                # Package found - extract version from dist-tags.latest
                if response.status_code == 200:
                    data = response.json()
                    version = data.get("dist-tags", {}).get("latest")

                    logger.info(f"npm package '{package}' found, version: {version}")

                    return {
                        "valid": True,
                        "error": None,
                        "version": version
                    }

                # Package not found in registry
                elif response.status_code == 404:
                    error_msg = f"Package '{package}' not found in npm registry"
                    logger.warning(error_msg)

                    return {
                        "valid": False,
                        "error": error_msg,
                        "version": None
                    }

                # Unexpected registry response
                else:
                    error_msg = f"npm registry error: HTTP {response.status_code}"
                    logger.error(f"{error_msg} for package '{package}'")

                    return {
                        "valid": False,
                        "error": error_msg,
                        "version": None
                    }

        except httpx.TimeoutException:
            # Network timeout - likely slow connection or registry issues
            error_msg = f"Timeout while validating npm package '{package}' (exceeded {self.timeout}s)"
            logger.error(error_msg)

            return {
                "valid": False,
                "error": "Package validation timed out. Please try again.",
                "version": None
            }

        except httpx.RequestError as e:
            # Network error (connection failed, DNS resolution, etc.)
            error_msg = f"Network error while validating npm package '{package}': {str(e)}"
            logger.error(error_msg)

            return {
                "valid": False,
                "error": "Failed to connect to npm registry. Check your internet connection.",
                "version": None
            }

        except Exception as e:
            # Unexpected error (malformed response, JSON parsing, etc.)
            error_msg = f"Unexpected error validating npm package '{package}': {str(e)}"
            logger.exception(error_msg)

            return {
                "valid": False,
                "error": f"Failed to validate package: {str(e)}",
                "version": None
            }

    async def validate_python_package(self, package: str) -> Dict[str, Any]:
        """
        Check if a Python package exists in the PyPI registry.

        Args:
            package: Package name (e.g., 'mcp-server-git' or 'requests')

        Returns:
            Dict with validation result:
            {
                "valid": bool,
                "error": str | None,
                "version": str | None
            }
        """
        # Validate package name is not empty
        if not package or not package.strip():
            error_msg = "Package name cannot be empty"
            logger.warning(error_msg)
            return {
                "valid": False,
                "error": error_msg,
                "version": None
            }

        # PyPI JSON API endpoint
        url = f"https://pypi.org/pypi/{package}/json"

        logger.info(f"Validating Python package: {package}")
        logger.debug(f"PyPI API URL: {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                # Package found - extract version from info.version
                if response.status_code == 200:
                    data = response.json()
                    version = data.get("info", {}).get("version")

                    logger.info(f"Python package '{package}' found, version: {version}")

                    return {
                        "valid": True,
                        "error": None,
                        "version": version
                    }

                # Package not found in registry
                elif response.status_code == 404:
                    error_msg = f"Package '{package}' not found in PyPI registry"
                    logger.warning(error_msg)

                    return {
                        "valid": False,
                        "error": error_msg,
                        "version": None
                    }

                # Unexpected registry response
                else:
                    error_msg = f"PyPI registry error: HTTP {response.status_code}"
                    logger.error(f"{error_msg} for package '{package}'")

                    return {
                        "valid": False,
                        "error": error_msg,
                        "version": None
                    }

        except httpx.TimeoutException:
            # Network timeout - likely slow connection or registry issues
            error_msg = f"Timeout while validating Python package '{package}' (exceeded {self.timeout}s)"
            logger.error(error_msg)

            return {
                "valid": False,
                "error": "Package validation timed out. Please try again.",
                "version": None
            }

        except httpx.RequestError as e:
            # Network error (connection failed, DNS resolution, etc.)
            error_msg = f"Network error while validating Python package '{package}': {str(e)}"
            logger.error(error_msg)

            return {
                "valid": False,
                "error": "Failed to connect to PyPI registry. Check your internet connection.",
                "version": None
            }

        except Exception as e:
            # Unexpected error (malformed response, JSON parsing, etc.)
            error_msg = f"Unexpected error validating Python package '{package}': {str(e)}"
            logger.exception(error_msg)

            return {
                "valid": False,
                "error": f"Failed to validate package: {str(e)}",
                "version": None
            }
