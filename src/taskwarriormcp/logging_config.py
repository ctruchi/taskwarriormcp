"""Logging configuration for TaskWarrior MCP server."""

import logging
import os
import sys
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

    Reads LOG_LEVEL from environment variable (default: INFO).
    Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    # Get log level from environment
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Validate and convert to logging level
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True  # Override any existing configuration
    )

    # Log the configured level
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized with level: {log_level_name}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
