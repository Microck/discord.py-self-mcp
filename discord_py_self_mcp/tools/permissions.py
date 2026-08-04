import json

import discord
from mcp.types import TextContent

from ..bot import client
from ..tool_utils import apply_rate_limit
from .registry import registry
from .roles import _hierarchy_block, _parse_permissions


def _resolve_target(guild, target_id: str, target_type: str):
    """Return ``(target, error_text)`` for a role or member id."""
    if target_type == "role":
        target = guild.get_role(int(target_id))
    elif target_type == "member":
        target = guild.get_member(int(target_id))
    else:
        return None, f"Invalid target_type '{target_type}' — use 'role' or 'member'"

    if not target:
        return None, f"{target_type.capitalize()} {target_id} not found"
    return target, None


def _build_overwrite(arguments: dict):
    allow = _parse_permissions(arguments.get("allow"))
    deny = _parse_permissions(arguments.get("deny"))
    return discord.PermissionOverwrite.from_pair(
        allow if allow is not None else discord.Permissions.none(),
        deny if deny is not None else discord.Permissions.none(),
    )


def _overwrite_rows(channel) -> list[dict]:
    rows = []
    for target, overwrite in channel.overwrites.items():
        allow, deny = overwrite.pair()
        rows.append(
            {
                "target_id": str(target.id),
                "target_type": "role" if isinstance(target, discord.Role) else "member",
                "target_name": target.name,
                "allow": str(allow.value),
                "deny": str(deny.value),
                "allowed": sorted(name for name, value in allow if value),
                "denied": sorted(name for name, value in deny if value),
            }
        )
    return rows


@registry.register(
    name="set_role_permissions",
    description=(
        "Replace a role's guild-wide permission set. Accepts a bitfield string or a "
        "list of flag names like [\"manage_roles\", \"kick_members\"]."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "role_id": {"type": "string"},
            "permissions": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ]
            },
            "reason": {"type": "string"}
        },
        "required": ["guild_id", "role_id", "permissions"]
    }
)
async def set_role_permissions(arguments: dict):
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

        permissions = _parse_permissions(arguments["permissions"])

        kwargs = {"permissions": permissions}
        reason = arguments.get("reason")
        if reason:
            kwargs["reason"] = reason

        await apply_rate_limit("action")
        await role.edit(**kwargs)
        return [
            TextContent(
                type="text",
                text=f"Set permissions on role {role.name} to {permissions.value}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting role permissions: {str(e)}")]


@registry.register(
    name="get_channel_permissions",
    description="List the permission overwrites on a channel or category as JSON",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"}
        },
        "required": ["channel_id"]
    }
)
async def get_channel_permissions(arguments: dict):
    try:
        channel = client.get_channel(int(arguments["channel_id"]))
        if not channel:
            return [TextContent(type="text", text="Channel not found")]

        return [TextContent(type="text", text=json.dumps(_overwrite_rows(channel), indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting channel permissions: {str(e)}")]


@registry.register(
    name="set_channel_permissions",
    description=(
        "Set the permission overwrite for a role or member on one channel. "
        "allow/deny take a bitfield string or a list of flag names."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "target_id": {"type": "string"},
            "target_type": {"type": "string", "enum": ["role", "member"]},
            "allow": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ]
            },
            "deny": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ]
            },
            "reason": {"type": "string"}
        },
        "required": ["channel_id", "target_id", "target_type"]
    }
)
async def set_channel_permissions(arguments: dict):
    try:
        channel = client.get_channel(int(arguments["channel_id"]))
        if not channel:
            return [TextContent(type="text", text="Channel not found")]

        target, error = _resolve_target(
            channel.guild, arguments["target_id"], arguments["target_type"]
        )
        if error:
            return [TextContent(type="text", text=error)]

        overwrite = _build_overwrite(arguments)
        reason = arguments.get("reason")

        await apply_rate_limit("action")
        if reason:
            await channel.set_permissions(target, overwrite=overwrite, reason=reason)
        else:
            await channel.set_permissions(target, overwrite=overwrite)

        return [
            TextContent(
                type="text",
                text=f"Set permissions for {target.name} on #{channel.name}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting channel permissions: {str(e)}")]


@registry.register(
    name="patch_channel_permissions",
    description=(
        "Change individual permission flags on a channel overwrite and leave the rest "
        "of that overwrite alone. Prefer this over set_channel_permissions whenever an "
        "overwrite already exists — set_channel_permissions replaces the whole entry, "
        "so untouched flags would be lost."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "target_id": {"type": "string"},
            "target_type": {"type": "string", "enum": ["role", "member"]},
            "set": {
                "type": "object",
                "description": (
                    "Flag name to true (allow), false (deny) or null (inherit). "
                    "Only the flags listed here change."
                ),
                "additionalProperties": {"type": ["boolean", "null"]}
            },
            "reason": {"type": "string"}
        },
        "required": ["channel_id", "target_id", "target_type", "set"]
    }
)
async def patch_channel_permissions(arguments: dict):
    try:
        channel = client.get_channel(int(arguments["channel_id"]))
        if not channel:
            return [TextContent(type="text", text="Channel not found")]

        target, error = _resolve_target(
            channel.guild, arguments["target_id"], arguments["target_type"]
        )
        if error:
            return [TextContent(type="text", text=error)]

        changes = arguments.get("set") or {}
        if not changes:
            return [TextContent(type="text", text="Nothing to change — 'set' is empty")]

        valid = getattr(discord.PermissionOverwrite, "VALID_NAMES", None)
        unknown = [name for name in changes if valid and name not in valid]
        if unknown:
            return [
                TextContent(
                    type="text",
                    text=f"Unknown permission name(s): {', '.join(unknown)}",
                )
            ]

        overwrite = channel.overwrites.get(target) or discord.PermissionOverwrite()
        for name, value in changes.items():
            setattr(overwrite, name, value)

        reason = arguments.get("reason")

        await apply_rate_limit("action")
        if reason:
            await channel.set_permissions(target, overwrite=overwrite, reason=reason)
        else:
            await channel.set_permissions(target, overwrite=overwrite)

        summary = ", ".join(f"{name}={value}" for name, value in changes.items())
        return [
            TextContent(
                type="text",
                text=f"Patched {target.name} on #{channel.name}: {summary}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error patching channel permissions: {str(e)}")]


@registry.register(
    name="remove_channel_permissions",
    description="Clear a role's or member's permission overwrite on a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "target_id": {"type": "string"},
            "target_type": {"type": "string", "enum": ["role", "member"]},
            "reason": {"type": "string"}
        },
        "required": ["channel_id", "target_id", "target_type"]
    }
)
async def remove_channel_permissions(arguments: dict):
    try:
        channel = client.get_channel(int(arguments["channel_id"]))
        if not channel:
            return [TextContent(type="text", text="Channel not found")]

        target, error = _resolve_target(
            channel.guild, arguments["target_id"], arguments["target_type"]
        )
        if error:
            return [TextContent(type="text", text=error)]

        reason = arguments.get("reason")

        await apply_rate_limit("action")
        if reason:
            await channel.set_permissions(target, overwrite=None, reason=reason)
        else:
            await channel.set_permissions(target, overwrite=None)

        return [
            TextContent(
                type="text",
                text=f"Removed permission overwrite for {target.name} on #{channel.name}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error removing channel permissions: {str(e)}")]


@registry.register(
    name="set_category_permissions",
    description=(
        "Set a permission overwrite on a category. By default the same overwrite is "
        "pushed to every channel inside it — set sync_children to false to touch only "
        "the category."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "category_id": {"type": "string"},
            "target_id": {"type": "string"},
            "target_type": {"type": "string", "enum": ["role", "member"]},
            "allow": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ]
            },
            "deny": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ]
            },
            "sync_children": {"type": "boolean", "default": True},
            "reason": {"type": "string"}
        },
        "required": ["category_id", "target_id", "target_type"]
    }
)
async def set_category_permissions(arguments: dict):
    try:
        category = client.get_channel(int(arguments["category_id"]))
        if not category or not isinstance(category, discord.CategoryChannel):
            return [TextContent(type="text", text="Category not found")]

        target, error = _resolve_target(
            category.guild, arguments["target_id"], arguments["target_type"]
        )
        if error:
            return [TextContent(type="text", text=error)]

        overwrite = _build_overwrite(arguments)

        await apply_rate_limit("action")
        await category.set_permissions(target, overwrite=overwrite)

        synced = []
        if arguments.get("sync_children", True):
            for child in category.channels:
                await apply_rate_limit("action")
                await child.set_permissions(target, overwrite=overwrite)
                synced.append(child.name)

        text = f"Set permissions for {target.name} on category {category.name}"
        if synced:
            text += f" and synced {len(synced)} channel(s): {', '.join(synced)}"
        return [TextContent(type="text", text=text)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting category permissions: {str(e)}")]


@registry.register(
    name="inspect_effective_permissions",
    description=(
        "Show what a role or member can actually do: guild-wide permissions plus which "
        "channels they can and cannot see once overwrites are applied. Returns JSON."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "target_id": {"type": "string"},
            "target_type": {"type": "string", "enum": ["role", "member"]},
            "channel_limit": {
                "type": "integer",
                "default": 25,
                "description": "How many channel names to list per bucket"
            }
        },
        "required": ["guild_id", "target_id", "target_type"]
    }
)
async def inspect_effective_permissions(arguments: dict):
    try:
        guild = client.get_guild(int(arguments["guild_id"]))
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        target, error = _resolve_target(
            guild, arguments["target_id"], arguments["target_type"]
        )
        if error:
            return [TextContent(type="text", text=error)]

        limit = int(arguments.get("channel_limit", 25))

        guild_permissions = (
            target.permissions
            if isinstance(target, discord.Role)
            else target.guild_permissions
        )

        accessible = []
        hidden = []
        for channel in guild.channels:
            bucket = accessible if channel.permissions_for(target).view_channel else hidden
            bucket.append(channel.name)

        payload = {
            "target_id": str(target.id),
            "target_type": arguments["target_type"],
            "target_name": target.name,
            "guild_permissions": str(guild_permissions.value),
            "granted": sorted(name for name, value in guild_permissions if value),
            "is_administrator": guild_permissions.administrator,
            "accessible_channel_count": len(accessible),
            "hidden_channel_count": len(hidden),
            "accessible_channels": sorted(accessible)[:limit],
            "hidden_channels": sorted(hidden)[:limit],
        }
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error inspecting permissions: {str(e)}")]
