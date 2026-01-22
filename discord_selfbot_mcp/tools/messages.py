import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

@registry.register(
    name="send_message",
    description="Send a message to a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["channel_id", "content"],
    }
)
async def send_message(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        content = arguments["content"]
        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]
        
        if not channel:
             return [TextContent(type="text", text="Channel not found")]

        await channel.send(content)
        return [TextContent(type="text", text=f"Message sent to {channel_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error sending message: {str(e)}")]

@registry.register(
    name="read_messages",
    description="Read messages from a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": ["channel_id"],
    }
)
async def read_messages(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        limit = arguments.get("limit", 50)
        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        
        messages = []
        async for msg in channel.history(limit=limit):
            messages.append(f"{msg.author.name}: {msg.content}")
        
        return [TextContent(type="text", text="\n".join(reversed(messages)))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading messages: {str(e)}")]
