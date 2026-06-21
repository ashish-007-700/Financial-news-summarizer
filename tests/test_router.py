from providers.exceptions import RateLimitError
from providers import router


def test_router_falls_back_after_rate_limit(monkeypatch):
    calls = []

    def primary(system, prompt, model, temperature):
        calls.append(("primary", model))
        raise RateLimitError("limit")

    def fallback(system, prompt, model, temperature):
        calls.append(("fallback", model))
        return '{"ok": true}'

    monkeypatch.setitem(router.PROVIDERS, "groq", primary)
    monkeypatch.setitem(router.PROVIDERS, "nvidia", fallback)
    monkeypatch.setitem(router.MODEL_CHAIN, "test_quality", [("groq", "primary-model"), ("nvidia", "fallback-model")])

    result = router.call_llm_with_fallback(
        task_tier="test_quality",
        system="system",
        prompt="prompt",
        temperature=0,
    )

    assert result == '{"ok": true}'
    assert calls == [("primary", "primary-model"), ("fallback", "fallback-model")]


def test_router_rejects_non_zero_temperature():
    try:
        router.call_llm_with_fallback(
            task_tier="cheap",
            system="system",
            prompt="prompt",
            temperature=0.7,
        )
    except ValueError as exc:
        assert "temperature=0" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

