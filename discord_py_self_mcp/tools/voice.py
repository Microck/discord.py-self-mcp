import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client
from ..tool_utils import apply_rate_limit

@registry.register(
    name="join_voice_channel",
    description="Join a voice channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"}
        },
        "required": ["channel_id"]
    }
)
async def join_voice_channel(arguments: dict):
    """Connect to a voice channel."""
    try:
        channel_id = int(arguments["channel_id"])
        channel = client.get_channel(channel_id)
        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        
        if not isinstance(channel, discord.VoiceChannel):
             return [TextContent(type="text", text="Channel is not a voice channel")]

        await apply_rate_limit("action")
        await channel.connect()
        return [TextContent(type="text", text=f"Joined voice channel {channel.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error joining voice channel: {str(e)}")]

@registry.register(
    name="leave_voice_channel",
    description="Leave the voice channel in a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"}
        },
        "required": ["guild_id"]
    }
)
async def leave_voice_channel(arguments: dict):
    """Disconnect from the active voice channel in a guild."""
    try:
        guild_id = int(arguments["guild_id"])
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        if guild.voice_client:
            await apply_rate_limit("action")
            await guild.voice_client.disconnect()
            return [TextContent(type="text", text=f"Left voice channel in {guild.name}")]
        else:
            return [TextContent(type="text", text="Not in a voice channel in this guild")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error leaving voice channel: {str(e)}")]
