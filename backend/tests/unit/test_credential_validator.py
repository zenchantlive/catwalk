"""
Tests for Credential Validator Service

Tests validation of required credentials before deployment.
"""

import pytest
from app.services.credential_validator import CredentialValidator


class TestCredentialValidation:
    """Test credential validation logic"""

    def test_all_required_credentials_provided(self):
        """Test validation when all required credentials are provided"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TICKTICK_TOKEN": "abc123",
            "env_API_KEY": "xyz789"
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True},
            {"name": "API_KEY", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_required_credential(self):
        """Test validation when a required credential is missing"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TICKTICK_TOKEN": "abc123"
            # Missing API_KEY
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True},
            {"name": "API_KEY", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "API_KEY" in result["errors"][0]
        assert "missing" in result["errors"][0].lower()

    def test_empty_string_credential(self):
        """Test validation when credential is empty string"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TICKTICK_TOKEN": "",  # Empty string
            "env_API_KEY": "   "  # Whitespace only
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True},
            {"name": "API_KEY", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is False
        assert len(result["errors"]) == 2
        # Both should be flagged as empty
        assert any("TICKTICK_TOKEN" in err for err in result["errors"])
        assert any("API_KEY" in err for err in result["errors"])

    def test_optional_credential_missing(self):
        """Test that missing optional credentials don't cause validation failure"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TICKTICK_TOKEN": "abc123"
            # Optional API_KEY is missing - should be OK
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True},
            {"name": "API_KEY", "required": False}  # Optional
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_multiple_missing_credentials(self):
        """Test that all missing credentials are listed in errors"""
        validator = CredentialValidator()

        provided_credentials = {}  # No credentials provided

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True},
            {"name": "API_KEY", "required": True},
            {"name": "DATABASE_URL", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is False
        assert len(result["errors"]) == 3
        # All three should be in the error list
        assert any("TICKTICK_TOKEN" in err for err in result["errors"])
        assert any("API_KEY" in err for err in result["errors"])
        assert any("DATABASE_URL" in err for err in result["errors"])

    def test_credential_without_env_prefix(self):
        """Test that credentials work both with and without 'env_' prefix"""
        validator = CredentialValidator()

        # Provide credential WITHOUT 'env_' prefix
        provided_credentials = {
            "TICKTICK_TOKEN": "abc123"  # No 'env_' prefix
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_mixed_prefix_and_no_prefix(self):
        """Test credentials with mixed prefix/no-prefix formats"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TICKTICK_TOKEN": "abc123",  # With prefix
            "API_KEY": "xyz789"  # Without prefix
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True},
            {"name": "API_KEY", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_env_var_without_name(self):
        """Test handling of malformed env var config (missing name)"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TICKTICK_TOKEN": "abc123"
        }

        required_env_vars = [
            {"required": True},  # Missing 'name' field
            {"name": "TICKTICK_TOKEN", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        # Should skip the malformed entry and validate the good one
        assert result["valid"] is True
        assert result["errors"] == []

    def test_empty_required_env_vars_list(self):
        """Test validation when no env vars are required"""
        validator = CredentialValidator()

        provided_credentials = {}
        required_env_vars = []

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_all_optional_credentials(self):
        """Test validation when all env vars are optional"""
        validator = CredentialValidator()

        provided_credentials = {}  # No credentials provided

        required_env_vars = [
            {"name": "OPTIONAL_VAR_1", "required": False},
            {"name": "OPTIONAL_VAR_2", "required": False}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        # Should be valid since all are optional
        assert result["valid"] is True
        assert result["errors"] == []

    def test_extra_credentials_provided(self):
        """Test that extra (not required) credentials don't cause issues"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TICKTICK_TOKEN": "abc123",
            "env_EXTRA_VAR": "extra_value",  # Not in required list
            "env_ANOTHER_EXTRA": "another_value"
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        # Extra credentials should be ignored
        assert result["valid"] is True
        assert result["errors"] == []


class TestCredentialValidationSimple:
    """Test simplified validation method"""

    def test_simple_validation_all_provided(self):
        """Test simplified validation with all credentials"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TOKEN": "abc",
            "env_KEY": "xyz"
        }

        required_var_names = ["TOKEN", "KEY"]

        result = validator.validate_credentials_simple(
            provided_credentials,
            required_var_names
        )

        assert result["valid"] is True
        assert result["errors"] == []

    def test_simple_validation_missing_credential(self):
        """Test simplified validation with missing credential"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TOKEN": "abc"
        }

        required_var_names = ["TOKEN", "KEY"]

        result = validator.validate_credentials_simple(
            provided_credentials,
            required_var_names
        )

        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "KEY" in result["errors"][0]

    def test_simple_validation_empty_list(self):
        """Test simplified validation with no required credentials"""
        validator = CredentialValidator()

        provided_credentials = {}
        required_var_names = []

        result = validator.validate_credentials_simple(
            provided_credentials,
            required_var_names
        )

        assert result["valid"] is True
        assert result["errors"] == []


class TestCredentialValidationEdgeCases:
    """Test edge cases and special scenarios"""

    def test_none_value_credential(self):
        """Test handling of None as credential value"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_TOKEN": None  # Explicit None
        }

        required_env_vars = [
            {"name": "TOKEN", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is False
        assert len(result["errors"]) == 1

    def test_numeric_credential_value(self):
        """Test that numeric credential values are accepted"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_PORT": "8080",  # Numeric but as string
            "env_TIMEOUT": "30"
        }

        required_env_vars = [
            {"name": "PORT", "required": True},
            {"name": "TIMEOUT", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_credential_with_special_characters(self):
        """Test credentials containing special characters"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_API_KEY": "sk-abc123_xyz!@#$%^&*()",
            "env_TOKEN": "Bearer eyJ..."
        }

        required_env_vars = [
            {"name": "API_KEY", "required": True},
            {"name": "TOKEN", "required": True}
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_case_sensitive_credential_names(self):
        """Test that credential names are case-sensitive"""
        validator = CredentialValidator()

        provided_credentials = {
            "env_ticktick_token": "abc123"  # Lowercase
        }

        required_env_vars = [
            {"name": "TICKTICK_TOKEN", "required": True}  # Uppercase
        ]

        result = validator.validate_credentials(provided_credentials, required_env_vars)

        # Should fail because case doesn't match
        assert result["valid"] is False
        assert any("TICKTICK_TOKEN" in err for err in result["errors"])
