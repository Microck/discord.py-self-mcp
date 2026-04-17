import os
import asyncio
import discord
import inspect
import importlib
from typing import Dict, Any, Optional
from google.protobuf import json_format
from dotenv import load_dotenv
from discord_py_self_mcp.captcha.solver import HCaptchaSolver
from discord_py_self_mcp.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    get_rate_limiter,
)

load_dotenv()

if (
    "including_default_value_fields"
    not in inspect.signature(json_format.MessageToDict).parameters
):

    def _message_to_dict_compat(message, **kwargs):
        """Compatibility shim for google.protobuf.json_format.MessageToDict.

        Renames the deprecated ``including_default_value_fields`` keyword to
        ``always_print_fields_with_no_presence`` which is used by newer
        versions of protobuf.

        Args:
            message: The protobuf message to convert.
            **kwargs: Keyword arguments forwarded to ``MessageToDict``.

        Returns:
            dict: The serialized protobuf message as a dictionary.
        """
        if "including_default_value_fields" in kwargs:
            kwargs["always_print_fields_with_no_presence"] = kwargs.pop(
                "including_default_value_fields"
            )
        return json_format.MessageToDict(message, **kwargs)

    discord_settings = importlib.import_module("discord.settings")
    setattr(discord_settings, "MessageToDict", _message_to_dict_compat)


rate_limiter = None


def init_rate_limiter():
    """Initialize the global rate limiter from environment variables.

    Reads rate-limit configuration from the environment and stores the
    resulting :class:`RateLimiter` in the module-level ``rate_limiter``
    global.

    Returns:
        RateLimiter: The newly created rate limiter instance.
    """
    global rate_limiter
    config = RateLimitConfig(
        enabled=os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true",
        messages_per_minute=int(os.getenv("RATE_LIMIT_MESSAGES_PER_MINUTE", "10")),
        messages_per_second=int(os.getenv("RATE_LIMIT_MESSAGES_PER_SECOND", "1")),
        actions_per_minute=int(os.getenv("RATE_LIMIT_ACTIONS_PER_MINUTE", "5")),
        cooldown_on_limit=int(os.getenv("RATE_LIMIT_COOLDOWN", "60")),
        respect_global_delay=os.getenv("RATE_LIMIT_RESPECT_GLOBAL", "true").lower()
        == "true",
    )
    rate_limiter = RateLimiter(config)
    if config.enabled:
        print(
            f"[RATE_LIMIT] Enabled with config: {config.messages_per_minute} msg/min, {config.actions_per_minute} actions/min"
        )
    return rate_limiter


captcha_solver = None


class SelfBot(discord.Client):
    def __init__(self):
        """Initialize the SelfBot client and the rate limiter."""
        init_rate_limiter()
        super().__init__()

    async def on_ready(self):
        """Handle the Discord ``READY`` event.

        Logs the authenticated user, guild count, and private channel count.
        Also prints rate-limiter stats when enabled.
        """
        user_id = self.user.id if self.user else "unknown"
        print(f"[READY] Logged in as {self.user} (ID: {user_id})")
        print(f"[READY] Guilds: {len(self.guilds)}")
        print(f"[READY] Private channels: {len(self.private_channels)}")

        if rate_limiter and rate_limiter.is_enabled():
            print(f"[RATE_LIMIT] Active - {rate_limiter.get_stats()}")

    async def on_connect(self):
        """Handle the Discord ``CONNECT`` event.

        Logs that the gateway connection has been established.
        """
        print("[CONNECT] Connected to Discord gateway")

    async def on_disconnect(self):
        """Handle the Discord ``DISCONNECT`` event.

        Logs that the gateway connection was lost.
        """
        print("[DISCONNECT] Disconnected from Discord gateway")

    async def on_error(self, event, *args, **kwargs):
        """Handle an unhandled exception from a Discord event.

        Args:
            event: The event name or exception instance that caused the error.
            *args: Positional arguments from the original event handler.
            **kwargs: Keyword arguments from the original event handler.
        """
        if isinstance(event, Exception):
            print(f"[ERROR] {type(event).__name__}: {event}")
        else:
            print(f"[ERROR] Event: {event}")

    async def on_resumed(self):
        """Handle the Discord ``RESUMED`` event.

        Logs that a dropped session has been successfully resumed.
        """
        print("[RESUMED] Session resumed")

    async def on_captcha(self, data: Dict[str, Any]) -> str:
        """Handle a CAPTCHA challenge from Discord.

        This is called automatically by discord.py-self when a CAPTCHA is
        required during an API request.

        Args:
            data: The CAPTCHA challenge payload from Discord.

        Returns:
            str: The solved CAPTCHA token.
        """
        return await solve_captcha()


async def solve_captcha() -> str:
    """Solve an hCaptcha challenge using the Gemini-powered solver.

    Lazily initializes the :class:`HCaptchaSolver` on first invocation.
    Requires the ``GEMINI_API_KEY`` environment variable to be set.

    Returns:
        str: The solved hCaptcha token.

    Raises:
        Exception: If ``GEMINI_API_KEY`` is not set or the solve fails.
    """
    global captcha_solver
    print(f"[CAPTCHA] Triggered")

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise Exception("GEMINI_API_KEY not set - required for hCaptcha solving")

    if captcha_solver is None:
        captcha_solver = HCaptchaSolver(
            sitekey="a9b5fb07-92ff-493f-86fe-352a2803b3df",
            host="discord.com",
            debug=True,
            proxy=os.getenv("CAPTCHA_PROXY"),
            gemini_api_key=gemini_api_key,
        )

    result = await captcha_solver.solve()
    if result.get("success"):
        print(f"[CAPTCHA] Solved: {result['token'][:20]}...")
        return result["token"]
    else:
        print(f"[CAPTCHA] Failed: {result.get('error')}")
        raise Exception(f"Captcha solve failed: {result.get('error')}")


client = SelfBot()
