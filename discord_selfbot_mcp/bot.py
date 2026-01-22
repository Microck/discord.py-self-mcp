import os
import discord
from dotenv import load_dotenv

load_dotenv()

class SelfBot(discord.Client):
    def __init__(self):
        super().__init__()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

client = SelfBot()
