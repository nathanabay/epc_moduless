"""
Logger Utility

Centralized logging configuration for EPC module.
"""

import frappe
import logging
import os
from datetime import datetime


class EPCLogger:
    """Logger class for EPC module with Frappe integration."""

    _loggers = {}

    @classmethod
    def get_logger(cls, name):
        """Get or create a logger for the given name."""
        if name not in cls._loggers:
            cls._loggers[name] = cls(name)
        return cls._loggers[name]

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)

            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            ch.setFormatter(formatter)

            self.logger.addHandler(ch)

    def info(self, message, **kwargs):
        """Log info message."""
        self._log_with_context('INFO', message, kwargs)

    def warning(self, message, **kwargs):
        """Log warning message."""
        self._log_with_context('WARNING', message, kwargs)

    def error(self, message, **kwargs):
        """Log error message."""
        self._log_with_context('ERROR', message, kwargs)

    def debug(self, message, **kwargs):
        """Log debug message."""
        self._log_with_context('DEBUG', message, kwargs)

    def _log_with_context(self, level, message, context):
        """Log with additional context."""
        # Add context to message
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"

        # Log to Python logger
        getattr(self.logger, level.lower())(message)

        # Also log to Frappe Error Log for ERROR level
        if level == 'ERROR':
            try:
                frappe.log_error(
                    title=f"EPC Module Error: {message}",
                    message=f"Logger: {self.logger.name}\nContext: {context}"
                )
            except Exception:
                pass  # Ignore if Frappe not available


# Backward compatibility function
def get_epc_logger(module_name):
    """Get a configured logger for the EPC module."""
    return EPCLogger.get_logger(module_name)