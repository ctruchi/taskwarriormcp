"""OAuth module for TaskWarrior MCP server.

This module provides OAuth 2.0 Dynamic Client Registration (RFC 7591)
support for the TaskWarrior MCP server, implementing the MCP SDK's
OAuthAuthorizationServerProvider protocol.
"""

from .config import OAuthConfig
from .provider import TaskWarriorOAuthProvider
from .storage import InMemoryStorage

__all__ = [
    "InMemoryStorage",
    "OAuthConfig",
    "TaskWarriorOAuthProvider",
]
