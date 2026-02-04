"""OAuth configuration for TaskWarrior MCP server."""

import os
from dataclasses import dataclass

from ..logging_config import get_logger

logger = get_logger(__name__)

# Default values
DEFAULT_OAUTH_ENABLED = False
DEFAULT_ISSUER_URL = "http://localhost:8000"
DEFAULT_AUTH_CODE_LIFETIME = 600  # 10 minutes
DEFAULT_ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
DEFAULT_REFRESH_TOKEN_LIFETIME = 30 * 24 * 3600  # 30 days
DEFAULT_DYNAMIC_REGISTRATION = True
DEFAULT_REVOCATION_ENABLED = True


@dataclass
class OAuthConfig:
    """OAuth configuration settings.

    Attributes:
        enabled: Whether OAuth is enabled
        issuer_url: OAuth issuer URL (authorization server URL)
        auth_code_lifetime: Authorization code lifetime in seconds
        access_token_lifetime: Access token lifetime in seconds
        refresh_token_lifetime: Refresh token lifetime in seconds
        dynamic_registration: Whether dynamic client registration is enabled
        revocation_enabled: Whether token revocation is enabled
    """

    enabled: bool
    issuer_url: str
    auth_code_lifetime: int
    access_token_lifetime: int
    refresh_token_lifetime: int
    dynamic_registration: bool
    revocation_enabled: bool

    @classmethod
    def from_env(cls) -> "OAuthConfig":
        """Load OAuth configuration from environment variables.

        Environment variables:
            OAUTH_ENABLED: Enable OAuth (default: false)
            OAUTH_ISSUER_URL: OAuth issuer URL (default: http://localhost:8000)
            OAUTH_AUTH_CODE_LIFETIME: Auth code lifetime in seconds (default: 600)
            OAUTH_ACCESS_TOKEN_LIFETIME: Access token lifetime in seconds (default: 3600)
            OAUTH_REFRESH_TOKEN_LIFETIME: Refresh token lifetime in seconds (default: 2592000)
            OAUTH_DYNAMIC_REGISTRATION: Enable dynamic registration (default: true)
            OAUTH_REVOCATION_ENABLED: Enable token revocation (default: true)

        Returns:
            OAuthConfig instance
        """
        enabled = _parse_bool(os.environ.get("OAUTH_ENABLED", ""), DEFAULT_OAUTH_ENABLED)
        issuer_url = os.environ.get("OAUTH_ISSUER_URL", DEFAULT_ISSUER_URL)
        auth_code_lifetime = _parse_int(
            os.environ.get("OAUTH_AUTH_CODE_LIFETIME", ""),
            DEFAULT_AUTH_CODE_LIFETIME
        )
        access_token_lifetime = _parse_int(
            os.environ.get("OAUTH_ACCESS_TOKEN_LIFETIME", ""),
            DEFAULT_ACCESS_TOKEN_LIFETIME
        )
        refresh_token_lifetime = _parse_int(
            os.environ.get("OAUTH_REFRESH_TOKEN_LIFETIME", ""),
            DEFAULT_REFRESH_TOKEN_LIFETIME
        )
        dynamic_registration = _parse_bool(
            os.environ.get("OAUTH_DYNAMIC_REGISTRATION", ""),
            DEFAULT_DYNAMIC_REGISTRATION
        )
        revocation_enabled = _parse_bool(
            os.environ.get("OAUTH_REVOCATION_ENABLED", ""),
            DEFAULT_REVOCATION_ENABLED
        )

        config = cls(
            enabled=enabled,
            issuer_url=issuer_url,
            auth_code_lifetime=auth_code_lifetime,
            access_token_lifetime=access_token_lifetime,
            refresh_token_lifetime=refresh_token_lifetime,
            dynamic_registration=dynamic_registration,
            revocation_enabled=revocation_enabled,
        )

        logger.debug(f"Loaded OAuth config: enabled={enabled}, issuer_url={issuer_url}")

        return config

    def validate(self) -> None:
        """Validate OAuth configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.enabled:
            logger.debug("OAuth is disabled, skipping validation")
            return

        # Validate issuer URL
        if not self.issuer_url:
            raise ValueError("OAUTH_ISSUER_URL is required when OAuth is enabled")

        # Warn if using non-HTTPS for non-localhost issuer URL
        if not self.issuer_url.startswith("https://"):
            if not _is_localhost_url(self.issuer_url):
                logger.warning(
                    "OAUTH_ISSUER_URL is not HTTPS. This is insecure for production use. "
                    f"Current value: {self.issuer_url}"
                )

        # Validate lifetimes are positive
        if self.auth_code_lifetime <= 0:
            raise ValueError("OAUTH_AUTH_CODE_LIFETIME must be positive")
        if self.access_token_lifetime <= 0:
            raise ValueError("OAUTH_ACCESS_TOKEN_LIFETIME must be positive")
        if self.refresh_token_lifetime <= 0:
            raise ValueError("OAUTH_REFRESH_TOKEN_LIFETIME must be positive")

        # Warn if auth code lifetime is longer than access token lifetime
        if self.auth_code_lifetime > self.access_token_lifetime:
            logger.warning(
                "OAUTH_AUTH_CODE_LIFETIME is longer than OAUTH_ACCESS_TOKEN_LIFETIME. "
                "This is unusual and may indicate a configuration error."
            )

        logger.info("OAuth configuration validated successfully")

    @property
    def is_https(self) -> bool:
        """Check if issuer URL uses HTTPS.

        Returns:
            True if issuer URL starts with https://
        """
        return self.issuer_url.startswith("https://")

    @property
    def is_localhost(self) -> bool:
        """Check if issuer URL is localhost.

        Returns:
            True if issuer URL is localhost
        """
        return _is_localhost_url(self.issuer_url)


def _parse_bool(value: str, default: bool) -> bool:
    """Parse a boolean from a string value.

    Args:
        value: String value to parse
        default: Default value if parsing fails

    Returns:
        Parsed boolean value
    """
    if not value:
        return default

    value_lower = value.lower().strip()
    if value_lower in ("true", "1", "yes", "on"):
        return True
    if value_lower in ("false", "0", "no", "off"):
        return False

    logger.warning(f"Invalid boolean value: {value!r}, using default: {default}")
    return default


def _parse_int(value: str, default: int) -> int:
    """Parse an integer from a string value.

    Args:
        value: String value to parse
        default: Default value if parsing fails

    Returns:
        Parsed integer value
    """
    if not value:
        return default

    try:
        return int(value.strip())
    except ValueError:
        logger.warning(f"Invalid integer value: {value!r}, using default: {default}")
        return default


def _is_localhost_url(url: str) -> bool:
    """Check if URL is a localhost URL.

    Args:
        url: URL to check

    Returns:
        True if URL points to localhost
    """
    url_lower = url.lower()
    localhost_patterns = [
        "://localhost",
        "://127.0.0.1",
        "://[::1]",
    ]
    return any(pattern in url_lower for pattern in localhost_patterns)
