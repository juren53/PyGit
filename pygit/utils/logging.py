"""
Logging framework for PyGit.

This module provides structured logging with configurable levels,
output formats, and destinations for PyGit operations.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any


class PyGitLogger:
    """PyGit-specific logger with structured output."""

    def __init__(
        self,
        name: str = "pygit",
        level: str = "INFO",
        log_file: Optional[Path] = None,
        format_type: str = "simple",
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Setup formatters
        self.formatters = {
            "simple": logging.Formatter("%(message)s"),
            "detailed": logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            "git": logging.Formatter("%(levelname)s: %(message)s"),
            "debug": logging.Formatter(
                "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
            ),
        }

        formatter = self.formatters.get(format_type, self.formatters["simple"])

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)

    def set_level(self, level: str):
        """Set logging level."""
        self.logger.setLevel(getattr(logging, level.upper()))

    def add_file_handler(self, log_file: Path, format_type: str = "detailed"):
        """Add a file handler."""
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            self.formatters.get(format_type, self.formatters["detailed"])
        )
        self.logger.addHandler(file_handler)

    def operation(self, operation: str, details: Dict[str, Any] = None):
        """Log a Git operation with structured details."""
        message = f"Operation: {operation}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" ({detail_str})"
        self.info(message)

    def object_operation(self, operation: str, obj_type: str, sha1: str):
        """Log a Git object operation."""
        self.info(f"{operation} {obj_type} {sha1}")

    def remote_operation(self, operation: str, remote: str, details: str = ""):
        """Log a remote operation."""
        message = f"{operation} {remote}"
        if details:
            message += f": {details}"
        self.info(message)

    def progress(self, message: str, current: int = None, total: int = None):
        """Log progress information."""
        if current is not None and total is not None:
            percentage = (current / total) * 100
            self.info(f"{message}: {current}/{total} ({percentage:.1f}%)")
        else:
            self.info(message)

    def __getattr__(self, name):
        """Delegate to underlying logger for any missing methods."""
        return getattr(self.logger, name)


# Global logger instance
_global_logger: Optional[PyGitLogger] = None


def get_logger(name: str = "pygit", **kwargs) -> PyGitLogger:
    """Get or create a PyGit logger instance."""
    global _global_logger

    if _global_logger is None or name != _global_logger.logger.name:
        _global_logger = PyGitLogger(name, **kwargs)

    return _global_logger


def configure_logging(
    level: str = "INFO", log_file: Optional[Path] = None, format_type: str = "simple"
):
    """Configure the global PyGit logger."""
    global _global_logger
    _global_logger = PyGitLogger("pygit", level, log_file, format_type)
    return _global_logger


def log_operation(operation: str, **kwargs):
    """Convenience function to log an operation."""
    get_logger().operation(operation, kwargs)


def log_object(operation: str, obj_type: str, sha1: str):
    """Convenience function to log object operations."""
    get_logger().object_operation(operation, obj_type, sha1)


def log_remote(operation: str, remote: str, details: str = ""):
    """Convenience function to log remote operations."""
    get_logger().remote_operation(operation, remote, details)


def log_progress(message: str, current: int = None, total: int = None):
    """Convenience function to log progress."""
    get_logger().progress(message, current, total)
