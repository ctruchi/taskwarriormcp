"""Configuration management for TaskWarrior MCP server."""

import os
from dataclasses import dataclass, field

from .logging_config import get_logger
from .validation import validate_task_command, ValidationError
from .exceptions import TaskWarriorValidationError
from .oauth.config import OAuthConfig

logger = get_logger(__name__)


@dataclass
class Config:
    """Configuration for TaskWarrior MCP server."""

    task_command: str
    oauth: OAuthConfig = field(default_factory=lambda: OAuthConfig.from_env())

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance
        """
        task_command = os.environ.get("TASK_COMMAND", "task")
        logger.debug(f"Loaded TASK_COMMAND from environment: {task_command}")

        oauth = OAuthConfig.from_env()

        return cls(task_command=task_command, oauth=oauth)

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

        # Validate OAuth configuration
        self.oauth.validate()
