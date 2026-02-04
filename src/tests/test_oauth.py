"""Tests for OAuth implementation."""

import os
import time
import pytest

from pydantic import AnyUrl

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull

from taskwarriormcp.oauth.config import OAuthConfig, _parse_bool, _parse_int, _is_localhost_url
from taskwarriormcp.oauth.storage import InMemoryStorage
from taskwarriormcp.oauth.provider import TaskWarriorOAuthProvider


class TestOAuthConfig:
    """Tests for OAuth configuration."""

    def test_default_values(self):
        """Test that default configuration values are used."""
        # Clear environment
        for key in ["OAUTH_ENABLED", "OAUTH_ISSUER_URL", "OAUTH_AUTH_CODE_LIFETIME",
                    "OAUTH_ACCESS_TOKEN_LIFETIME", "OAUTH_REFRESH_TOKEN_LIFETIME",
                    "OAUTH_DYNAMIC_REGISTRATION", "OAUTH_REVOCATION_ENABLED"]:
            os.environ.pop(key, None)

        config = OAuthConfig.from_env()

        assert config.enabled is False
        assert config.issuer_url == "http://localhost:8000"
        assert config.auth_code_lifetime == 600
        assert config.access_token_lifetime == 3600
        assert config.refresh_token_lifetime == 30 * 24 * 3600
        assert config.dynamic_registration is True
        assert config.revocation_enabled is True

    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        os.environ["OAUTH_ENABLED"] = "true"
        os.environ["OAUTH_ISSUER_URL"] = "https://example.com"
        os.environ["OAUTH_AUTH_CODE_LIFETIME"] = "300"
        os.environ["OAUTH_ACCESS_TOKEN_LIFETIME"] = "7200"
        os.environ["OAUTH_REFRESH_TOKEN_LIFETIME"] = "86400"
        os.environ["OAUTH_DYNAMIC_REGISTRATION"] = "false"
        os.environ["OAUTH_REVOCATION_ENABLED"] = "false"

        try:
            config = OAuthConfig.from_env()

            assert config.enabled is True
            assert config.issuer_url == "https://example.com"
            assert config.auth_code_lifetime == 300
            assert config.access_token_lifetime == 7200
            assert config.refresh_token_lifetime == 86400
            assert config.dynamic_registration is False
            assert config.revocation_enabled is False
        finally:
            # Clean up
            for key in ["OAUTH_ENABLED", "OAUTH_ISSUER_URL", "OAUTH_AUTH_CODE_LIFETIME",
                        "OAUTH_ACCESS_TOKEN_LIFETIME", "OAUTH_REFRESH_TOKEN_LIFETIME",
                        "OAUTH_DYNAMIC_REGISTRATION", "OAUTH_REVOCATION_ENABLED"]:
                os.environ.pop(key, None)

    def test_validation_disabled(self):
        """Test that validation passes when OAuth is disabled."""
        config = OAuthConfig(
            enabled=False,
            issuer_url="",  # Invalid, but should be ignored
            auth_code_lifetime=-1,  # Invalid, but should be ignored
            access_token_lifetime=0,  # Invalid, but should be ignored
            refresh_token_lifetime=0,  # Invalid, but should be ignored
            dynamic_registration=True,
            revocation_enabled=True,
        )
        # Should not raise
        config.validate()

    def test_validation_invalid_auth_code_lifetime(self):
        """Test that invalid auth code lifetime is rejected."""
        config = OAuthConfig(
            enabled=True,
            issuer_url="http://localhost:8000",
            auth_code_lifetime=0,
            access_token_lifetime=3600,
            refresh_token_lifetime=86400,
            dynamic_registration=True,
            revocation_enabled=True,
        )
        with pytest.raises(ValueError, match="AUTH_CODE_LIFETIME must be positive"):
            config.validate()

    def test_validation_invalid_access_token_lifetime(self):
        """Test that invalid access token lifetime is rejected."""
        config = OAuthConfig(
            enabled=True,
            issuer_url="http://localhost:8000",
            auth_code_lifetime=600,
            access_token_lifetime=-1,
            refresh_token_lifetime=86400,
            dynamic_registration=True,
            revocation_enabled=True,
        )
        with pytest.raises(ValueError, match="ACCESS_TOKEN_LIFETIME must be positive"):
            config.validate()

    def test_is_https(self):
        """Test HTTPS detection."""
        config = OAuthConfig(
            enabled=True,
            issuer_url="https://example.com",
            auth_code_lifetime=600,
            access_token_lifetime=3600,
            refresh_token_lifetime=86400,
            dynamic_registration=True,
            revocation_enabled=True,
        )
        assert config.is_https is True

        config.issuer_url = "http://localhost:8000"
        assert config.is_https is False

    def test_is_localhost(self):
        """Test localhost detection."""
        config = OAuthConfig(
            enabled=True,
            issuer_url="http://localhost:8000",
            auth_code_lifetime=600,
            access_token_lifetime=3600,
            refresh_token_lifetime=86400,
            dynamic_registration=True,
            revocation_enabled=True,
        )
        assert config.is_localhost is True

        config.issuer_url = "http://127.0.0.1:8000"
        assert config.is_localhost is True

        config.issuer_url = "https://example.com"
        assert config.is_localhost is False


class TestConfigHelpers:
    """Tests for configuration helper functions."""

    def test_parse_bool_true_values(self):
        """Test parsing boolean true values."""
        for value in ["true", "True", "TRUE", "1", "yes", "on"]:
            assert _parse_bool(value, False) is True

    def test_parse_bool_false_values(self):
        """Test parsing boolean false values."""
        for value in ["false", "False", "FALSE", "0", "no", "off"]:
            assert _parse_bool(value, True) is False

    def test_parse_bool_default(self):
        """Test parsing boolean with default."""
        assert _parse_bool("", True) is True
        assert _parse_bool("", False) is False
        assert _parse_bool("invalid", True) is True
        assert _parse_bool("invalid", False) is False

    def test_parse_int_valid(self):
        """Test parsing valid integers."""
        assert _parse_int("42", 0) == 42
        assert _parse_int("  100  ", 0) == 100
        assert _parse_int("-5", 0) == -5

    def test_parse_int_invalid(self):
        """Test parsing invalid integers."""
        assert _parse_int("", 99) == 99
        assert _parse_int("abc", 99) == 99
        assert _parse_int("1.5", 99) == 99

    def test_is_localhost_url(self):
        """Test localhost URL detection."""
        assert _is_localhost_url("http://localhost:8000") is True
        assert _is_localhost_url("http://127.0.0.1:8000") is True
        assert _is_localhost_url("http://[::1]:8000") is True
        assert _is_localhost_url("https://localhost:8000") is True
        assert _is_localhost_url("https://example.com") is False
        assert _is_localhost_url("http://192.168.1.1:8000") is False


class TestInMemoryStorage:
    """Tests for in-memory OAuth storage."""

    @pytest.fixture
    def storage(self):
        """Create a fresh storage instance."""
        return InMemoryStorage()

    @pytest.fixture
    def sample_client(self):
        """Create a sample client for testing."""
        return OAuthClientInformationFull(
            client_id="test-client-id",
            client_secret="test-secret",
            redirect_uris=["http://localhost:3000/callback"],
            client_name="Test Client",
        )

    @pytest.mark.asyncio
    async def test_client_operations(self, storage, sample_client):
        """Test client CRUD operations."""
        # Initially empty
        assert await storage.get_client("test-client-id") is None

        # Save client
        await storage.save_client(sample_client)

        # Retrieve client
        client = await storage.get_client("test-client-id")
        assert client is not None
        assert client.client_id == "test-client-id"
        assert client.client_name == "Test Client"

        # Delete client
        result = await storage.delete_client("test-client-id")
        assert result is True

        # Verify deleted
        assert await storage.get_client("test-client-id") is None

        # Delete non-existent
        result = await storage.delete_client("test-client-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_save_client_without_id(self, storage):
        """Test that saving a client without ID raises an error."""
        client = OAuthClientInformationFull(redirect_uris=["http://localhost:3000/callback"])
        with pytest.raises(ValueError, match="client_id"):
            await storage.save_client(client)

    @pytest.mark.asyncio
    async def test_authorization_code_operations(self, storage):
        """Test authorization code CRUD operations."""
        code = AuthorizationCode(
            code="test-code",
            scopes=["read", "write"],
            expires_at=time.time() + 600,
            client_id="test-client",
            code_challenge="challenge",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )

        # Save and retrieve
        await storage.save_authorization_code(code)
        retrieved = await storage.get_authorization_code("test-code")
        assert retrieved is not None
        assert retrieved.code == "test-code"
        assert retrieved.client_id == "test-client"

        # Delete
        result = await storage.delete_authorization_code("test-code")
        assert result is True

        # Verify deleted
        assert await storage.get_authorization_code("test-code") is None

    @pytest.mark.asyncio
    async def test_access_token_operations(self, storage):
        """Test access token CRUD operations."""
        token = AccessToken(
            token="test-access-token",
            client_id="test-client",
            scopes=["read"],
            expires_at=int(time.time() + 3600),
        )

        # Save and retrieve
        await storage.save_access_token(token)
        retrieved = await storage.get_access_token("test-access-token")
        assert retrieved is not None
        assert retrieved.token == "test-access-token"

        # Delete
        result = await storage.delete_access_token("test-access-token")
        assert result is True

        # Verify deleted
        assert await storage.get_access_token("test-access-token") is None

    @pytest.mark.asyncio
    async def test_refresh_token_operations(self, storage):
        """Test refresh token CRUD operations."""
        token = RefreshToken(
            token="test-refresh-token",
            client_id="test-client",
            scopes=["read"],
            expires_at=int(time.time() + 86400),
        )

        # Save and retrieve
        await storage.save_refresh_token(token)
        retrieved = await storage.get_refresh_token("test-refresh-token")
        assert retrieved is not None
        assert retrieved.token == "test-refresh-token"

        # Delete
        result = await storage.delete_refresh_token("test-refresh-token")
        assert result is True

        # Verify deleted
        assert await storage.get_refresh_token("test-refresh-token") is None

    @pytest.mark.asyncio
    async def test_delete_tokens_for_client(self, storage):
        """Test deleting all tokens for a specific client."""
        # Create tokens for client1
        for i in range(3):
            await storage.save_access_token(AccessToken(
                token=f"access-{i}",
                client_id="client1",
                scopes=["read"],
            ))
            await storage.save_refresh_token(RefreshToken(
                token=f"refresh-{i}",
                client_id="client1",
                scopes=["read"],
            ))

        # Create token for client2
        await storage.save_access_token(AccessToken(
            token="access-other",
            client_id="client2",
            scopes=["read"],
        ))

        # Delete tokens for client1
        access_deleted = await storage.delete_access_tokens_for_client("client1")
        refresh_deleted = await storage.delete_refresh_tokens_for_client("client1")

        assert access_deleted == 3
        assert refresh_deleted == 3

        # Verify client2's token still exists
        assert await storage.get_access_token("access-other") is not None

    def test_get_stats(self, storage):
        """Test storage statistics."""
        stats = storage.get_stats()
        assert stats["clients"] == 0
        assert stats["authorization_codes"] == 0
        assert stats["access_tokens"] == 0
        assert stats["refresh_tokens"] == 0

    @pytest.mark.asyncio
    async def test_clear(self, storage, sample_client):
        """Test clearing all storage."""
        await storage.save_client(sample_client)
        await storage.save_access_token(AccessToken(
            token="test-token",
            client_id="test-client",
            scopes=["read"],
        ))

        stats = storage.get_stats()
        assert stats["clients"] == 1
        assert stats["access_tokens"] == 1

        storage.clear()

        stats = storage.get_stats()
        assert stats["clients"] == 0
        assert stats["access_tokens"] == 0


class TestTaskWarriorOAuthProvider:
    """Tests for the OAuth provider."""

    @pytest.fixture
    def config(self):
        """Create OAuth config for testing."""
        return OAuthConfig(
            enabled=True,
            issuer_url="http://localhost:8000",
            auth_code_lifetime=600,
            access_token_lifetime=3600,
            refresh_token_lifetime=86400,
            dynamic_registration=True,
            revocation_enabled=True,
        )

    @pytest.fixture
    def storage(self):
        """Create storage instance."""
        return InMemoryStorage()

    @pytest.fixture
    def provider(self, storage, config):
        """Create provider instance."""
        return TaskWarriorOAuthProvider(storage, config)

    @pytest.fixture
    def sample_client(self):
        """Create a sample client."""
        return OAuthClientInformationFull(
            client_id="test-client",
            client_secret="test-secret",
            redirect_uris=["http://localhost:3000/callback"],
            client_name="Test Client",
        )

    @pytest.mark.asyncio
    async def test_register_client_success(self, provider, storage):
        """Test successful client registration."""
        client = OAuthClientInformationFull(
            redirect_uris=["http://localhost:3000/callback"],
            client_name="New Client",
        )

        await provider.register_client(client)

        # Client should have ID and secret generated
        assert client.client_id is not None
        assert client.client_secret is not None
        assert client.client_id_issued_at is not None

        # Client should be stored
        stored = await storage.get_client(client.client_id)
        assert stored is not None
        assert stored.client_name == "New Client"

    @pytest.mark.asyncio
    async def test_register_client_no_redirect_uris(self, provider):
        """Test that registration fails without redirect URIs."""
        client = OAuthClientInformationFull(
            redirect_uris=None,
            client_name="Bad Client",
        )

        with pytest.raises(RegistrationError) as exc_info:
            await provider.register_client(client)

        assert exc_info.value.error == "invalid_redirect_uri"

    @pytest.mark.asyncio
    async def test_register_client_invalid_redirect_uri(self, provider):
        """Test that non-HTTPS redirect URIs are rejected."""
        client = OAuthClientInformationFull(
            redirect_uris=["http://example.com/callback"],  # Not HTTPS, not localhost
            client_name="Bad Client",
        )

        with pytest.raises(RegistrationError) as exc_info:
            await provider.register_client(client)

        assert exc_info.value.error == "invalid_redirect_uri"

    @pytest.mark.asyncio
    async def test_register_client_https_allowed(self, provider):
        """Test that HTTPS redirect URIs are allowed."""
        client = OAuthClientInformationFull(
            redirect_uris=["https://example.com/callback"],
            client_name="HTTPS Client",
        )

        await provider.register_client(client)
        assert client.client_id is not None

    @pytest.mark.asyncio
    async def test_get_client(self, provider, storage, sample_client):
        """Test getting a client."""
        await storage.save_client(sample_client)

        client = await provider.get_client("test-client")
        assert client is not None
        assert client.client_id == "test-client"

        # Non-existent client
        assert await provider.get_client("nonexistent") is None

    @pytest.mark.asyncio
    async def test_authorize_success(self, provider, storage, sample_client):
        """Test successful authorization."""
        await storage.save_client(sample_client)

        params = AuthorizationParams(
            state="test-state",
            scopes=["read", "write"],
            code_challenge="challenge123",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )

        redirect_url = await provider.authorize(sample_client, params)

        # Should redirect to client's redirect_uri with code and state
        assert "http://localhost:3000/callback" in redirect_url
        assert "code=" in redirect_url
        assert "state=test-state" in redirect_url

    @pytest.mark.asyncio
    async def test_authorize_no_client_id(self, provider):
        """Test that authorization fails without client ID."""
        client = OAuthClientInformationFull(
            redirect_uris=["http://localhost:3000/callback"],
        )

        params = AuthorizationParams(
            state="test-state",
            scopes=None,
            code_challenge="challenge123",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )

        with pytest.raises(AuthorizeError) as exc_info:
            await provider.authorize(client, params)

        assert exc_info.value.error == "invalid_request"

    @pytest.mark.asyncio
    async def test_load_authorization_code(self, provider, storage, sample_client):
        """Test loading an authorization code."""
        await storage.save_client(sample_client)

        # Create authorization code
        params = AuthorizationParams(
            state=None,
            scopes=["read"],
            code_challenge="challenge",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )
        redirect_url = await provider.authorize(sample_client, params)

        # Extract code from redirect URL
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(redirect_url)
        code = parse_qs(parsed.query)["code"][0]

        # Load the code
        auth_code = await provider.load_authorization_code(sample_client, code)
        assert auth_code is not None
        assert auth_code.client_id == "test-client"
        assert auth_code.scopes == ["read"]

    @pytest.mark.asyncio
    async def test_load_authorization_code_wrong_client(self, provider, storage, sample_client):
        """Test that loading code with wrong client fails."""
        await storage.save_client(sample_client)

        # Save a code for test-client
        code = AuthorizationCode(
            code="test-code",
            scopes=["read"],
            expires_at=time.time() + 600,
            client_id="test-client",
            code_challenge="challenge",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )
        await storage.save_authorization_code(code)

        # Try to load with different client
        other_client = OAuthClientInformationFull(
            client_id="other-client",
            redirect_uris=["http://localhost:3000/callback"],
        )

        result = await provider.load_authorization_code(other_client, "test-code")
        assert result is None

    @pytest.mark.asyncio
    async def test_load_authorization_code_expired(self, provider, storage, sample_client):
        """Test that expired codes are not loaded."""
        await storage.save_client(sample_client)

        # Save an expired code
        code = AuthorizationCode(
            code="expired-code",
            scopes=["read"],
            expires_at=time.time() - 1,  # Already expired
            client_id="test-client",
            code_challenge="challenge",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )
        await storage.save_authorization_code(code)

        result = await provider.load_authorization_code(sample_client, "expired-code")
        assert result is None

        # Code should be cleaned up
        assert await storage.get_authorization_code("expired-code") is None

    @pytest.mark.asyncio
    async def test_exchange_authorization_code(self, provider, storage, sample_client):
        """Test exchanging authorization code for tokens."""
        await storage.save_client(sample_client)

        # Create and save authorization code
        auth_code = AuthorizationCode(
            code="exchange-code",
            scopes=["read", "write"],
            expires_at=time.time() + 600,
            client_id="test-client",
            code_challenge="challenge",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )
        await storage.save_authorization_code(auth_code)

        # Exchange code
        token = await provider.exchange_authorization_code(sample_client, auth_code)

        assert token.access_token is not None
        assert token.refresh_token is not None
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.scope == "read write"

        # Authorization code should be deleted (one-time use)
        assert await storage.get_authorization_code("exchange-code") is None

        # Tokens should be stored
        access = await storage.get_access_token(token.access_token)
        assert access is not None
        assert access.client_id == "test-client"

    @pytest.mark.asyncio
    async def test_load_access_token(self, provider, storage):
        """Test loading an access token."""
        token = AccessToken(
            token="valid-token",
            client_id="test-client",
            scopes=["read"],
            expires_at=int(time.time() + 3600),
        )
        await storage.save_access_token(token)

        loaded = await provider.load_access_token("valid-token")
        assert loaded is not None
        assert loaded.token == "valid-token"

    @pytest.mark.asyncio
    async def test_load_access_token_expired(self, provider, storage):
        """Test that expired access tokens are not loaded."""
        token = AccessToken(
            token="expired-token",
            client_id="test-client",
            scopes=["read"],
            expires_at=int(time.time() - 1),  # Expired
        )
        await storage.save_access_token(token)

        loaded = await provider.load_access_token("expired-token")
        assert loaded is None

        # Token should be cleaned up
        assert await storage.get_access_token("expired-token") is None

    @pytest.mark.asyncio
    async def test_load_refresh_token(self, provider, storage, sample_client):
        """Test loading a refresh token."""
        token = RefreshToken(
            token="valid-refresh",
            client_id="test-client",
            scopes=["read"],
            expires_at=int(time.time() + 86400),
        )
        await storage.save_refresh_token(token)

        loaded = await provider.load_refresh_token(sample_client, "valid-refresh")
        assert loaded is not None
        assert loaded.token == "valid-refresh"

    @pytest.mark.asyncio
    async def test_load_refresh_token_wrong_client(self, provider, storage, sample_client):
        """Test that refresh token from wrong client is not loaded."""
        token = RefreshToken(
            token="other-refresh",
            client_id="other-client",
            scopes=["read"],
        )
        await storage.save_refresh_token(token)

        loaded = await provider.load_refresh_token(sample_client, "other-refresh")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_exchange_refresh_token(self, provider, storage, sample_client):
        """Test exchanging a refresh token for new tokens."""
        refresh = RefreshToken(
            token="old-refresh",
            client_id="test-client",
            scopes=["read", "write"],
            expires_at=int(time.time() + 86400),
        )
        await storage.save_refresh_token(refresh)

        new_token = await provider.exchange_refresh_token(sample_client, refresh, [])

        assert new_token.access_token is not None
        assert new_token.refresh_token is not None
        assert new_token.refresh_token != "old-refresh"  # Rotated

        # Old refresh token should be deleted
        assert await storage.get_refresh_token("old-refresh") is None

    @pytest.mark.asyncio
    async def test_exchange_refresh_token_reduced_scopes(self, provider, storage, sample_client):
        """Test exchanging refresh token with reduced scopes."""
        refresh = RefreshToken(
            token="scoped-refresh",
            client_id="test-client",
            scopes=["read", "write", "delete"],
        )
        await storage.save_refresh_token(refresh)

        # Request only "read" scope
        new_token = await provider.exchange_refresh_token(sample_client, refresh, ["read"])

        assert new_token.scope == "read"

    @pytest.mark.asyncio
    async def test_exchange_refresh_token_invalid_scope(self, provider, storage, sample_client):
        """Test that exchanging with invalid scope fails."""
        refresh = RefreshToken(
            token="limited-refresh",
            client_id="test-client",
            scopes=["read"],
        )
        await storage.save_refresh_token(refresh)

        # Request scope not in original grant
        with pytest.raises(TokenError) as exc_info:
            await provider.exchange_refresh_token(sample_client, refresh, ["admin"])

        assert exc_info.value.error == "invalid_scope"

    @pytest.mark.asyncio
    async def test_revoke_access_token(self, provider, storage):
        """Test revoking an access token."""
        access = AccessToken(
            token="revoke-access",
            client_id="test-client",
            scopes=["read"],
        )
        refresh = RefreshToken(
            token="associated-refresh",
            client_id="test-client",
            scopes=["read"],
        )
        await storage.save_access_token(access)
        await storage.save_refresh_token(refresh)

        await provider.revoke_token(access)

        # Both tokens should be deleted
        assert await storage.get_access_token("revoke-access") is None
        assert await storage.get_refresh_token("associated-refresh") is None

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self, provider, storage):
        """Test revoking a refresh token."""
        access = AccessToken(
            token="associated-access",
            client_id="test-client",
            scopes=["read"],
        )
        refresh = RefreshToken(
            token="revoke-refresh",
            client_id="test-client",
            scopes=["read"],
        )
        await storage.save_access_token(access)
        await storage.save_refresh_token(refresh)

        await provider.revoke_token(refresh)

        # Both tokens should be deleted
        assert await storage.get_access_token("associated-access") is None
        assert await storage.get_refresh_token("revoke-refresh") is None


class TestFullAuthorizationFlow:
    """Integration tests for the full authorization flow."""

    @pytest.fixture
    def config(self):
        """Create OAuth config."""
        return OAuthConfig(
            enabled=True,
            issuer_url="http://localhost:8000",
            auth_code_lifetime=600,
            access_token_lifetime=3600,
            refresh_token_lifetime=86400,
            dynamic_registration=True,
            revocation_enabled=True,
        )

    @pytest.fixture
    def storage(self):
        """Create storage."""
        return InMemoryStorage()

    @pytest.fixture
    def provider(self, storage, config):
        """Create provider."""
        return TaskWarriorOAuthProvider(storage, config)

    @pytest.mark.asyncio
    async def test_complete_flow(self, provider, storage):
        """Test complete OAuth flow: register -> authorize -> exchange -> refresh -> revoke."""
        from urllib.parse import urlparse, parse_qs

        # 1. Register client
        client = OAuthClientInformationFull(
            redirect_uris=["http://localhost:3000/callback"],
            client_name="Flow Test Client",
        )
        await provider.register_client(client)
        assert client.client_id is not None

        # 2. Authorize
        params = AuthorizationParams(
            state="unique-state",
            scopes=["read", "write"],
            code_challenge="challenge-value",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )
        redirect_url = await provider.authorize(client, params)

        # Extract code
        parsed = urlparse(redirect_url)
        query = parse_qs(parsed.query)
        code = query["code"][0]
        assert query["state"][0] == "unique-state"

        # 3. Exchange code for tokens
        auth_code = await provider.load_authorization_code(client, code)
        assert auth_code is not None

        token = await provider.exchange_authorization_code(client, auth_code)
        assert token.access_token is not None
        assert token.refresh_token is not None

        # 4. Verify access token
        access = await provider.load_access_token(token.access_token)
        assert access is not None
        assert access.client_id == client.client_id

        # 5. Refresh tokens
        refresh = await provider.load_refresh_token(client, token.refresh_token)
        assert refresh is not None

        new_token = await provider.exchange_refresh_token(client, refresh, [])
        assert new_token.access_token != token.access_token
        assert new_token.refresh_token != token.refresh_token

        # Old access token should still work (we didn't revoke it)
        # But old refresh token should be invalid (rotated)
        assert await provider.load_refresh_token(client, token.refresh_token) is None

        # 6. Revoke new tokens
        new_access = await provider.load_access_token(new_token.access_token)
        assert new_access is not None

        await provider.revoke_token(new_access)

        # Tokens should be revoked
        assert await provider.load_access_token(new_token.access_token) is None
        assert await provider.load_refresh_token(client, new_token.refresh_token) is None
