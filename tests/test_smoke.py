import config.settings as settings


def test_settings_load() -> None:
    assert settings.LLM_MODE in {"live", "cache_only", "record"}
    assert abs(sum(settings.CONFIDENCE_WEIGHTS.values()) - 1.0) < 1e-9
