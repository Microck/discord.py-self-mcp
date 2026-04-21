import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client
from ..tool_utils import apply_rate_limit

@registry.register(
    name="kick_member",
    description="Kick a member from a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "user_id": {"type": "string"},
            "reason": {"type": "string"}
        },
        "required": ["guild_id", "user_id"]
    }
)
async def kick_member(arguments: dict):
    """Kick a member from a guild."""
    try:
        guild_id = int(arguments["guild_id"])
        user_id = int(arguments["user_id"])
        reason = arguments.get("reason")
        
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]
            
        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        if not member:
            return [TextContent(type="text", text="Member not found")]

        await apply_rate_limit("action")
        await member.kick(reason=reason)
        return [TextContent(type="text", text=f"Kicked member {member.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error kicking member: {str(e)}")]

@registry.register(
    name="ban_member",
    description="Ban a member from a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "user_id": {"type": "string"},
            "reason": {"type": "string"},
            "delete_message_days": {"type": "integer", "default": 0}
        },
        "required": ["guild_id", "user_id"]
    }
)
async def ban_member(arguments: dict):
    """Ban a user from a guild, optionally deleting recent messages."""
    try:
        guild_id = int(arguments["guild_id"])
        user_id = int(arguments["user_id"])
        reason = arguments.get("reason")
        delete_days = arguments.get("delete_message_days", 0)
        
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]
            
        # Can ban user even if not in guild
        user = discord.Object(id=user_id)

        await apply_rate_limit("action")
        await guild.ban(user, reason=reason, delete_message_days=delete_days)
        return [TextContent(type="text", text=f"Banned user {user_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error banning member: {str(e)}")]

@registry.register(
    name="unban_member",
    description="Unban a user from a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "user_id": {"type": "string"},
            "reason": {"type": "string"}
        },
        "required": ["guild_id", "user_id"]
    }
)
async def unban_member(arguments: dict):
    """Ban a user from a guild, optionally deleting recent messages."""
    try:
        guild_id = int(arguments["guild_id"])
        user_id = int(arguments["user_id"])
        reason = arguments.get("reason")
        
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]
            
        user = discord.Object(id=user_id)

        await apply_rate_limit("action")
        await guild.unban(user, reason=reason)
        return [TextContent(type="text", text=f"Unbanned user {user_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error unbanning member: {str(e)}")]

@registry.register(
    name="add_role",
    description="Add a role to a member",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "user_id": {"type": "string"},
            "role_id": {"type": "string"}
        },
        "required": ["guild_id", "user_id", "role_id"]
    }
)
async def add_role(arguments: dict):
    """Assign a role to a guild member."""
    try:
        guild_id = int(arguments["guild_id"])
        user_id = int(arguments["user_id"])
        role_id = int(arguments["role_id"])
        
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        if not member:
            return [TextContent(type="text", text="Member not found")]

        role = guild.get_role(role_id)
        
        if not role:
            return [TextContent(type="text", text="Role not found")]

        await apply_rate_limit("action")
        await member.add_roles(role)
        return [TextContent(type="text", text=f"Added role {role.name} to {member.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error adding role: {str(e)}")]

@registry.register(
    name="remove_role",
    description="Remove a role from a member",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "user_id": {"type": "string"},
            "role_id": {"type": "string"}
        },
        "required": ["guild_id", "user_id", "role_id"]
    }
)
async def remove_role(arguments: dict):
    """Remove a role from a guild member."""
    try:
        guild_id = int(arguments["guild_id"])
        user_id = int(arguments["user_id"])
        role_id = int(arguments["role_id"])
        
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        if not member:
            return [TextContent(type="text", text="Member not found")]

        role = guild.get_role(role_id)
        
        if not role:
            return [TextContent(type="text", text="Role not found")]

        await apply_rate_limit("action")
        await member.remove_roles(role)
        return [TextContent(type="text", text=f"Removed role {role.name} from {member.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error removing role: {str(e)}")]
