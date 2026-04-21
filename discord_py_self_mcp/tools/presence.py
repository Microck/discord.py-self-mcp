import discord
from mcp.types import TextContent

from ..bot import client
from ..tool_utils import apply_rate_limit
from .registry import registry

@registry.register(
    name="set_status",
    description="Set user status (online, idle, dnd, invisible)",
    input_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["online", "idle", "dnd", "invisible"]}
        },
        "required": ["status"]
    }
)
async def set_status(arguments: dict):
    """Set the self-bot presence status."""
    try:
        status_str = arguments["status"]
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        
        await apply_rate_limit("action")
        await client.change_presence(status=status_map[status_str])
        return [TextContent(type="text", text=f"Status set to {status_str}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting status: {str(e)}")]

@registry.register(
    name="set_activity",
    description="Set user activity (playing, watching, listening, competing)",
    input_schema={
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["playing", "watching", "listening", "competing"]},
            "name": {"type": "string"}
        },
        "required": ["type", "name"]
    }
)
async def set_activity(arguments: dict):
    """Set the self-bot activity (playing, watching, listening, competing)."""
    try:
        activity_type = arguments["type"]
        name = arguments["name"]
        
        type_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing
        }
        
        activity = discord.Activity(type=type_map[activity_type], name=name)
        await apply_rate_limit("action")
        await client.change_presence(activity=activity)
        return [TextContent(type="text", text=f"Activity set to {activity_type} {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting activity: {str(e)}")]
