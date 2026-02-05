"""Logging configuration for TaskWarrior MCP server."""

import logging
import logging.config
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

    Uses dictConfig to ensure consistent formatting across all loggers,
    including third-party libraries like Uvicorn.
    """
    # Get log level from environment
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Define consistent format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Use dictConfig for comprehensive logging configuration
    # This ensures uvicorn and other libraries use our format
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": log_format,
                "datefmt": date_format,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "level": log_level_name,
            "handlers": ["default"],
        },
        "loggers": {
            # Configure uvicorn loggers to use our format
            "uvicorn": {
                "level": log_level_name,
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": log_level_name,
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": log_level_name,
                "handlers": ["default"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)

    # Override uvicorn's default logging config to prevent it from
    # reconfiguring loggers when the server starts
    try:
        import uvicorn.config
        uvicorn.config.LOGGING_CONFIG["formatters"]["default"]["fmt"] = log_format
        uvicorn.config.LOGGING_CONFIG["formatters"]["default"]["datefmt"] = date_format
        uvicorn.config.LOGGING_CONFIG["formatters"]["access"]["fmt"] = log_format
        uvicorn.config.LOGGING_CONFIG["formatters"]["access"]["datefmt"] = date_format
    except (ImportError, KeyError):
        pass  # uvicorn not installed or config structure changed

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
