import os
import logging

try:
    # Python 3.8+
    from importlib.metadata import version as _pkg_version
except Exception:  # pragma: no cover
    _pkg_version = None  # type: ignore

def _get_version() -> str:
    if _pkg_version is None:
        return "0.0.0"
    try:
        # Must match [project].name in pyproject.toml
        return _pkg_version("msight_core")
    except Exception:
        # Happens when running from source tree without installation
        return "0.0.0"

__version__ = _get_version()

REDIS_MESSAGE_BROKER_HOST = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_HOST", "localhost")
REDIS_MESSAGE_BROKER_PORT = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_PORT", 6379)
REDIS_MESSAGE_BROKER_DB = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_DB", 0)
MSIGHT_EDGE_DEVICE_NAME = os.getenv("MSIGHT_EDGE_DEVICE_NAME")
LOGGING_LEVEL = os.getenv("MSIGHT_LOGGING_LEVEL", "INFO").upper()
logging.basicConfig(level=LOGGING_LEVEL)

assert MSIGHT_EDGE_DEVICE_NAME is not None, "MSIGHT_EDGE_DEVICE_NAME environment variable must be set."

