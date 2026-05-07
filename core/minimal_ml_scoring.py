#!/usr/bin/env python3
"""Deprecated compatibility wrapper for ML scoring."""

import warnings

from core.ml_scoring import *  # noqa: F401,F403

warnings.warn(
    "core.minimal_ml_scoring is deprecated. Use core.ml_scoring instead.",
    DeprecationWarning,
    stacklevel=2,
)
