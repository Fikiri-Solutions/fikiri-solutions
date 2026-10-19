"""Guards for nightly QA and load-test workflow contracts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ci_does_not_pull_redis_from_public_ecr():
    offenders = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = _read(path)
        if "public.ecr.aws/docker/library/redis" in text:
            offenders.append(path.name)
    assert offenders == []


def test_redis_jobs_install_local_redis():
    for name in ("testing.yml", "smoke-test.yml", "ci-cd.yml"):
        text = _read(WORKFLOWS / name)
        assert "redis-server" in text, name


def test_nightly_runs_focused_integration_tests_against_localhost():
    text = _read(WORKFLOWS / "testing.yml")
    assert '("RUN_INTEGRATION_TESTS", "1")' in text
    assert '("INTEGRATION_BACKEND_URL", "http://127.0.0.1:5000")' in text
    assert '("FLASK_ENV", "development")' in text
    assert "did not pass any tests" in text
    assert "secrets.PERF_API_BASE_URL" not in text
    assert "k6 run" not in text
    assert "/src/main.tsx" in text


def test_k6_does_not_default_to_the_production_site():
    text = _read(ROOT / "scripts" / "k6-performance-test.js")
    assert "https://www.fikirisolutions.com" not in text
    assert "const FRONTEND_URL = __ENV.FRONTEND_URL || '';" in text
    assert "if (FRONTEND_URL)" in text


def test_dev_server_can_resolve_pwa_virtual_module():
    vite = _read(ROOT / "frontend" / "vite.config.mts")
    pwa = _read(ROOT / "frontend" / "src" / "config" / "pwa.ts")
    main = _read(ROOT / "frontend" / "src" / "main.tsx")
    assert "mode === 'production' ? [pwaConfig]" not in vite
    assert "mode === 'test' ? [] : [pwaConfig]" in vite
    assert "enabled: false" in pwa
    assert "virtual:pwa-register" in main


def test_legacy_integration_suite_is_not_enabled_by_nightly_flag(monkeypatch):
    monkeypatch.setenv("RUN_INTEGRATION_TESTS", "1")
    monkeypatch.delenv("RUN_LEGACY_INTEGRATION_TESTS", raising=False)
    from tests.integration.test_integration import _integration_enabled

    assert _integration_enabled() is False
