import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

@registry.register(
    name="add_reaction",
    description="Add a reaction to a message",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "emoji": {"type": "string", "description": "The emoji to react with (unicode or custom ID)"}
        },
        "required": ["channel_id", "message_id", "emoji"]
    }
)
async def add_reaction(arguments: dict):
    """Add a reaction emoji to a Discord message.

    This is an async MCP tool handler that resolves the target message and
    adds the specified emoji reaction.

    Args:
        arguments: A dictionary containing ``channel_id`` (str),
            ``message_id`` (str), and ``emoji`` (str — unicode emoji or
            custom emoji ID).

    Returns:
        list[TextContent]: A single-element list with a confirmation or
            error message.
    """
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        emoji = arguments["emoji"]
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        
        await message.add_reaction(emoji)
        return [TextContent(type="text", text=f"Added reaction {emoji} to message {message_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error adding reaction: {str(e)}")]

@registry.register(
    name="remove_reaction",
    description="Remove a reaction from a message",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "emoji": {"type": "string"},
            "user_id": {"type": "string", "description": "Optional: User ID to remove reaction from (default: self)"}
        },
        "required": ["channel_id", "message_id", "emoji"]
    }
)
async def remove_reaction(arguments: dict):
    """Remove a reaction emoji from a Discord message.

    This is an async MCP tool handler that removes the specified emoji
    reaction. When ``user_id`` is provided the reaction for that user is
    removed; otherwise the self-bot's own reaction is removed.

    Args:
        arguments: A dictionary containing ``channel_id`` (str),
            ``message_id`` (str), ``emoji`` (str), and optionally
            ``user_id`` (str).

    Returns:
        list[TextContent]: A single-element list with a confirmation or
            error message.
    """
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        emoji = arguments["emoji"]
        user_id = arguments.get("user_id")
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        
        if user_id:
            user = await client.fetch_user(int(user_id))
            await message.remove_reaction(emoji, user)
            return [TextContent(type="text", text=f"Removed reaction {emoji} from {user.name}")]
        else:
            await message.remove_reaction(emoji, client.user)
            return [TextContent(type="text", text=f"Removed own reaction {emoji}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error removing reaction: {str(e)}")]
