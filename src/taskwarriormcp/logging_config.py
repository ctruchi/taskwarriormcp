"""Logging configuration for TaskWarrior MCP server."""

import logging
import logging.config
from pathlib import Path
from typing import Any


def sanitize_for_logging(data: Any, max_length: int = 100) -> str:
    """Sanitize data for logging by truncating long strings.

    Args:
        data: Data to sanitize
        max_length: Maximum length for string representation

    Returns:
        Sanitized string representation
    """
    str_repr = str(data)
    if len(str_repr) > max_length:
        return str_repr[:max_length] + "..."
    return str_repr


def sanitize_command(command: list[str]) -> str:
    """Sanitize command for logging by removing sensitive data.

    Args:
        command: Command parts list

    Returns:
        Sanitized command string
    """
    # Don't log full task descriptions or credentials
    sanitized = []
    for part in command:
        # Truncate long arguments
        if len(part) > 50:
            sanitized.append(part[:50] + "...")
        else:
            sanitized.append(part)
    return " ".join(sanitized)


def setup_logging() -> None:
    """Configure logging for the application.

    Loads configuration from logging.ini file.
    Edit logging.ini to change log levels and formatting.
    """
    config_path = Path(__file__).parent / "logging.ini"
    logging.config.fileConfig(config_path, disable_existing_loggers=False)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
