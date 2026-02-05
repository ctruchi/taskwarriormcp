"""Configuration management for TaskWarrior MCP server."""

import os
from dataclasses import dataclass, field

from .logging_config import get_logger
from .validation import validate_task_command, ValidationError
from .exceptions import TaskWarriorValidationError
from .oauth.config import OAuthConfig

logger = get_logger(__name__)


VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")


@dataclass
class Config:
    """Configuration for TaskWarrior MCP server."""

    task_command: str
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    oauth: OAuthConfig = field(default_factory=lambda: OAuthConfig.from_env())

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance
        """
        task_command = os.environ.get("TASK_COMMAND", "task")
        logger.debug(f"Loaded TASK_COMMAND from environment: {task_command}")

        transport = os.environ.get("MCP_TRANSPORT", "stdio")
        logger.debug(f"Loaded MCP_TRANSPORT from environment: {transport}")

        host = os.environ.get("MCP_HOST", "127.0.0.1")
        logger.debug(f"Loaded MCP_HOST from environment: {host}")

        port = int(os.environ.get("MCP_PORT", "8000"))
        logger.debug(f"Loaded MCP_PORT from environment: {port}")

        oauth = OAuthConfig.from_env()

        return cls(task_command=task_command, transport=transport, host=host, port=port, oauth=oauth)

    def validate(self) -> None:
        """Validate configuration.

        Raises:
            TaskWarriorValidationError: If configuration is invalid
        """
        try:
            self.task_command = validate_task_command(self.task_command)
            logger.info(f"Configuration validated successfully: task_command={self.task_command}")
        except ValidationError as e:
            logger.error(f"TASK_COMMAND validation failed: {e}")
            raise TaskWarriorValidationError(str(e)) from e

        # Validate transport
        if self.transport not in VALID_TRANSPORTS:
            msg = f"Invalid MCP_TRANSPORT: {self.transport}. Must be one of: {', '.join(VALID_TRANSPORTS)}"
            logger.error(msg)
            raise TaskWarriorValidationError(msg)

        # Validate port
        if not (1 <= self.port <= 65535):
            msg = f"Invalid MCP_PORT: {self.port}. Must be between 1 and 65535"
            logger.error(msg)
            raise TaskWarriorValidationError(msg)

        logger.info(f"Transport configured: {self.transport}, host={self.host}, port={self.port}")

        # Validate OAuth configuration
        self.oauth.validate()
