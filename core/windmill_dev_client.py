"""Minimal Windmill CE HTTP client for the Fikiri development pilot.

Used only for Flask → Windmill outbound job runs against a local CE instance.
Never logs tokens or full payloads.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_WORKSPACE = "fikiri-dev"
DEFAULT_SCRIPT_PATH = "f/normalize_leads/normalize_leads"
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_WAIT_TIMEOUT_S = 60.0


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def windmill_trigger_enabled() -> bool:
    return _env("FIKIRI_WINDMILL_TRIGGER_ENABLED").lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class WindmillDevConfig:
    base_url: str
    workspace: str
    token: str
    script_path: str
    timeout_s: float
    wait_timeout_s: float

    @classmethod
    def from_env(cls) -> "WindmillDevConfig":
        timeout_raw = _env("WINDMILL_HTTP_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_S))
        wait_raw = _env("WINDMILL_WAIT_TIMEOUT_SECONDS", str(DEFAULT_WAIT_TIMEOUT_S))
        try:
            timeout_s = float(timeout_raw)
        except ValueError:
            timeout_s = DEFAULT_TIMEOUT_S
        try:
            wait_timeout_s = float(wait_raw)
        except ValueError:
            wait_timeout_s = DEFAULT_WAIT_TIMEOUT_S
        return cls(
            base_url=_env("WINDMILL_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            workspace=_env("WINDMILL_WORKSPACE", DEFAULT_WORKSPACE),
            token=_env("WINDMILL_DEV_TOKEN") or _env("WINDMILL_TOKEN"),
            script_path=_env(
                "WINDMILL_NORMALIZE_SCRIPT_PATH", DEFAULT_SCRIPT_PATH
            ).lstrip("/"),
            timeout_s=max(1.0, timeout_s),
            wait_timeout_s=max(1.0, wait_timeout_s),
        )


class WindmillClientError(Exception):
    def __init__(self, message: str, *, status_code: Optional[int] = None, error_code: str = "WINDMILL_ERROR"):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


def _script_path_url_segment(script_path: str) -> str:
    # Windmill expects /p/<path> with slashes preserved (not fully encoded).
    parts = [p for p in script_path.split("/") if p]
    return "/".join(quote(p, safe="") for p in parts)


def _post_json(
    url: str,
    *,
    token: str,
    body: Dict[str, Any],
    timeout_s: float,
) -> Tuple[int, str]:
    data = json.dumps(body, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        except Exception:
            err_body = ""
        raise WindmillClientError(
            (err_body or f"Windmill HTTP {exc.code}")[:300],
            status_code=int(exc.code),
            error_code="WINDMILL_HTTP_ERROR",
        ) from exc
    except urllib.error.URLError as exc:
        raise WindmillClientError(
            f"Windmill unreachable: {exc.reason}",
            error_code="WINDMILL_UNREACHABLE",
        ) from exc


def run_script(
    args: Dict[str, Any],
    *,
    config: Optional[WindmillDevConfig] = None,
    wait: bool = False,
) -> Dict[str, Any]:
    """
    Enqueue (or wait for) a Windmill script run.

    wait=False → POST .../jobs/run/p/... → {job_id}
    wait=True  → POST .../jobs/run_wait_result/p/... → {job_id: None, result}
    """
    cfg = config or WindmillDevConfig.from_env()
    if not cfg.token:
        raise WindmillClientError(
            "WINDMILL_DEV_TOKEN is not configured",
            error_code="WINDMILL_TOKEN_MISSING",
        )
    if not cfg.workspace or not cfg.script_path:
        raise WindmillClientError(
            "Windmill workspace/script path not configured",
            error_code="WINDMILL_CONFIG_INVALID",
        )

    path_seg = _script_path_url_segment(cfg.script_path)
    if wait:
        url = (
            f"{cfg.base_url}/api/w/{quote(cfg.workspace, safe='')}"
            f"/jobs/run_wait_result/p/{path_seg}"
        )
        timeout = cfg.wait_timeout_s
    else:
        url = (
            f"{cfg.base_url}/api/w/{quote(cfg.workspace, safe='')}"
            f"/jobs/run/p/{path_seg}"
        )
        timeout = cfg.timeout_s

    logger.info(
        "windmill_run_script workspace=%s script=%s wait=%s",
        cfg.workspace,
        cfg.script_path,
        wait,
        extra={
            "event": "automation.windmill.run",
            "service": "automation",
            "workspace": cfg.workspace,
            "script_path": cfg.script_path,
            "wait": wait,
        },
    )

    status, body = _post_json(url, token=cfg.token, body=args, timeout_s=timeout)
    if wait:
        try:
            result = json.loads(body) if body else None
        except json.JSONDecodeError as exc:
            raise WindmillClientError(
                "Windmill wait result was not JSON",
                status_code=status,
                error_code="WINDMILL_BAD_RESULT",
            ) from exc
        return {
            "workspace": cfg.workspace,
            "script_path": cfg.script_path,
            "wait": True,
            "http_status": status,
            "result": result,
        }

    job_id = (body or "").strip().strip('"')
    if not job_id:
        raise WindmillClientError(
            "Windmill run returned empty job id",
            status_code=status,
            error_code="WINDMILL_EMPTY_JOB_ID",
        )
    return {
        "workspace": cfg.workspace,
        "script_path": cfg.script_path,
        "wait": False,
        "http_status": status,
        "job_id": job_id,
    }
