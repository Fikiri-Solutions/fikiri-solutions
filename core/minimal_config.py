#!/usr/bin/env python3
"""Deprecated compatibility wrapper for runtime config."""

import warnings

from core.config import *  # noqa: F401,F403

warnings.warn(
    "core.minimal_config is deprecated. Use core.config instead.",
    DeprecationWarning,
    stacklevel=2,
)
