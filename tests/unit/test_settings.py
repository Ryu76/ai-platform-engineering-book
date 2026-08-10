from ai_platform.core.settings import LlmSettings


def test_settings_uses_empty_values_without_secret(monkeypatch) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)

    settings = LlmSettings.from_environment()

    assert settings.model == ""
    assert settings.api_key is None
    assert settings.base_url == "https://api.openai.com/v1"
    assert settings.timeout_seconds == 30.0


def test_settings_rejects_invalid_timeout(monkeypatch) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "none")

    try:
        LlmSettings.from_environment()
    except ValueError as error:
        assert str(error) == "LLM_TIMEOUT_SECONDS must be a number"
    else:
        raise AssertionError("invalid timeout must be rejected")
