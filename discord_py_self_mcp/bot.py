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


async def captcha_handler(
    captcha_required, client: Optional[discord.Client] = None
) -> str:
    print(f"[CAPTCHA] Triggered")
    try:
        sitekey = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
        solver = HCaptchaSolver(
            sitekey=sitekey,
            host="discord.com",
            debug=True,
            proxy=os.getenv("CAPTCHA_PROXY"),
        )

        HCaptchaSolver.install_models(upgrade=True, clip=True)

        result = await solver.solve()
        if result.get("success"):
            print(f"[CAPTCHA] Solved: {result['token'][:20]}...")
            return result["token"]
        else:
            print(f"[CAPTCHA] Failed: {result.get('error')}")
            raise Exception(f"Captcha solve failed: {result.get('error')}")
    except Exception as e:
        print(f"[CAPTCHA] Error: {e}")
        raise


class CaptchaHandlerImpl(discord.CaptchaHandler):
    def __init__(self, client: Optional[discord.Client] = None):
        self.client = client

    async def fetch_token(
        self, data: Dict[str, Any], proxy: Optional[str] = None, proxy_auth=None
    ) -> str:
        return await captcha_handler(data, self.client)

    async def prefetch_token(
        self, proxy: Optional[str] = None, proxy_auth=None
    ) -> None:
        pass

    async def startup(self):
        pass


class SelfBot(discord.Client):
    def __init__(self):
        init_rate_limiter()
        captcha_handler_instance = CaptchaHandlerImpl(self)
        super().__init__(captcha_handler=captcha_handler_instance)

    async def on_ready(self):
        user_id = self.user.id if self.user else "unknown"
        print(f"[READY] Logged in as {self.user} (ID: {user_id})")
        print(f"[READY] Guilds: {len(self.guilds)}")
        print(f"[READY] Private channels: {len(self.private_channels)}")

        if rate_limiter and rate_limiter.is_enabled():
            print(f"[RATE_LIMIT] Active - {rate_limiter.get_stats()}")

    async def on_connect(self):
        print("[CONNECT] Connected to Discord gateway")

    async def on_disconnect(self):
        print("[DISCONNECT] Disconnected from Discord gateway")

    async def on_error(self, event, *args, **kwargs):
        if isinstance(event, Exception):
            print(f"[ERROR] {type(event).__name__}: {event}")
        else:
            print(f"[ERROR] Event: {event}")

    async def on_resumed(self):
        print("[RESUMED] Session resumed")


client = SelfBot()
