from app.core.config import get_settings


def test_default_cors_origins_include_vue():
    settings = get_settings()
    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins


def test_default_cors_origins_exclude_old_nextjs():
    settings = get_settings()
    assert "http://localhost:3000" not in settings.cors_origins
    assert "http://127.0.0.1:3000" not in settings.cors_origins
