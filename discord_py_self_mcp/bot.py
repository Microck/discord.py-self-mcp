import os
import discord
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .captcha.solver import HCaptchaSolver

load_dotenv()

async def captcha_handler(captcha_required, client: discord.Client) -> str:
    print(f"[CAPTCHA] Triggered")
    try:
        sitekey = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
        solver = HCaptchaSolver(
            sitekey=sitekey,
            host="discord.com",
            debug=True,
            proxy=os.getenv("CAPTCHA_PROXY")
        )
        result = await solver.solve()
        if result.get('success'):
            print(f"[CAPTCHA] Solved: {result['token'][:20]}...")
            return result['token']
        else:
            print(f"[CAPTCHA] Failed: {result.get('error')}")
            raise Exception(f"Captcha solve failed: {result.get('error')}")
    except Exception as e:
        print(f"[CAPTCHA] Error: {e}")
        raise

class SelfBot(discord.Client):
    def __init__(self):
        super().__init__(captcha_handler=captcha_handler)

    async def on_ready(self):
        print(f'[READY] Logged in as {self.user} (ID: {self.user.id})')
        print(f'[READY] Guilds: {len(self.guilds)}')
        print(f'[READY] Private channels: {len(self.private_channels)}')

    async def on_connect(self):
        print('[CONNECT] Connected to Discord gateway')

    async def on_disconnect(self):
        print('[DISCONNECT] Disconnected from Discord gateway')

    async def on_error(self, event, *args, **kwargs):
        if isinstance(event, Exception):
            print(f'[ERROR] {type(event).__name__}: {event}')
        else:
            print(f'[ERROR] Event: {event}')

    async def on_resumed(self):
        print('[RESUMED] Session resumed')

client = SelfBot()
