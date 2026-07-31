from app.core.config import Settings, get_settings


def test_default_cors_origins_include_vue():
    settings = get_settings()
    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins


def test_default_cors_origins_exclude_old_nextjs():
    settings = get_settings()
    assert "http://localhost:3000" not in settings.cors_origins
    assert "http://127.0.0.1:3000" not in settings.cors_origins


def test_ai_interpretation_is_opt_in_and_secret_is_redacted():
    disabled = Settings(_env_file=None, ai_interpretation_api_key="secret-value")
    assert disabled.ai_interpretation_configured is False
    assert "secret-value" not in repr(disabled)

    missing_key = Settings(_env_file=None, ai_interpretation_enabled=True)
    assert missing_key.ai_interpretation_configured is False

    fake = Settings(
        _env_file=None,
        ai_interpretation_enabled=True,
        ai_interpretation_provider="fake",
        ai_interpretation_model="deterministic-test",
    )
    assert fake.ai_interpretation_configured is True
