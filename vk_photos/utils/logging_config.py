"""Logging configuration for VK Photos application.

This module provides centralized logging configuration with consistent formatting
and log levels across the entire application.
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """
    Set up centralized logging configuration for the VK Photos application.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path to write logs to
        format_string: Optional custom format string for log messages

    Returns:
        Configured logger instance

    Note:
        If no format_string is provided, uses a standard format with timestamp,
        logger name, level, and message.
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    formatter = logging.Formatter(format_string, datefmt="%d-%b-%y %H:%M:%S")

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file is not None:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Create and return application logger
    app_logger = logging.getLogger("vk_photos")
    app_logger.setLevel(level)

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (usually module name)

    Returns:
        Logger instance configured with the application's logging settings
    """
    return logging.getLogger(f"vk_photos.{name}")


# Default logger instances for common modules
def get_downloader_logger() -> logging.Logger:
    """Get logger for downloader modules."""
    return get_logger("downloaders")


def get_utils_logger() -> logging.Logger:
    """Get logger for utility modules."""
    return get_logger("utils")


def get_main_logger() -> logging.Logger:
    """Get logger for main application."""
    return get_logger("main")
