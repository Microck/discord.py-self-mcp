import os
import discord
import asyncio
from dotenv import load_dotenv
from .captcha.solver import HCaptchaSolver

load_dotenv()

async def captcha_handler(captcha_url: str, client: discord.Client):
    print(f"[CAPTCHA] Triggered: {captcha_url}")
    try:
        # Extract sitekey from URL if possible, or use default logic
        # discord.py-self passes the captcha URL (usually https://discord.com/...)
        # We need to solve it.
        # But HCaptchaSolver expects sitekey.
        # Captcha URL usually contains sitekey? No, usually it's just a verification page.
        # Actually, discord.py-self's captcha_handler receives (captcha_url, client) or just (captcha_url).
        # Let's check dolfies docs or source.
        # It seems the handler receives an `Exception` or `data` in some versions.
        # BUT, the most common pattern for selfbots is to intercept requests.
        # discord.py-self 2.0 handles this internally if we provide a solver?
        # No, we usually need to handle the 400 Bad Request manually if not using built-in.
        
        # However, if we assume the user might get a captcha, we can try to solve it.
        # Let's assume sitekey is the standard Discord one: a9b5fb07-92ff-493f-86fe-352a2803b3df
        
        sitekey = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
        solver = HCaptchaSolver(
            sitekey=sitekey,
            host="discord.com",
            debug=True,
            proxy=os.getenv("CAPTCHA_PROXY") # Optional proxy
        )
        
        result = await solver.solve()
        if result.get('success'):
            print(f"[CAPTCHA] Solved: {result['token'][:20]}...")
            return result['token']
        else:
            print(f"[CAPTCHA] Failed: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"[CAPTCHA] Error: {e}")
        return None

class SelfBot(discord.Client):
    def __init__(self):
        super().__init__(captcha_handler=captcha_handler)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

client = SelfBot()
