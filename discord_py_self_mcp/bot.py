import discord
import inspect
import importlib
import sys
from typing import Dict, Any
from google.protobuf import json_format
from dotenv import load_dotenv
from discord_py_self_mcp.captcha.solver import HCaptchaSolver
from discord_py_self_mcp.rate_limiter import (
    RateLimiter,
)
from discord_py_self_mcp.logging_utils import log_to_stderr

load_dotenv()

if (
    "including_default_value_fields"
    not in inspect.signature(json_format.MessageToDict).parameters
):

    def _message_to_dict_compat(message, **kwargs):
        if "including_default_value_fields" in kwargs:
            kwargs["always_print_fields_with_no_presence"] = kwargs.pop(
                "including_default_value_fields"
            )
        return json_format.MessageToDict(message, **kwargs)

    discord_settings = importlib.import_module("discord.settings")
    setattr(discord_settings, "MessageToDict", _message_to_dict_compat)


rate_limiter = None


def init_rate_limiter():
    global rate_limiter
    rate_limiter = RateLimiter()
    if rate_limiter.is_enabled():
        log_to_stderr(
            "[RATE_LIMIT] Enabled with config: "
            f"{rate_limiter.config.messages_per_minute} msg/min, "
            f"{rate_limiter.config.actions_per_minute} actions/min"
        )
    return rate_limiter


captcha_solver = None


class SelfBot(discord.Client):
    def __init__(self):
        init_rate_limiter()
        super().__init__()

    async def on_ready(self):
        user_id = self.user.id if self.user else "unknown"
        log_to_stderr(f"[READY] Logged in as {self.user} (ID: {user_id})")
        log_to_stderr(f"[READY] Guilds: {len(self.guilds)}")
        log_to_stderr(f"[READY] Private channels: {len(self.private_channels)}")

        if rate_limiter and rate_limiter.is_enabled():
            log_to_stderr(f"[RATE_LIMIT] Active - {rate_limiter.get_stats()}")

    async def on_connect(self):
        log_to_stderr("[CONNECT] Connected to Discord gateway")

    async def on_disconnect(self):
        log_to_stderr("[DISCONNECT] Disconnected from Discord gateway")

    async def on_error(self, event, *args, **kwargs):
        exc_type, exc_value, _ = sys.exc_info()
        if exc_type and exc_value:
            log_to_stderr(
                f"[ERROR] Event: {event}, Exception: {exc_type.__name__}: {exc_value}"
            )
            return
        log_to_stderr(f"[ERROR] Event: {event}")

    async def on_resumed(self):
        log_to_stderr("[RESUMED] Session resumed")

    async def on_captcha(self, data: Dict[str, Any]) -> str:
        return await solve_captcha()


async def solve_captcha() -> str:
    global captcha_solver
    log_to_stderr("[CAPTCHA] Triggered")

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise Exception(
            "Cannot solve CAPTCHA: GEMINI_API_KEY is not set. Set it in your MCP client environment config."
        )

    if captcha_solver is None:
        captcha_solver = HCaptchaSolver(
            sitekey="a9b5fb07-92ff-493f-86fe-352a2803b3df",
            host="discord.com",
            debug=True,
            proxy=os.getenv("CAPTCHA_PROXY"),
            gemini_api_key=gemini_api_key,
        )

    try:
        result = await captcha_solver.solve()
    finally:
        if captcha_solver is not None:
            await captcha_solver.close()
            captcha_solver = None

    if result.get("success"):
        log_to_stderr("[CAPTCHA] Solved successfully")
        return result["token"]

    error_text = result.get("error") or "unknown error"
    log_to_stderr(f"[CAPTCHA] Failed: {error_text}")
    raise Exception(f"Captcha solve failed: {error_text}")


client = SelfBot()
