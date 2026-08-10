from ai_platform.core.settings import LlmSettings


def test_settings_uses_empty_values_without_secret(monkeypatch) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = LlmSettings.from_environment()

    assert settings.model == ""
    assert settings.api_key is None
