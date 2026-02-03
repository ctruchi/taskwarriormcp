"""Configuration management for TaskWarrior MCP server."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration for TaskWarrior MCP server."""

    task_command: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance
        """
        task_command = os.environ.get("TASK_COMMAND", "task")
        return cls(task_command=task_command)

    def validate(self) -> None:
        """Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.task_command or not self.task_command.strip():
            raise ValueError("TASK_COMMAND cannot be empty")
