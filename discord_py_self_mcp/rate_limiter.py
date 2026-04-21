import os
import time
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass

from discord_py_self_mcp.logging_utils import log_to_stderr


@dataclass
class RateLimitConfig:
    """Configuration dataclass for rate limiting behaviour."""

    enabled: bool = False
    messages_per_minute: int = 10
    messages_per_second: int = 1
    actions_per_minute: int = 5
    cooldown_on_limit: int = 60


class RateLimiter:
    """Token-bucket rate limiter for Discord API actions."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize the rate limiter with an optional config."""
        self.config = config or self._load_from_env()

        self._message_timestamps: list = []
        self._action_timestamps: list = []
        self._cooldown_until: float = 0
        self._lock = asyncio.Lock()

        self._last_action_time: float = 0
        self._min_action_interval: float = 1.0

    @classmethod
    def _load_from_env(cls) -> RateLimitConfig:
        """Load rate limit configuration from environment variables."""
        return RateLimitConfig(
            enabled=os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true",
            messages_per_minute=int(os.getenv("RATE_LIMIT_MESSAGES_PER_MINUTE", "10")),
            messages_per_second=int(os.getenv("RATE_LIMIT_MESSAGES_PER_SECOND", "1")),
            actions_per_minute=int(os.getenv("RATE_LIMIT_ACTIONS_PER_MINUTE", "5")),
            cooldown_on_limit=int(os.getenv("RATE_LIMIT_COOLDOWN", "60")),
        )

    def is_enabled(self) -> bool:
        """Check whether rate limiting is active."""
        return self.config.enabled

    def get_cooldown_remaining(self) -> int:
        """Return seconds remaining in the current cooldown, or 0."""
        remaining = self._cooldown_until - time.time()
        return max(0, int(remaining))

    async def wait_if_needed(self, action_type: str = "message"):
        """Block until the action is allowed under the current rate limits."""
        if not self.is_enabled():
            return

        async with self._lock:
            now = time.time()

            if now < self._cooldown_until:
                wait_time = self._cooldown_until - now
                await asyncio.sleep(wait_time)
                now = time.time()

            if action_type == "message":
                self._clean_timestamps(self._message_timestamps, 60)
                self._clean_timestamps(self._message_timestamps, 1)

                msg_in_minute = len(
                    [t for t in self._message_timestamps if now - t < 60]
                )
                msg_in_second = len(
                    [t for t in self._message_timestamps if now - t < 1]
                )

                if msg_in_minute >= self.config.messages_per_minute:
                    self._trigger_cooldown(
                        f"Message rate limit reached ({self.config.messages_per_minute}/min)"
                    )
                    return

                if msg_in_second >= self.config.messages_per_second:
                    sleep_time = (
                        1.0 - (now - self._message_timestamps[-1])
                        if self._message_timestamps
                        else 1.0
                    )
                    await asyncio.sleep(sleep_time)
                    now = time.time()

                self._message_timestamps.append(now)

            elif action_type == "action":
                self._clean_timestamps(self._action_timestamps, 60)

                action_in_minute = len(
                    [t for t in self._action_timestamps if now - t < 60]
                )

                if action_in_minute >= self.config.actions_per_minute:
                    self._trigger_cooldown(
                        f"Action rate limit reached ({self.config.actions_per_minute}/min)"
                    )
                    return

                time_since_last = now - self._last_action_time
                if time_since_last < self._min_action_interval:
                    await asyncio.sleep(self._min_action_interval - time_since_last)
                    now = time.time()

                self._action_timestamps.append(now)
                self._last_action_time = now

    def _clean_timestamps(self, timestamps: list, window: int):
        now = time.time()
        timestamps[:] = [t for t in timestamps if now - t < window]

    def _trigger_cooldown(self, reason: str):
        self._cooldown_until = time.time() + self.config.cooldown_on_limit
        log_to_stderr(
            f"[RATE_LIMIT] Cooldown triggered: {reason}. Cooldown for {self.config.cooldown_on_limit}s"
        )

    def reset(self):
        """Clear all tracked timestamps and any active cooldown."""
        self._message_timestamps.clear()
        self._action_timestamps.clear()
        self._cooldown_until = 0

    def get_stats(self) -> Dict[str, Any]:
        """Return a dict of current rate-limiter statistics."""
        now = time.time()
        return {
            "enabled": self.is_enabled(),
            "cooldown_remaining": self.get_cooldown_remaining(),
            "messages_last_minute": len(
                [t for t in self._message_timestamps if now - t < 60]
            ),
            "actions_last_minute": len(
                [t for t in self._action_timestamps if now - t < 60]
            ),
            "config": {
                "messages_per_minute": self.config.messages_per_minute,
                "messages_per_second": self.config.messages_per_second,
                "actions_per_minute": self.config.actions_per_minute,
            },
        }


_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Return the global RateLimiter singleton, creating it if needed."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(config)
    return _global_rate_limiter
