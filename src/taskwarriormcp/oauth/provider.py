"""OAuth authorization server provider implementation."""

import secrets
import time
from urllib.parse import urlparse

from pydantic import AnyUrl

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from ..logging_config import get_logger
from .config import OAuthConfig
from .storage import InMemoryStorage

logger = get_logger(__name__)


class TaskWarriorOAuthProvider:
    """OAuth authorization server provider for TaskWarrior MCP.

    Implements the OAuthAuthorizationServerProvider protocol from the MCP SDK.
    Handles client registration, authorization, and token management.
    """

    def __init__(self, storage: InMemoryStorage, config: OAuthConfig) -> None:
        """Initialize the OAuth provider.

        Args:
            storage: In-memory storage for OAuth data
            config: OAuth configuration settings
        """
        self._storage = storage
        self._config = config
        logger.info("TaskWarriorOAuthProvider initialized")

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Retrieve client information by client ID.

        Args:
            client_id: The ID of the client to retrieve

        Returns:
            The client information, or None if the client does not exist
        """
        logger.debug(f"Getting client: {client_id}")
        return await self._storage.get_client(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Register a new OAuth client.

        Validates redirect URIs and generates client credentials.

        Args:
            client_info: The client metadata to register

        Raises:
            RegistrationError: If the client metadata is invalid
        """
        logger.info(f"Registering new client: {client_info.client_name or 'unnamed'}")

        # Validate redirect URIs
        if not client_info.redirect_uris:
            raise RegistrationError(
                error="invalid_redirect_uri",
                error_description="At least one redirect_uri is required"
            )

        for redirect_uri in client_info.redirect_uris:
            self._validate_redirect_uri(redirect_uri)

        # Generate client credentials if not provided
        if not client_info.client_id:
            client_info.client_id = self._generate_client_id()

        # Generate client secret for confidential clients
        if client_info.token_endpoint_auth_method != "none":
            if not client_info.client_secret:
                client_info.client_secret = self._generate_client_secret()

        # Set issued timestamp
        client_info.client_id_issued_at = int(time.time())

        # Save client
        await self._storage.save_client(client_info)
        logger.info(f"Client registered successfully: {client_info.client_id}")

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams
    ) -> str:
        """Handle authorization request and return redirect URL.

        Generates an authorization code and constructs the redirect URI.

        Args:
            client: The client requesting authorization
            params: The authorization request parameters

        Returns:
            A URL to redirect the client to

        Raises:
            AuthorizeError: If the authorization request is invalid
        """
        logger.info(f"Processing authorization request for client: {client.client_id}")

        if not client.client_id:
            raise AuthorizeError(
                error="invalid_request",
                error_description="Client ID is required"
            )

        # Generate authorization code with high entropy (256 bits)
        code = secrets.token_urlsafe(32)

        # Calculate expiration time
        expires_at = time.time() + self._config.auth_code_lifetime

        # Determine scopes
        scopes = params.scopes if params.scopes else []

        # Create authorization code object
        auth_code = AuthorizationCode(
            code=code,
            scopes=scopes,
            expires_at=expires_at,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
        )

        # Store the authorization code
        await self._storage.save_authorization_code(auth_code)

        # Construct redirect URI with code and state
        redirect_url = construct_redirect_uri(
            str(params.redirect_uri),
            code=code,
            state=params.state,
        )

        logger.info(f"Authorization code generated for client: {client.client_id}")
        return redirect_url

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str
    ) -> AuthorizationCode | None:
        """Load an authorization code by its code string.

        Args:
            client: The client that requested the authorization code
            authorization_code: The authorization code to load

        Returns:
            The AuthorizationCode, or None if not found or expired
        """
        logger.debug(f"Loading authorization code for client: {client.client_id}")

        auth_code = await self._storage.get_authorization_code(authorization_code)
        if not auth_code:
            logger.debug("Authorization code not found")
            return None

        # Verify the code belongs to this client
        if auth_code.client_id != client.client_id:
            logger.warning(
                f"Authorization code client mismatch: "
                f"expected {client.client_id}, got {auth_code.client_id}"
            )
            return None

        # Check if code is expired
        if time.time() > auth_code.expires_at:
            logger.debug("Authorization code expired")
            # Clean up expired code
            await self._storage.delete_authorization_code(authorization_code)
            return None

        return auth_code

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode
    ) -> OAuthToken:
        """Exchange an authorization code for access and refresh tokens.

        Args:
            client: The client exchanging the authorization code
            authorization_code: The authorization code to exchange

        Returns:
            The OAuth token containing access and refresh tokens

        Raises:
            TokenError: If the exchange fails
        """
        logger.info(f"Exchanging authorization code for client: {client.client_id}")

        # Delete the authorization code (one-time use)
        await self._storage.delete_authorization_code(authorization_code.code)

        # Generate access token
        access_token_str = secrets.token_urlsafe(32)
        access_token_expires_at = int(time.time() + self._config.access_token_lifetime)

        access_token = AccessToken(
            token=access_token_str,
            client_id=authorization_code.client_id,
            scopes=authorization_code.scopes,
            expires_at=access_token_expires_at,
            resource=authorization_code.resource,
        )
        await self._storage.save_access_token(access_token)

        # Generate refresh token
        refresh_token_str = secrets.token_urlsafe(32)
        refresh_token_expires_at = int(time.time() + self._config.refresh_token_lifetime)

        refresh_token = RefreshToken(
            token=refresh_token_str,
            client_id=authorization_code.client_id,
            scopes=authorization_code.scopes,
            expires_at=refresh_token_expires_at,
        )
        await self._storage.save_refresh_token(refresh_token)

        # Build scope string
        scope = " ".join(authorization_code.scopes) if authorization_code.scopes else None

        logger.info(f"Tokens generated for client: {client.client_id}")

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=self._config.access_token_lifetime,
            scope=scope,
            refresh_token=refresh_token_str,
        )

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str
    ) -> RefreshToken | None:
        """Load a refresh token by its token string.

        Args:
            client: The client requesting to load the refresh token
            refresh_token: The refresh token string to load

        Returns:
            The RefreshToken object if found and valid, None otherwise
        """
        logger.debug(f"Loading refresh token for client: {client.client_id}")

        token = await self._storage.get_refresh_token(refresh_token)
        if not token:
            logger.debug("Refresh token not found")
            return None

        # Verify the token belongs to this client
        if token.client_id != client.client_id:
            logger.warning(
                f"Refresh token client mismatch: "
                f"expected {client.client_id}, got {token.client_id}"
            )
            return None

        # Check if token is expired
        if token.expires_at is not None and time.time() > token.expires_at:
            logger.debug("Refresh token expired")
            await self._storage.delete_refresh_token(refresh_token)
            return None

        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Exchange a refresh token for new tokens.

        Rotates both access and refresh tokens.

        Args:
            client: The client exchanging the refresh token
            refresh_token: The refresh token to exchange
            scopes: Requested scopes for the new token

        Returns:
            The OAuth token containing new access and refresh tokens

        Raises:
            TokenError: If the exchange fails
        """
        logger.info(f"Exchanging refresh token for client: {client.client_id}")

        # Validate scopes - can only request same or fewer scopes
        if scopes:
            for scope in scopes:
                if scope not in refresh_token.scopes:
                    raise TokenError(
                        error="invalid_scope",
                        error_description=f"Scope '{scope}' not in original grant"
                    )
            token_scopes = scopes
        else:
            token_scopes = refresh_token.scopes

        # Delete old refresh token (rotation)
        await self._storage.delete_refresh_token(refresh_token.token)

        # Generate new access token
        access_token_str = secrets.token_urlsafe(32)
        access_token_expires_at = int(time.time() + self._config.access_token_lifetime)

        access_token = AccessToken(
            token=access_token_str,
            client_id=refresh_token.client_id,
            scopes=token_scopes,
            expires_at=access_token_expires_at,
        )
        await self._storage.save_access_token(access_token)

        # Generate new refresh token (rotation)
        new_refresh_token_str = secrets.token_urlsafe(32)
        new_refresh_token_expires_at = int(time.time() + self._config.refresh_token_lifetime)

        new_refresh_token = RefreshToken(
            token=new_refresh_token_str,
            client_id=refresh_token.client_id,
            scopes=token_scopes,
            expires_at=new_refresh_token_expires_at,
        )
        await self._storage.save_refresh_token(new_refresh_token)

        # Build scope string
        scope = " ".join(token_scopes) if token_scopes else None

        logger.info(f"Tokens rotated for client: {client.client_id}")

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=self._config.access_token_lifetime,
            scope=scope,
            refresh_token=new_refresh_token_str,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load and validate an access token.

        Args:
            token: The access token string to verify

        Returns:
            The AccessToken if valid, None otherwise
        """
        logger.debug("Loading access token")

        access_token = await self._storage.get_access_token(token)
        if not access_token:
            logger.debug("Access token not found")
            return None

        # Check if token is expired
        if access_token.expires_at is not None and time.time() > access_token.expires_at:
            logger.debug("Access token expired")
            await self._storage.delete_access_token(token)
            return None

        logger.debug(f"Access token valid for client: {access_token.client_id}")
        return access_token

    async def revoke_token(
        self,
        token: AccessToken | RefreshToken,
    ) -> None:
        """Revoke an access or refresh token.

        Also revokes associated tokens (if revoking refresh token, revokes
        access tokens for the same client, and vice versa).

        Args:
            token: The token to revoke
        """
        logger.info(f"Revoking token for client: {token.client_id}")

        if isinstance(token, AccessToken):
            await self._storage.delete_access_token(token.token)
            # Also revoke all refresh tokens for this client
            await self._storage.delete_refresh_tokens_for_client(token.client_id)
        elif isinstance(token, RefreshToken):
            await self._storage.delete_refresh_token(token.token)
            # Also revoke all access tokens for this client
            await self._storage.delete_access_tokens_for_client(token.client_id)

        logger.info(f"Token revoked for client: {token.client_id}")

    def _validate_redirect_uri(self, redirect_uri: AnyUrl) -> None:
        """Validate a redirect URI.

        Redirect URIs must be HTTPS or localhost.

        Args:
            redirect_uri: The redirect URI to validate

        Raises:
            RegistrationError: If the redirect URI is invalid
        """
        uri_str = str(redirect_uri)
        parsed = urlparse(uri_str)

        # Allow localhost for development
        if parsed.hostname in ("localhost", "127.0.0.1", "::1", "[::1]"):
            logger.debug(f"Allowing localhost redirect URI: {uri_str}")
            return

        # Require HTTPS for non-localhost
        if parsed.scheme != "https":
            logger.warning(f"Rejecting non-HTTPS redirect URI: {uri_str}")
            raise RegistrationError(
                error="invalid_redirect_uri",
                error_description="Redirect URI must use HTTPS (except for localhost)"
            )

        logger.debug(f"Validated redirect URI: {uri_str}")

    def _generate_client_id(self) -> str:
        """Generate a unique client ID.

        Returns:
            A unique client ID string
        """
        return secrets.token_urlsafe(16)

    def _generate_client_secret(self) -> str:
        """Generate a secure client secret.

        Returns:
            A secure client secret string (256 bits of entropy)
        """
        return secrets.token_urlsafe(32)
