import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

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
    """Set the self-bot's presence status.

    This is an async MCP tool handler that updates the user's online
    status to one of ``online``, ``idle``, ``dnd``, or ``invisible``.

    Args:
        arguments: A dictionary containing ``status`` (str) — one of
            ``"online"``, ``"idle"``, ``"dnd"``, or ``"invisible"``.

    Returns:
        list[TextContent]: A single-element list with a confirmation or
            error message.
    """
    try:
        status_str = arguments["status"]
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        
        await client.change_presence(status=status_map[status_str])
        return [TextContent(type="text", text=f"Status set to {status_str}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting status: {str(e)}")]

@registry.register(
    name="set_activity",
    description="Set user activity (playing, watching, listening)",
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
    """Set the self-bot's activity (rich presence).

    This is an async MCP tool handler that updates the user's activity
    status (e.g. "Playing …", "Watching …").

    Args:
        arguments: A dictionary containing ``type`` (str — one of
            ``"playing"``, ``"watching"``, ``"listening"``, or
            ``"competing"``) and ``name`` (str).

    Returns:
        list[TextContent]: A single-element list with a confirmation or
            error message.
    """
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
        await client.change_presence(activity=activity)
        return [TextContent(type="text", text=f"Activity set to {activity_type} {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting activity: {str(e)}")]
