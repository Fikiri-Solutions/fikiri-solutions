"""Live-mode preflight for chatbot eval CLI (fail-fast, optional trace checkpoints)."""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import List, Optional

logger = logging.getLogger(__name__)


class LiveEvalUnavailableError(RuntimeError):
    """Raised when live eval cannot initialize required retrieval dependencies."""


def eval_trace_enabled() -> bool:
    return (os.getenv("FIKIRI_EVAL_TRACE_IMPORTS") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def trace_checkpoint(label: str) -> None:
    if eval_trace_enabled():
        print(f"[chatbot-eval] {label}", flush=True)


def _probe_vector_singleton(timeout_sec: float) -> None:
    """Initialize vector search singleton with a wall-clock guard."""

    def _init():
        from core.vector_search import get_vector_search

        get_vector_search()

    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(_init)
        try:
            fut.result(timeout=timeout_sec)
        except FuturesTimeout as exc:
            raise LiveEvalUnavailableError(
                f"vector search initialization exceeded {timeout_sec}s "
                "(likely sentence_transformers/torch mutex or Pinecone network). "
                "Set FIKIRI_VECTOR_EMBEDDINGS=hash, run with --mock, or stop other "
                "Python processes loading torch (e.g. duplicate app.py)."
            ) from exc
        except Exception as exc:
            raise LiveEvalUnavailableError(
                f"vector search initialization failed: {exc}"
            ) from exc


def preflight_live_eval_dependencies(
    *,
    timeout_sec: float = 45.0,
    require_vector: bool = False,
) -> List[str]:
    """
    Verify live retrieval dependencies can initialize.

    Returns checkpoint labels when tracing is enabled.
    Raises LiveEvalUnavailableError on failure.
    """
    checkpoints: List[str] = []
    started = time.perf_counter()

    def _step(label: str, fn) -> None:
        trace_checkpoint(f"preflight: {label} …")
        t0 = time.perf_counter()
        fn()
        elapsed = int((time.perf_counter() - t0) * 1000)
        checkpoints.append(f"{label} ({elapsed}ms)")
        trace_checkpoint(f"preflight: {label} ok ({elapsed}ms)")

    _step("import chatbot_retrieval", lambda: __import__("core.chatbot_retrieval", fromlist=["retrieve_chatbot_context"]))
    def _warm_faq_kb() -> None:
        from core.chatbot_retrieval import _get_faq_system, _get_knowledge_base

        _get_faq_system()
        _get_knowledge_base()

    _step("faq/kb singletons", _warm_faq_kb)

    if require_vector:
        _step(
            f"vector get_vector_search (timeout={timeout_sec}s)",
            lambda: _probe_vector_singleton(timeout_sec),
        )
    else:
        trace_checkpoint("preflight: vector probe skipped (feature flag off)")

    trace_checkpoint(
        f"preflight complete ({int((time.perf_counter() - started) * 1000)}ms)"
    )
    return checkpoints


def live_eval_needs_vector_probe() -> bool:
    try:
        from core.feature_flags import get_feature_flags

        return bool(get_feature_flags().is_enabled("vector_search"))
    except Exception:
        return False
