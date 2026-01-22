import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

@registry.register(
    name="create_channel",
    description="Create a new channel in a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["text", "voice"], "default": "text"},
            "category_id": {"type": "string", "description": "Optional category ID"}
        },
        "required": ["guild_id", "name"]
    }
)
async def create_channel(arguments: dict):
    try:
        guild_id = int(arguments["guild_id"])
        name = arguments["name"]
        channel_type = arguments.get("type", "text")
        category_id = arguments.get("category_id")

        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        category = None
        if category_id:
            category = guild.get_channel(int(category_id))

        if channel_type == "text":
            channel = await guild.create_text_channel(name, category=category)
        elif channel_type == "voice":
            channel = await guild.create_voice_channel(name, category=category)
        else:
            return [TextContent(type="text", text="Invalid channel type")]

        return [TextContent(type="text", text=f"Created channel {channel.name} ({channel.id})")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating channel: {str(e)}")]

@registry.register(
    name="delete_channel",
    description="Delete a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"}
        },
        "required": ["channel_id"]
    }
)
async def delete_channel(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        channel = client.get_channel(channel_id)
        if not channel:
             return [TextContent(type="text", text="Channel not found")]
        
        await channel.delete()
        return [TextContent(type="text", text=f"Deleted channel {channel.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting channel: {str(e)}")]

@registry.register(
    name="list_channels",
    description="List all channels in a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"}
        },
        "required": ["guild_id"]
    }
)
async def list_channels(arguments: dict):
    try:
        guild_id = int(arguments["guild_id"])
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]
        
        channels = []
        for channel in guild.channels:
            channels.append(f"{channel.name} ({channel.id}) - {channel.type}")
            
        return [TextContent(type="text", text="\n".join(channels))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing channels: {str(e)}")]
