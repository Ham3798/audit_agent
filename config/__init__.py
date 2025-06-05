"""
Configuration package for audit_agent

This package contains configuration and logging setup for the audit_agent project.
"""

from .settings import Settings
from .logging_config import setup_logging

__all__ = ['Settings', 'setup_logging'] 