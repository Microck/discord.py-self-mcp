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

@registry.register(
    name="search_messages",
    description="Search for messages in a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "query": {"type": "string", "description": "Text to search for (simple containment)"},
            "limit": {"type": "integer", "default": 50}
        },
        "required": ["channel_id", "query"]
    }
)
async def search_messages(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        query = arguments["query"].lower()
        limit = arguments.get("limit", 50)
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        
        messages = []
        # Basic filtering using history since standard search API is not always reliable in selfbots without indexing
        async for msg in channel.history(limit=limit * 2): # Fetch double to filter
            if query in msg.content.lower():
                messages.append(f"{msg.author.name}: {msg.content}")
                if len(messages) >= limit:
                    break
        
        if not messages:
            return [TextContent(type="text", text="No messages found matching query")]
            
        return [TextContent(type="text", text="\n".join(reversed(messages)))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error searching messages: {str(e)}")]

@registry.register(
    name="edit_message",
    description="Edit a message sent by the user",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["channel_id", "message_id", "content"]
    }
)
async def edit_message(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        content = arguments["content"]
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        
        if message.author.id != client.user.id:
            return [TextContent(type="text", text="Cannot edit messages from other users")]
            
        await message.edit(content=content)
        return [TextContent(type="text", text=f"Edited message {message_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error editing message: {str(e)}")]

@registry.register(
    name="delete_message",
    description="Delete a message",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"}
        },
        "required": ["channel_id", "message_id"]
    }
)
async def delete_message(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        
        await message.delete()
        return [TextContent(type="text", text=f"Deleted message {message_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting message: {str(e)}")]
