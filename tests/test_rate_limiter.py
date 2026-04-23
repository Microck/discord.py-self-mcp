import pytest

from discord_py_self_mcp.rate_limiter import RateLimitConfig, RateLimiter


class FakeClock:
    def __init__(self, now: float):
        self.now = now

    def time(self) -> float:
        return self.now


@pytest.mark.asyncio
async def test_wait_if_needed_preserves_minute_window_before_cooldown(monkeypatch):
    limiter = RateLimiter(
        RateLimitConfig(
            enabled=True,
            messages_per_minute=2,
            messages_per_second=5,
            actions_per_minute=5,
            cooldown_on_limit=60,
        )
    )
    limiter._message_timestamps = [0.8, 1.4]
    clock = FakeClock(1.5)
    sleeps: list[float] = []

    async def fake_sleep(delay: float):
        sleeps.append(delay)
        clock.now += delay

    monkeypatch.setattr("discord_py_self_mcp.rate_limiter.time.time", clock.time)
    monkeypatch.setattr("discord_py_self_mcp.rate_limiter.asyncio.sleep", fake_sleep)

    await limiter.wait_if_needed("message")

    assert sleeps == [60]
    assert limiter._message_timestamps[-1] == pytest.approx(61.5)


def test_load_from_env_enables_rate_limiting_by_default(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)

    config = RateLimiter._load_from_env()

    assert config.enabled is True


def test_get_stats_drops_stale_timestamps(monkeypatch):
    limiter = RateLimiter(RateLimitConfig(enabled=True))
    limiter._message_timestamps = [0.0, 61.0]
    limiter._action_timestamps = [10.0, 61.0]
    clock = FakeClock(70.0)

    monkeypatch.setattr("discord_py_self_mcp.rate_limiter.time.time", clock.time)

    stats = limiter.get_stats()

    assert stats["messages_last_minute"] == 1
    assert stats["actions_last_minute"] == 1
