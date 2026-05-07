#!/usr/bin/env python3
"""Deprecated compatibility wrapper for vector search."""

import warnings

from core.vector_search import *  # noqa: F401,F403

warnings.warn(
    "core.minimal_vector_search is deprecated. Use core.vector_search instead.",
    DeprecationWarning,
    stacklevel=2,
)
