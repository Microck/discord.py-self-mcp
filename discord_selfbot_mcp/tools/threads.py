import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

@registry.register(
    name="create_thread",
    description="Create a new thread",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "name": {"type": "string"},
            "message_id": {"type": "string", "description": "Optional message to start thread from"}
        },
        "required": ["channel_id", "name"]
    }
)
async def create_thread(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        name = arguments["name"]
        message_id = arguments.get("message_id")
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        
        message = None
        if message_id:
            message = await channel.fetch_message(int(message_id))
            
        thread = await channel.create_thread(name=name, message=message)
        return [TextContent(type="text", text=f"Created thread {thread.name} ({thread.id})")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating thread: {str(e)}")]

@registry.register(
    name="archive_thread",
    description="Archive or unarchive a thread",
    input_schema={
        "type": "object",
        "properties": {
            "thread_id": {"type": "string"},
            "archived": {"type": "boolean"}
        },
        "required": ["thread_id", "archived"]
    }
)
async def archive_thread(arguments: dict):
    try:
        thread_id = int(arguments["thread_id"])
        archived = arguments["archived"]
        
        thread = client.get_channel(thread_id) or await client.fetch_channel(thread_id)
        if not isinstance(thread, discord.Thread):
            return [TextContent(type="text", text="Channel is not a thread")]
            
        await thread.edit(archived=archived)
        return [TextContent(type="text", text=f"Set thread archived={archived}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error editing thread: {str(e)}")]
