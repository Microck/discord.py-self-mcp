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

@registry.register(
    name="read_thread_messages",
    description="Read messages from a thread",
    input_schema={
        "type": "object",
        "properties": {
            "thread_id": {"type": "string"},
            "limit": {"type": "integer", "default": 50}
        },
        "required": ["thread_id"]
    }
)
async def read_thread_messages(arguments: dict):
    try:
        thread_id = int(arguments["thread_id"])
        limit = arguments.get("limit", 50)
        
        thread = client.get_channel(thread_id)
        if not thread:
            try:
                thread = await client.fetch_channel(thread_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Thread not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to thread")]
        
        if not thread:
            return [TextContent(type="text", text="Thread not found")]
        if not isinstance(thread, discord.Thread):
            return [TextContent(type="text", text=f"Channel {thread_id} is not a thread (type: {type(thread).__name__})")]
        
        messages = []
        async for msg in thread.history(limit=limit):
            messages.append(f"{msg.author.name}: {msg.content}")
        
        if not messages:
            return [TextContent(type="text", text="No messages found in thread")]
        
        return [TextContent(type="text", text="\n".join(reversed(messages)))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading thread messages: {str(e)}")]

@registry.register(
    name="list_active_threads",
    description="List all active threads in a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"}
        },
        "required": ["channel_id"]
    }
)
async def list_active_threads(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        
        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]
        
        if not hasattr(channel, 'threads'):
            return [TextContent(type="text", text=f"Channel type {type(channel).__name__} does not support threads")]
        
        threads = []
        for thread in channel.threads:
            threads.append(f"{thread.name} (ID: {thread.id}, Archived: {thread.archived})")
        
        if not threads:
            return [TextContent(type="text", text="No active threads found in this channel")]
        
        return [TextContent(type="text", text=f"Active threads ({len(threads)}):\n" + "\n".join(threads))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing threads: {str(e)}")]

@registry.register(
    name="send_thread_message",
    description="Send a message to a thread",
    input_schema={
        "type": "object",
        "properties": {
            "thread_id": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["thread_id", "content"]
    }
)
async def send_thread_message(arguments: dict):
    try:
        thread_id = int(arguments["thread_id"])
        content = arguments["content"]
        
        thread = client.get_channel(thread_id)
        if not thread:
            try:
                thread = await client.fetch_channel(thread_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Thread not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to thread")]
        
        if not isinstance(thread, discord.Thread):
            return [TextContent(type="text", text=f"Channel {thread_id} is not a thread")]
        
        message = await thread.send(content)
        return [TextContent(type="text", text=f"Message sent to thread (message_id={message.id})")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error sending message to thread: {str(e)}")]
