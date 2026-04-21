from mcp.types import TextContent

from ..bot import client
from ..tool_utils import apply_rate_limit
from .registry import registry

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
    """Add an emoji reaction to a message."""
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        emoji = arguments["emoji"]
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)

        await apply_rate_limit("action")
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
    """Remove an emoji reaction from a message."""
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        emoji = arguments["emoji"]
        user_id = arguments.get("user_id")
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)

        if user_id:
            user = await client.fetch_user(int(user_id))
            await apply_rate_limit("action")
            await message.remove_reaction(emoji, user)
            return [TextContent(type="text", text=f"Removed reaction {emoji} from {user.name}")]
        else:
            await apply_rate_limit("action")
            await message.remove_reaction(emoji, client.user)
            return [TextContent(type="text", text=f"Removed own reaction {emoji}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error removing reaction: {str(e)}")]
