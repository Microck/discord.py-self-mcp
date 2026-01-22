import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

@registry.register(
    name="list_guilds",
    description="List all guilds the user is in",
    input_schema={
        "type": "object",
        "properties": {},
    }
)
async def list_guilds(arguments: dict):
    if not client.is_ready():
        return [TextContent(type="text", text="Bot is not ready yet")]
    
    guilds = [f"{g.name} ({g.id})" for g in client.guilds]
    return [TextContent(type="text", text="\n".join(guilds))]

@registry.register(
    name="get_user_info",
    description="Get information about the current user",
    input_schema={
        "type": "object",
        "properties": {},
    }
)
async def get_user_info(arguments: dict):
    if not client.is_ready():
        return [TextContent(type="text", text="Bot is not ready yet")]
    
    user = client.user
    return [TextContent(type="text", text=f"User: {user.name}#{user.discriminator} ({user.id})")]
