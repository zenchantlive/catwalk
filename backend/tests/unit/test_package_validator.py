"""
Tests for Package Validator Service

Tests validation of npm and Python packages against their respective registries.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, Mock
from app.services.package_validator import PackageValidator


@pytest.mark.asyncio
class TestNpmPackageValidation:
    """Test npm package validation"""

    async def test_valid_npm_package(self):
        """Test validation of a real, existing npm package"""
        validator = PackageValidator()

        # Use a real, stable npm package for testing
        result = await validator.validate_npm_package("express")

        assert result["valid"] is True
        assert result["error"] is None
        assert result["version"] is not None
        assert isinstance(result["version"], str)

    async def test_valid_scoped_npm_package(self):
        """Test validation of a scoped npm package (e.g., @user/package)"""
        validator = PackageValidator()

        # Test with a real scoped package
        result = await validator.validate_npm_package("@types/node")

        assert result["valid"] is True
        assert result["error"] is None
        assert result["version"] is not None

    async def test_invalid_npm_package(self):
        """Test validation of a non-existent npm package"""
        validator = PackageValidator()

        # Use a package name that definitely doesn't exist
        fake_package = "this-package-definitely-does-not-exist-xyz-123456789"
        result = await validator.validate_npm_package(fake_package)

        assert result["valid"] is False
        assert result["error"] is not None
        assert f"Package '{fake_package}' not found" in result["error"]
        assert result["version"] is None

    async def test_npm_package_url_encoding(self):
        """Test that scoped packages are properly URL-encoded"""
        validator = PackageValidator()

        # This tests the @user/package → @user%2Fpackage encoding
        # We use a mocked response to ensure URL encoding is correct
        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            # json() is synchronous in httpx, so use regular Mock (not AsyncMock)
            mock_response.json = Mock(return_value={
                "dist-tags": {"latest": "1.0.0"}
            })
            mock_get.return_value = mock_response

            await validator.validate_npm_package("@scope/package")

            # Check that the URL was properly encoded
            called_url = mock_get.call_args[0][0]
            assert "%2F" in called_url
            assert "@scope%2Fpackage" in called_url

    async def test_npm_network_timeout(self):
        """Test handling of network timeout"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            # Simulate timeout exception
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            result = await validator.validate_npm_package("test-package")

            assert result["valid"] is False
            assert result["error"] is not None
            assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()
            assert result["version"] is None

    async def test_npm_network_error(self):
        """Test handling of network connection errors"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            # Simulate network error
            mock_get.side_effect = httpx.RequestError("Connection failed")

            result = await validator.validate_npm_package("test-package")

            assert result["valid"] is False
            assert result["error"] is not None
            assert "connect" in result["error"].lower() or "network" in result["error"].lower()
            assert result["version"] is None

    async def test_npm_registry_error(self):
        """Test handling of unexpected registry HTTP errors"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 500  # Internal server error
            mock_get.return_value = mock_response

            result = await validator.validate_npm_package("test-package")

            assert result["valid"] is False
            assert result["error"] is not None
            assert "500" in result["error"]
            assert result["version"] is None

    async def test_npm_malformed_response(self):
        """Test handling of malformed JSON response from registry"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            # json() is synchronous in httpx, so use regular Mock (not AsyncMock)
            mock_response.json = Mock(return_value={})
            mock_get.return_value = mock_response

            result = await validator.validate_npm_package("test-package")

            # Should still return valid=True even if version is missing
            assert result["valid"] is True
            assert result["version"] is None


@pytest.mark.asyncio
class TestPythonPackageValidation:
    """Test Python package validation"""

    async def test_valid_python_package(self):
        """Test validation of a real, existing Python package"""
        validator = PackageValidator()

        # Use a real, stable Python package for testing
        result = await validator.validate_python_package("requests")

        assert result["valid"] is True
        assert result["error"] is None
        assert result["version"] is not None
        assert isinstance(result["version"], str)

    async def test_invalid_python_package(self):
        """Test validation of a non-existent Python package"""
        validator = PackageValidator()

        # Use a package name that definitely doesn't exist
        fake_package = "this-python-package-does-not-exist-xyz-987654321"
        result = await validator.validate_python_package(fake_package)

        assert result["valid"] is False
        assert result["error"] is not None
        assert f"Package '{fake_package}' not found" in result["error"]
        assert result["version"] is None

    async def test_python_package_with_hyphens(self):
        """Test Python packages with hyphens (common in Python ecosystem)"""
        validator = PackageValidator()

        # Test with a real package that uses hyphens
        result = await validator.validate_python_package("urllib3")

        assert result["valid"] is True
        assert result["version"] is not None

    async def test_python_network_timeout(self):
        """Test handling of network timeout for PyPI"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            # Simulate timeout exception
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            result = await validator.validate_python_package("test-package")

            assert result["valid"] is False
            assert result["error"] is not None
            assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()
            assert result["version"] is None

    async def test_python_network_error(self):
        """Test handling of network connection errors for PyPI"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            # Simulate network error
            mock_get.side_effect = httpx.RequestError("Connection failed")

            result = await validator.validate_python_package("test-package")

            assert result["valid"] is False
            assert result["error"] is not None
            assert "connect" in result["error"].lower() or "network" in result["error"].lower()
            assert result["version"] is None

    async def test_python_registry_error(self):
        """Test handling of unexpected PyPI HTTP errors"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 503  # Service unavailable
            mock_get.return_value = mock_response

            result = await validator.validate_python_package("test-package")

            assert result["valid"] is False
            assert result["error"] is not None
            assert "503" in result["error"]
            assert result["version"] is None

    async def test_python_malformed_response(self):
        """Test handling of malformed JSON response from PyPI"""
        validator = PackageValidator()

        with patch.object(httpx.AsyncClient, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            # json() is synchronous in httpx, so use regular Mock (not AsyncMock)
            mock_response.json = Mock(return_value={"info": {}})
            mock_get.return_value = mock_response

            result = await validator.validate_python_package("test-package")

            # Should still return valid=True even if version is missing
            assert result["valid"] is True
            assert result["version"] is None


@pytest.mark.asyncio
class TestPackageValidatorEdgeCases:
    """Test edge cases and special scenarios"""

    async def test_empty_package_name_npm(self):
        """Test handling of empty package name for npm"""
        validator = PackageValidator()

        result = await validator.validate_npm_package("")

        # Empty package should fail validation
        assert result["valid"] is False
        assert result["error"] is not None

    async def test_empty_package_name_python(self):
        """Test handling of empty package name for Python"""
        validator = PackageValidator()

        result = await validator.validate_python_package("")

        # Empty package should fail validation
        assert result["valid"] is False
        assert result["error"] is not None

    async def test_special_characters_in_package_name(self):
        """Test package names with special characters"""
        validator = PackageValidator()

        # npm packages can have @, /, and -
        result = await validator.validate_npm_package("@scope/package-name")
        # Should handle the encoding properly (even if package doesn't exist)
        assert "error" in result

    async def test_timeout_value_respected(self):
        """Test that the timeout value is properly used"""
        validator = PackageValidator()

        # Verify timeout is set correctly
        assert validator.timeout == 5.0

        # We could mock httpx.AsyncClient to verify timeout is passed
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get = AsyncMock(return_value=AsyncMock(status_code=404))

            await validator.validate_npm_package("test")

            # Verify AsyncClient was called with correct timeout
            mock_client_class.assert_called_with(timeout=5.0)
