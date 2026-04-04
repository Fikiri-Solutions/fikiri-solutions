"""core.flask_secret — production parity with SECRET_KEY on Render."""


def test_production_prefers_flask_secret_key(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("FLASK_SECRET_KEY", "aaa")
    monkeypatch.setenv("SECRET_KEY", "bbb")
    from core.flask_secret import resolve_flask_secret_key

    assert resolve_flask_secret_key() == "aaa"


def test_production_falls_back_to_secret_key(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "from-render")
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    from core.flask_secret import resolve_flask_secret_key

    assert resolve_flask_secret_key() == "from-render"


def test_development_default(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    from core.flask_secret import resolve_flask_secret_key

    assert resolve_flask_secret_key() == "dev-secret-key"
