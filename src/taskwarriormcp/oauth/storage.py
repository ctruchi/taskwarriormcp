"""Thread-safe in-memory storage for OAuth clients and tokens."""

import threading
from typing import TypeVar

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull

from ..logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class InMemoryStorage:
    """Thread-safe in-memory storage for OAuth data.

    Stores OAuth clients, authorization codes, access tokens, and refresh tokens
    in memory with thread-safe access using locks.

    Note: This storage is ephemeral and data is lost on server restart.
    For production use, consider implementing persistent storage.
    """

    def __init__(self) -> None:
        """Initialize empty storage with thread locks."""
        self._lock = threading.Lock()

        # Client storage: client_id -> OAuthClientInformationFull
        self._clients: dict[str, OAuthClientInformationFull] = {}

        # Authorization code storage: code -> AuthorizationCode
        self._authorization_codes: dict[str, AuthorizationCode] = {}

        # Access token storage: token -> AccessToken
        self._access_tokens: dict[str, AccessToken] = {}

        # Refresh token storage: token -> RefreshToken
        self._refresh_tokens: dict[str, RefreshToken] = {}

        logger.debug("InMemoryStorage initialized")

    # Client methods
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Retrieve a client by ID.

        Args:
            client_id: The client ID to look up

        Returns:
            The client information if found, None otherwise
        """
        with self._lock:
            client = self._clients.get(client_id)
            if client:
                logger.debug(f"Retrieved client: {client_id}")
            else:
                logger.debug(f"Client not found: {client_id}")
            return client

    async def save_client(self, client: OAuthClientInformationFull) -> None:
        """Save a client to storage.

        Args:
            client: The client information to save

        Raises:
            ValueError: If client_id is not set
        """
        if not client.client_id:
            raise ValueError("Client must have a client_id")

        with self._lock:
            self._clients[client.client_id] = client
            logger.debug(f"Saved client: {client.client_id}")

    async def delete_client(self, client_id: str) -> bool:
        """Delete a client from storage.

        Args:
            client_id: The client ID to delete

        Returns:
            True if client was deleted, False if not found
        """
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                logger.debug(f"Deleted client: {client_id}")
                return True
            logger.debug(f"Client not found for deletion: {client_id}")
            return False

    # Authorization code methods
    async def save_authorization_code(self, code: AuthorizationCode) -> None:
        """Save an authorization code to storage.

        Args:
            code: The authorization code to save
        """
        with self._lock:
            self._authorization_codes[code.code] = code
            logger.debug(f"Saved authorization code for client: {code.client_id}")

    async def get_authorization_code(self, code: str) -> AuthorizationCode | None:
        """Retrieve an authorization code.

        Args:
            code: The authorization code string

        Returns:
            The authorization code if found, None otherwise
        """
        with self._lock:
            auth_code = self._authorization_codes.get(code)
            if auth_code:
                logger.debug(f"Retrieved authorization code for client: {auth_code.client_id}")
            else:
                logger.debug("Authorization code not found")
            return auth_code

    async def delete_authorization_code(self, code: str) -> bool:
        """Delete an authorization code from storage.

        Args:
            code: The authorization code string to delete

        Returns:
            True if code was deleted, False if not found
        """
        with self._lock:
            if code in self._authorization_codes:
                del self._authorization_codes[code]
                logger.debug("Deleted authorization code")
                return True
            logger.debug("Authorization code not found for deletion")
            return False

    # Access token methods
    async def save_access_token(self, token: AccessToken) -> None:
        """Save an access token to storage.

        Args:
            token: The access token to save
        """
        with self._lock:
            self._access_tokens[token.token] = token
            logger.debug(f"Saved access token for client: {token.client_id}")

    async def get_access_token(self, token: str) -> AccessToken | None:
        """Retrieve an access token.

        Args:
            token: The access token string

        Returns:
            The access token if found, None otherwise
        """
        with self._lock:
            access_token = self._access_tokens.get(token)
            if access_token:
                logger.debug(f"Retrieved access token for client: {access_token.client_id}")
            else:
                logger.debug("Access token not found")
            return access_token

    async def delete_access_token(self, token: str) -> bool:
        """Delete an access token from storage.

        Args:
            token: The access token string to delete

        Returns:
            True if token was deleted, False if not found
        """
        with self._lock:
            if token in self._access_tokens:
                del self._access_tokens[token]
                logger.debug("Deleted access token")
                return True
            logger.debug("Access token not found for deletion")
            return False

    async def delete_access_tokens_for_client(self, client_id: str) -> int:
        """Delete all access tokens for a specific client.

        Args:
            client_id: The client ID whose tokens should be deleted

        Returns:
            Number of tokens deleted
        """
        with self._lock:
            to_delete = [
                token for token, data in self._access_tokens.items()
                if data.client_id == client_id
            ]
            for token in to_delete:
                del self._access_tokens[token]
            if to_delete:
                logger.debug(f"Deleted {len(to_delete)} access tokens for client: {client_id}")
            return len(to_delete)

    # Refresh token methods
    async def save_refresh_token(self, token: RefreshToken) -> None:
        """Save a refresh token to storage.

        Args:
            token: The refresh token to save
        """
        with self._lock:
            self._refresh_tokens[token.token] = token
            logger.debug(f"Saved refresh token for client: {token.client_id}")

    async def get_refresh_token(self, token: str) -> RefreshToken | None:
        """Retrieve a refresh token.

        Args:
            token: The refresh token string

        Returns:
            The refresh token if found, None otherwise
        """
        with self._lock:
            refresh_token = self._refresh_tokens.get(token)
            if refresh_token:
                logger.debug(f"Retrieved refresh token for client: {refresh_token.client_id}")
            else:
                logger.debug("Refresh token not found")
            return refresh_token

    async def delete_refresh_token(self, token: str) -> bool:
        """Delete a refresh token from storage.

        Args:
            token: The refresh token string to delete

        Returns:
            True if token was deleted, False if not found
        """
        with self._lock:
            if token in self._refresh_tokens:
                del self._refresh_tokens[token]
                logger.debug("Deleted refresh token")
                return True
            logger.debug("Refresh token not found for deletion")
            return False

    async def delete_refresh_tokens_for_client(self, client_id: str) -> int:
        """Delete all refresh tokens for a specific client.

        Args:
            client_id: The client ID whose tokens should be deleted

        Returns:
            Number of tokens deleted
        """
        with self._lock:
            to_delete = [
                token for token, data in self._refresh_tokens.items()
                if data.client_id == client_id
            ]
            for token in to_delete:
                del self._refresh_tokens[token]
            if to_delete:
                logger.debug(f"Deleted {len(to_delete)} refresh tokens for client: {client_id}")
            return len(to_delete)

    # Utility methods
    def get_stats(self) -> dict[str, int]:
        """Get storage statistics.

        Returns:
            Dictionary with counts of stored items
        """
        with self._lock:
            return {
                "clients": len(self._clients),
                "authorization_codes": len(self._authorization_codes),
                "access_tokens": len(self._access_tokens),
                "refresh_tokens": len(self._refresh_tokens),
            }

    def clear(self) -> None:
        """Clear all stored data.

        Warning: This will invalidate all tokens and remove all clients.
        """
        with self._lock:
            self._clients.clear()
            self._authorization_codes.clear()
            self._access_tokens.clear()
            self._refresh_tokens.clear()
            logger.info("Cleared all OAuth storage data")
