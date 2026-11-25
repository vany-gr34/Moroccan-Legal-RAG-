"""
Environment variable config reader.

Simple wrapper around os.getenv(). All configuration is read from .env files.
"""

import os


def get_config(config_key: str, default: str = "") -> str:
    """Get a configuration value from the environment.

    Args:
        config_key: Environment variable name (e.g. 'EMBEDDING_SERVICE_URL').
        default: Fallback value if not set.

    Returns:
        The configuration value as a string.
    """
    return os.getenv(config_key, default)
