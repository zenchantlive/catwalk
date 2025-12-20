"""
Credential Validator Service

Validates that all required credentials are provided before deployment.
Checks that required environment variables are present and non-empty.
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class CredentialValidator:
    """Service for validating deployment credentials"""

    def validate_credentials(
        self,
        provided_credentials: Dict[str, str],
        required_env_vars: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate that all required credentials are provided and non-empty.

        Args:
            provided_credentials: Dict of credential key-value pairs
                Example: {"env_TICKTICK_TOKEN": "abc123", "env_API_KEY": "xyz"}
            required_env_vars: List of env var definitions from mcp_config
                Example: [
                    {"name": "TICKTICK_TOKEN", "required": true},
                    {"name": "API_KEY", "required": false}
                ]

        Returns:
            Dict with validation result:
            {
                "valid": bool,
                "errors": List[str]  # List of error messages for missing/invalid credentials
            }

        Note:
            - Frontend sends credentials with 'env_' prefix (e.g., 'env_TICKTICK_TOKEN')
            - MCP config defines env vars without prefix (e.g., 'TICKTICK_TOKEN')
            - This method handles the prefix stripping automatically
        """
        errors: List[str] = []

        logger.info(f"Validating credentials: {len(provided_credentials)} provided, "
                   f"{len(required_env_vars)} env vars defined")

        # Filter to only required env vars (ignore optional ones)
        required_only = [
            env_var for env_var in required_env_vars
            if env_var.get("required", False)
        ]

        logger.debug(f"Required credentials: {[v.get('name') for v in required_only]}")

        # Check each required env var
        for env_var in required_only:
            var_name = env_var.get("name")

            if not var_name:
                # Skip env vars without a name (malformed config)
                logger.warning(f"Skipping env var without name: {env_var}")
                continue

            # Check if credential is provided
            # Try both with and without 'env_' prefix to handle different formats
            sanitized_var_name = re.sub(r"[^A-Za-z0-9_]", "_", var_name)
            credential_key_with_prefix = f"env_{sanitized_var_name}"
            credential_key_without_prefix = sanitized_var_name

            credential_value = (
                provided_credentials.get(credential_key_with_prefix) or
                provided_credentials.get(credential_key_without_prefix)
            )

            # Validate credential exists and is not empty
            if credential_value is None:
                error_msg = f"Required credential '{var_name}' is missing"
                errors.append(error_msg)
                logger.warning(error_msg)

            elif isinstance(credential_value, str) and not credential_value.strip():
                # Credential exists but is empty string or whitespace
                error_msg = f"Required credential '{var_name}' is empty"
                errors.append(error_msg)
                logger.warning(error_msg)

            else:
                # Credential is valid
                logger.debug(f"Credential '{var_name}' is valid")

        # Determine overall validation result
        is_valid = len(errors) == 0

        if is_valid:
            logger.info("Credential validation passed: all required credentials provided")
        else:
            logger.warning(f"Credential validation failed: {len(errors)} error(s)")
            for error in errors:
                logger.warning(f"  - {error}")

        return {
            "valid": is_valid,
            "errors": errors
        }

    def validate_credentials_simple(
        self,
        provided_credentials: Dict[str, str],
        required_var_names: List[str]
    ) -> Dict[str, Any]:
        """
        Simplified validation when you only have a list of required variable names.

        Args:
            provided_credentials: Dict of credential key-value pairs
            required_var_names: List of required env var names (strings)
                Example: ["TICKTICK_TOKEN", "API_KEY"]

        Returns:
            Same format as validate_credentials()
        """
        # Convert simple list to the full format expected by validate_credentials
        required_env_vars = [
            {"name": var_name, "required": True}
            for var_name in required_var_names
        ]

        return self.validate_credentials(provided_credentials, required_env_vars)
