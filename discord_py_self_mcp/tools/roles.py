import json

import discord
from mcp.types import TextContent

from ..bot import client
from ..tool_utils import apply_rate_limit
from .registry import registry


def _role_payload(role) -> dict:
    return {
        "id": str(role.id),
        "name": role.name,
        "color": f"#{role.color.value:06X}",
        "color_value": role.color.value,
        "hoist": role.hoist,
        "position": role.position,
        "permissions": str(role.permissions.value),
        "managed": role.managed,
        "mentionable": role.mentionable,
    }


def _parse_color(raw):
    """Accept ``"#5865F2"``/``"5865F2"``/``"0x5865F2"`` as hex, plain ints as decimal."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ValueError("color must be a hex string or an integer")
    if isinstance(raw, int):
        return discord.Color(raw)

    text = str(raw).strip().lstrip("#")
    if text.lower().startswith("0x"):
        text = text[2:]
    try:
        return discord.Color(int(text, 16))
    except ValueError:
        raise ValueError(f"Invalid color '{raw}'. Use a hex string like #5865F2.")


def _parse_permissions(raw):
    """Accept either a raw bitfield or a list of ``discord.Permissions`` flag names."""
    if raw is None:
        return None
    if isinstance(raw, list):
        # Permissions.update() drops unknown keys silently, so validate up front.
        valid_flags = getattr(discord.Permissions, "VALID_FLAGS", {})
        unknown = [name for name in raw if valid_flags and name not in valid_flags]
        if unknown:
            raise ValueError(
                f"Unknown permission name(s): {', '.join(unknown)}. "
                "Use names like manage_roles, send_messages, view_channel."
            )
        perms = discord.Permissions()
        perms.update(**{name: True for name in raw})
        return perms
    return discord.Permissions(int(raw))


def _hierarchy_block(guild, role) -> str | None:
    """Explain an unavoidable 403 before spending the request on it.

    Discord answers "role above yours" with a bare Forbidden, which reads like a
    bug. The position comparison is local and says exactly what is wrong.
    """
    me = getattr(guild, "me", None)
    if me is None:
        return None
    if getattr(guild, "owner_id", None) == getattr(me, "id", None):
        return None

    top_role = getattr(me, "top_role", None)
    if top_role is None:
        return None

    if role.position >= top_role.position:
        return (
            f"Role '{role.name}' (position {role.position}) is at or above your highest "
            f"role '{top_role.name}' (position {top_role.position}). Discord refuses "
            "edits to roles that are not below your own — ask for a higher role first."
        )
    return None


@registry.register(
    name="list_roles",
    description=(
        "List every role in a guild with id, name, color, position and permission "
        "bitfield. Returns JSON — use it to snapshot the current setup before "
        "reordering anything."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"}
        },
        "required": ["guild_id"]
    }
)
async def list_roles(arguments: dict):
    try:
        guild = client.get_guild(int(arguments["guild_id"]))
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
        payload = [_role_payload(role) for role in roles]
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing roles: {str(e)}")]


@registry.register(
    name="get_role",
    description="Get a single role's full details as JSON",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "role_id": {"type": "string"}
        },
        "required": ["guild_id", "role_id"]
    }
)
async def get_role(arguments: dict):
    try:
        guild = client.get_guild(int(arguments["guild_id"]))
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        role = guild.get_role(int(arguments["role_id"]))
        if not role:
            return [TextContent(type="text", text="Role not found")]

        return [TextContent(type="text", text=json.dumps(_role_payload(role), indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting role: {str(e)}")]


@registry.register(
    name="create_role",
    description="Create a role in a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "name": {"type": "string"},
            "color": {
                "anyOf": [{"type": "string"}, {"type": "integer"}],
                "description": "Hex string like #5865F2, or an integer color value"
            },
            "permissions": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ],
                "description": "Permission bitfield as a string, or a list of flag names like [\"manage_roles\"]"
            },
            "hoist": {"type": "boolean", "default": False},
            "mentionable": {"type": "boolean", "default": False},
            "reason": {"type": "string"}
        },
        "required": ["guild_id", "name"]
    }
)
async def create_role(arguments: dict):
    try:
        guild = client.get_guild(int(arguments["guild_id"]))
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        kwargs = {
            "name": arguments["name"],
            "hoist": arguments.get("hoist", False),
            "mentionable": arguments.get("mentionable", False),
        }

        color = _parse_color(arguments.get("color"))
        if color is not None:
            kwargs["color"] = color

        permissions = _parse_permissions(arguments.get("permissions"))
        if permissions is not None:
            kwargs["permissions"] = permissions

        reason = arguments.get("reason")
        if reason:
            kwargs["reason"] = reason

        await apply_rate_limit("action")
        role = await guild.create_role(**kwargs)
        return [
            TextContent(
                type="text",
                text=f"Created role {role.name} ({role.id}) at position {role.position}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating role: {str(e)}")]


@registry.register(
    name="edit_role",
    description=(
        "Edit a role's name, color, permissions, position, hoist or mentionable flag. "
        "Only the fields you pass are changed."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "role_id": {"type": "string"},
            "name": {"type": "string"},
            "color": {
                "anyOf": [{"type": "string"}, {"type": "integer"}],
                "description": "Hex string like #5865F2, or an integer color value"
            },
            "permissions": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ],
                "description": "Permission bitfield as a string, or a list of flag names. Replaces the whole set."
            },
            "position": {"type": "integer"},
            "hoist": {"type": "boolean"},
            "mentionable": {"type": "boolean"},
            "reason": {"type": "string"}
        },
        "required": ["guild_id", "role_id"]
    }
)
async def edit_role(arguments: dict):
    try:
        guild = client.get_guild(int(arguments["guild_id"]))
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        role = guild.get_role(int(arguments["role_id"]))
        if not role:
            return [TextContent(type="text", text="Role not found")]

        blocked = _hierarchy_block(guild, role)
        if blocked:
            return [TextContent(type="text", text=blocked)]

        kwargs = {}
        for field in ("name", "position", "hoist", "mentionable"):
            if arguments.get(field) is not None:
                kwargs[field] = arguments[field]

        color = _parse_color(arguments.get("color"))
        if color is not None:
            kwargs["color"] = color

        permissions = _parse_permissions(arguments.get("permissions"))
        if permissions is not None:
            kwargs["permissions"] = permissions

        if not kwargs:
            return [TextContent(type="text", text="Nothing to change — pass at least one field")]

        reason = arguments.get("reason")
        if reason:
            kwargs["reason"] = reason

        await apply_rate_limit("action")
        await role.edit(**kwargs)

        changed = ", ".join(sorted(field for field in kwargs if field != "reason"))
        return [TextContent(type="text", text=f"Edited role {role.name} ({changed})")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error editing role: {str(e)}")]


@registry.register(
    name="delete_role",
    description="Delete a role from a guild. This cannot be undone.",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "role_id": {"type": "string"},
            "reason": {"type": "string"}
        },
        "required": ["guild_id", "role_id"]
    }
)
async def delete_role(arguments: dict):
    try:
        guild = client.get_guild(int(arguments["guild_id"]))
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        role = guild.get_role(int(arguments["role_id"]))
        if not role:
            return [TextContent(type="text", text="Role not found")]

        blocked = _hierarchy_block(guild, role)
        if blocked:
            return [TextContent(type="text", text=blocked)]

        role_name = role.name
        reason = arguments.get("reason")

        await apply_rate_limit("action")
        if reason:
            await role.delete(reason=reason)
        else:
            await role.delete()
        return [TextContent(type="text", text=f"Deleted role {role_name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting role: {str(e)}")]


@registry.register(
    name="reorder_roles",
    description=(
        "Move several roles to new positions in one call. Position is guild-wide: "
        "higher number sits higher in the list. Snapshot with list_roles first."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "positions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string"},
                        "position": {"type": "integer"}
                    },
                    "required": ["role_id", "position"]
                }
            },
            "reason": {"type": "string"}
        },
        "required": ["guild_id", "positions"]
    }
)
async def reorder_roles(arguments: dict):
    try:
        guild = client.get_guild(int(arguments["guild_id"]))
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        entries = arguments.get("positions") or []
        if not entries:
            return [TextContent(type="text", text="No positions given")]

        resolved = {}
        for entry in entries:
            role = guild.get_role(int(entry["role_id"]))
            if not role:
                return [TextContent(type="text", text=f"Role {entry['role_id']} not found")]

            blocked = _hierarchy_block(guild, role)
            if blocked:
                return [TextContent(type="text", text=blocked)]

            resolved[role] = int(entry["position"])

        reason = arguments.get("reason")

        await apply_rate_limit("action")
        if hasattr(guild, "edit_role_positions"):
            await guild.edit_role_positions(positions=resolved, reason=reason)
        else:
            # Older discord.py-self builds have no bulk endpoint wrapper.
            for role, position in resolved.items():
                await role.edit(position=position)

        moved = ", ".join(f"{role.name}->{position}" for role, position in resolved.items())
        return [TextContent(type="text", text=f"Reordered {len(resolved)} role(s): {moved}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error reordering roles: {str(e)}")]
