"""Guild-folder tools backed by Discord's preloaded user settings protobuf."""

import base64
import json
import secrets
from typing import Any

from discord.http import Route
from discord_protos import PreloadedUserSettings
from mcp.types import TextContent

from ..bot import client
from ..logging_utils import log_to_stderr
from ..tool_utils import NOT_READY_TEXT, apply_rate_limit
from .registry import registry


SETTINGS_ROUTE = "/users/@me/settings-proto/1"


def _text(value: str) -> list[TextContent]:
    return [TextContent(type="text", text=value)]


def _folder_id(folder) -> int | None:
    return folder.id.value if folder.HasField("id") else None


def _folder_name(folder) -> str | None:
    return folder.name.value if folder.HasField("name") else None


def _folder_color(folder) -> int | None:
    return folder.color.value if folder.HasField("color") else None


def _serialize_folders(settings: PreloadedUserSettings) -> list[dict[str, Any]]:
    guild_names = {str(guild.id): guild.name for guild in client.guilds}
    folders: list[dict[str, Any]] = []
    for folder in settings.guild_folders.folders:
        guild_ids = [str(guild_id) for guild_id in folder.guild_ids]
        row: dict[str, Any] = {
            "folder_id": str(_folder_id(folder)) if _folder_id(folder) is not None else None,
            "name": _folder_name(folder),
            "color": _folder_color(folder),
            "guild_ids": guild_ids,
            "guilds": [
                {"id": guild_id, "name": guild_names.get(guild_id)}
                for guild_id in guild_ids
            ],
        }
        folders.append(row)
    return folders


def _decode_settings(encoded_settings: object) -> PreloadedUserSettings:
    if not isinstance(encoded_settings, str) or not encoded_settings:
        raise ValueError("Discord returned an invalid settings payload")
    try:
        payload = base64.b64decode(encoded_settings, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Discord returned settings that are not valid base64") from exc
    try:
        return PreloadedUserSettings.FromString(payload)
    except Exception as exc:
        raise ValueError("Discord returned settings that could not be decoded") from exc


async def _get_settings() -> PreloadedUserSettings:
    response = await client.http.request(Route("GET", SETTINGS_ROUTE))
    if not isinstance(response, dict):
        raise ValueError("Discord returned an invalid settings response")
    return _decode_settings(response.get("settings"))


async def _save_settings(settings: PreloadedUserSettings) -> None:
    payload: dict[str, Any] = {
        "settings": base64.b64encode(settings.SerializeToString()).decode("ascii"),
    }
    if settings.HasField("versions"):
        payload["required_data_version"] = settings.versions.data_version

    log_to_stderr(
        "[FOLDERS] Saving guild-folder settings"
        + (f" at data_version={payload['required_data_version']}" if "required_data_version" in payload else "")
    )
    response = await client.http.request(Route("PATCH", SETTINGS_ROUTE), json=payload)
    if isinstance(response, dict) and response.get("out_of_date"):
        raise ValueError(
            "Folder layout changed on another Discord client. Read the folders again and retry."
        )


def _validate_snowflake(value: object, field_name: str) -> int:
    try:
        result = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a Discord ID") from exc
    if result <= 0:
        raise ValueError(f"{field_name} must be a positive Discord ID")
    return result


def _parse_color(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("color must be a hex color such as #5865F2 or an integer")
    if isinstance(value, int):
        color = value
    elif isinstance(value, str):
        candidate = value.strip()
        if candidate.startswith("#"):
            candidate = candidate[1:]
            try:
                color = int(candidate, 16)
            except ValueError as exc:
                raise ValueError("color must be a valid hex color") from exc
        else:
            try:
                color = int(candidate)
            except ValueError as exc:
                raise ValueError("color must be a hex color such as #5865F2 or an integer") from exc
    else:
        raise ValueError("color must be a hex color such as #5865F2 or an integer")
    if not 0 <= color <= 0xFFFFFF:
        raise ValueError("color must be between #000000 and #FFFFFF")
    return color


def _remove_guild_ids(settings: PreloadedUserSettings, guild_ids: set[int]) -> None:
    kept = []
    for folder in settings.guild_folders.folders:
        remaining = [guild_id for guild_id in folder.guild_ids if guild_id not in guild_ids]
        if not remaining:
            continue
        clone = type(folder)()
        clone.CopyFrom(folder)
        del clone.guild_ids[:]
        clone.guild_ids.extend(remaining)
        kept.append(clone)

    del settings.guild_folders.folders[:]
    for folder in kept:
        settings.guild_folders.folders.add().CopyFrom(folder)


def _new_folder_id(settings: PreloadedUserSettings) -> int:
    existing = {_folder_id(folder) for folder in settings.guild_folders.folders}
    while True:
        folder_id = secrets.randbelow((1 << 63) - 1) + 1
        if folder_id not in existing:
            return folder_id


def _find_folder(settings: PreloadedUserSettings, folder_id: int):
    for folder in settings.guild_folders.folders:
        if _folder_id(folder) == folder_id:
            return folder
    raise ValueError(f"Folder {folder_id} was not found")


def _append_ungrouped(settings: PreloadedUserSettings, guild_id: int) -> None:
    folder = settings.guild_folders.folders.add()
    folder.guild_ids.append(guild_id)


def _validate_guild_ids(value: object, field_name: str = "guild_ids") -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty array of Discord IDs")
    guild_ids = [_validate_snowflake(item, field_name) for item in value]
    if len(set(guild_ids)) != len(guild_ids):
        raise ValueError(f"{field_name} must not contain duplicates")
    return guild_ids


def _clone_folder(folder):
    clone = type(folder)()
    clone.CopyFrom(folder)
    return clone


def _folder_location(folder) -> str:
    folder_id = _folder_id(folder)
    if folder_id is None:
        return "ungrouped"
    return _folder_name(folder) or f"folder {folder_id}"


def _guild_locations(settings: PreloadedUserSettings) -> dict[int, str]:
    return {
        guild_id: _folder_location(folder)
        for folder in settings.guild_folders.folders
        for guild_id in folder.guild_ids
    }


def _apply_folder_layout(
    settings: PreloadedUserSettings, arguments: dict
) -> dict[str, Any]:
    """Apply a partial named-folder layout to an in-memory settings protobuf.

    Only guilds explicitly listed in ``folders`` or ``ungrouped_guild_ids`` move.
    All other servers remain where they are, while requested folders become the
    leading named folders in the requested order.
    """
    requested_folders = arguments.get("folders")
    if not isinstance(requested_folders, list) or not requested_folders:
        raise ValueError("folders must be a non-empty array")
    if len(requested_folders) > 100:
        raise ValueError("folders may contain at most 100 entries")

    original = [_clone_folder(folder) for folder in settings.guild_folders.folders]
    before = _guild_locations(settings)
    named_by_id = {
        folder_id: folder
        for folder in original
        if (folder_id := _folder_id(folder)) is not None
    }
    named_by_name: dict[str, list] = {}
    for folder in named_by_id.values():
        name = _folder_name(folder)
        if name:
            named_by_name.setdefault(name, []).append(folder)

    destinations: list[dict[str, Any]] = []
    moved_guild_ids: set[int] = set()
    destination_keys: set[tuple[str, object]] = set()
    planned_creations: list[str] = []
    planned_renames: list[dict[str, str]] = []
    planned_recolors: list[dict[str, int | None]] = []
    for index, entry in enumerate(requested_folders):
        if not isinstance(entry, dict):
            raise ValueError(f"folders[{index}] must be an object")
        name = str(entry.get("name", "")).strip()
        if not name:
            raise ValueError(f"folders[{index}].name must not be empty")
        guild_ids = _validate_guild_ids(entry.get("guild_ids"), f"folders[{index}].guild_ids")
        if moved_guild_ids.intersection(guild_ids):
            raise ValueError("A server may appear in only one destination folder")
        moved_guild_ids.update(guild_ids)

        folder = None
        raw_folder_id = entry.get("folder_id")
        if raw_folder_id is not None:
            folder_id = _validate_snowflake(raw_folder_id, f"folders[{index}].folder_id")
            folder = named_by_id.get(folder_id)
            if folder is None:
                raise ValueError(f"Folder {folder_id} was not found")
            key = ("id", folder_id)
        else:
            matching = named_by_name.get(name, [])
            if len(matching) > 1:
                raise ValueError(
                    f"More than one existing folder is named {name!r}; provide folder_id to disambiguate"
                )
            folder = matching[0] if matching else None
            key = ("id", _folder_id(folder)) if folder is not None else ("new", name)
        if key in destination_keys:
            raise ValueError("Each destination folder may be specified only once")
        destination_keys.add(key)

        color = _parse_color(entry["color"]) if "color" in entry else None
        if folder is None:
            planned_creations.append(name)
        else:
            old_name = _folder_name(folder)
            if old_name != name:
                planned_renames.append({"from": old_name or "", "to": name})
            if "color" in entry and _folder_color(folder) != color:
                planned_recolors.append({"name": name, "color": color})
        destinations.append(
            {"name": name, "guild_ids": guild_ids, "color": color, "existing": folder}
        )

    ungrouped = _validate_guild_ids(arguments.get("ungrouped_guild_ids"), "ungrouped_guild_ids") if arguments.get("ungrouped_guild_ids") is not None else []
    if moved_guild_ids.intersection(ungrouped):
        raise ValueError("A server may not be both grouped and ungrouped")
    moved_guild_ids.update(ungrouped)

    # Remove each explicitly moved server, preserving all unrelated entries.
    remaining = []
    for folder in original:
        clone = _clone_folder(folder)
        del clone.guild_ids[:]
        clone.guild_ids.extend(guild_id for guild_id in folder.guild_ids if guild_id not in moved_guild_ids)
        if clone.guild_ids:
            remaining.append(clone)
    remaining_by_id = {
        _folder_id(folder): folder
        for folder in remaining
        if _folder_id(folder) is not None
    }

    final_folders = []
    for destination in destinations:
        existing = destination["existing"]
        folder_id = _folder_id(existing) if existing is not None else None
        target = remaining_by_id.pop(folder_id, None) if folder_id is not None else None
        if target is None:
            target = (
                _clone_folder(existing)
                if existing is not None
                else PreloadedUserSettings.GuildFolder()
            )
            del target.guild_ids[:]
        target.guild_ids.extend(destination["guild_ids"])
        if folder_id is None:
            target.id.value = _new_folder_id(settings)
        target.name.value = destination["name"]
        if destination["color"] is not None:
            target.color.value = destination["color"]
        final_folders.append(target)

    target_ids = {
        _folder_id(destination["existing"])
        for destination in destinations
        if destination["existing"] is not None
    }
    for folder in remaining:
        if _folder_id(folder) not in target_ids:
            final_folders.append(folder)
    for guild_id in ungrouped:
        root = type(final_folders[0])()
        root.guild_ids.append(guild_id)
        final_folders.append(root)

    del settings.guild_folders.folders[:]
    for folder in final_folders:
        settings.guild_folders.folders.add().CopyFrom(folder)

    after = _guild_locations(settings)
    moves = [
        {"guild_id": str(guild_id), "from": before.get(guild_id, "unknown"), "to": after[guild_id]}
        for guild_id in sorted(moved_guild_ids)
        if before.get(guild_id) != after.get(guild_id)
    ]
    final_ids = {_folder_id(folder) for folder in settings.guild_folders.folders}
    deleted = [
        _folder_location(folder)
        for folder in original
        if _folder_id(folder) is not None and _folder_id(folder) not in final_ids
    ]
    return {
        "will_create": planned_creations,
        "will_rename": planned_renames,
        "will_recolor": planned_recolors,
        "will_move": moves,
        "will_delete_empty": deleted,
        "resulting_folders": _serialize_folders(settings),
    }


@registry.register(
    name="list_server_folders",
    description="List the current Discord server-folder layout, including ungrouped servers.",
    input_schema={"type": "object", "properties": {}},
)
async def list_server_folders(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        settings = await _get_settings()
        return _text(json.dumps({"folders": _serialize_folders(settings)}, indent=2))
    except Exception as exc:
        return _text(f"Error listing server folders: {exc}")


@registry.register(
    name="create_server_folder",
    description="Create a server folder and move the listed servers into it. Existing folders and other servers are preserved.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Folder name"},
            "guild_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Server IDs to place in the new folder",
            },
            "color": {
                "description": "Optional #RRGGBB color or integer color value",
                "anyOf": [{"type": "string"}, {"type": "integer"}],
            },
        },
        "required": ["name", "guild_ids"],
    },
)
async def create_server_folder(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        name = str(arguments.get("name", "")).strip()
        if not name:
            raise ValueError("name must not be empty")
        guild_ids = _validate_guild_ids(arguments.get("guild_ids"))
        color = _parse_color(arguments["color"]) if "color" in arguments else None

        settings = await _get_settings()
        _remove_guild_ids(settings, set(guild_ids))
        folder = settings.guild_folders.folders.add()
        folder.guild_ids.extend(guild_ids)
        folder_id = _new_folder_id(settings)
        folder.id.value = folder_id
        folder.name.value = name
        if color is not None:
            folder.color.value = color
        log_to_stderr(f"[FOLDERS] Creating folder name={name!r} servers={len(guild_ids)}")
        await apply_rate_limit("action")
        await _save_settings(settings)
        return _text(f"Created server folder {name!r} (id={folder_id}) with {len(guild_ids)} server(s)")
    except Exception as exc:
        return _text(f"Error creating server folder: {exc}")


@registry.register(
    name="move_server_to_folder",
    description="Move one server into a folder. Omit folder_id to make the server ungrouped.",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string", "description": "Server ID to move"},
            "folder_id": {
                "type": "string",
                "description": "Destination folder ID from list_server_folders; omit to ungroup the server",
            },
        },
        "required": ["guild_id"],
    },
)
async def move_server_to_folder(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        guild_id = _validate_snowflake(arguments.get("guild_id"), "guild_id")
        folder_id = (
            _validate_snowflake(arguments["folder_id"], "folder_id")
            if arguments.get("folder_id") is not None
            else None
        )
        settings = await _get_settings()
        destination = _find_folder(settings, folder_id) if folder_id is not None else None
        _remove_guild_ids(settings, {guild_id})
        if destination is not None:
            # Removing entries rebuilds the protobuf container, so resolve the
            # destination again before adding the server to it.
            _find_folder(settings, folder_id).guild_ids.append(guild_id)
            target = f"folder {folder_id}"
        else:
            _append_ungrouped(settings, guild_id)
            target = "the ungrouped sidebar"
        log_to_stderr(f"[FOLDERS] Moving guild={guild_id} to {target}")
        await apply_rate_limit("action")
        await _save_settings(settings)
        return _text(f"Moved server {guild_id} to {target}")
    except Exception as exc:
        return _text(f"Error moving server: {exc}")


@registry.register(
    name="rename_server_folder",
    description="Rename an existing Discord server folder.",
    input_schema={
        "type": "object",
        "properties": {
            "folder_id": {"type": "string"},
            "name": {"type": "string", "description": "New folder name"},
        },
        "required": ["folder_id", "name"],
    },
)
async def rename_server_folder(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        folder_id = _validate_snowflake(arguments.get("folder_id"), "folder_id")
        name = str(arguments.get("name", "")).strip()
        if not name:
            raise ValueError("name must not be empty")
        settings = await _get_settings()
        _find_folder(settings, folder_id).name.value = name
        log_to_stderr(f"[FOLDERS] Renaming folder={folder_id} name={name!r}")
        await apply_rate_limit("action")
        await _save_settings(settings)
        return _text(f"Renamed folder {folder_id} to {name!r}")
    except Exception as exc:
        return _text(f"Error renaming server folder: {exc}")


@registry.register(
    name="apply_server_folder_layout",
    description=(
        "Create or update multiple server folders in one settings write. Listed servers "
        "move to their named destinations; unlisted servers stay where they are. Set "
        "dry_run=true to inspect every planned change without saving."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "folders": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "folder_id": {"type": "string", "description": "Existing folder ID, when renaming or recoloring it"},
                        "name": {"type": "string"},
                        "color": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                        "guild_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name", "guild_ids"],
                },
            },
            "ungrouped_guild_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Servers to remove from folders and leave in the root sidebar",
            },
            "dry_run": {"type": "boolean", "default": False},
        },
        "required": ["folders"],
    },
)
async def apply_server_folder_layout(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        settings = await _get_settings()
        plan = _apply_folder_layout(settings, arguments)
        plan["dry_run"] = bool(arguments.get("dry_run", False))
        if arguments.get("dry_run", False):
            log_to_stderr(
                f"[FOLDERS] Dry run: create={len(plan['will_create'])} move={len(plan['will_move'])}"
            )
            return _text(json.dumps(plan, indent=2))

        log_to_stderr(
            f"[FOLDERS] Applying layout: create={len(plan['will_create'])} "
            f"rename={len(plan['will_rename'])} move={len(plan['will_move'])}"
        )
        await apply_rate_limit("action")
        await _save_settings(settings)
        return _text(json.dumps(plan, indent=2))
    except Exception as exc:
        return _text(f"Error applying server folder layout: {exc}")


@registry.register(
    name="reorder_server_folders",
    description=(
        "Reorder server folders. Pass folder_ids to reorder named folders while preserving "
        "ungrouped-server positions, or use the legacy complete folder_order form."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "folder_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Every named folder ID, in desired order",
            },
            "folder_order": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "folder_id": {"type": ["string", "null"]},
                        "guild_ids": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "description": "All entries from list_server_folders, in desired sidebar order",
            },
        },
        "anyOf": [{"required": ["folder_ids"]}, {"required": ["folder_order"]}],
    },
)
async def reorder_server_folders(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        settings = await _get_settings()
        current = list(settings.guild_folders.folders)

        folder_ids = arguments.get("folder_ids")
        if folder_ids is not None:
            if not isinstance(folder_ids, list):
                raise ValueError("folder_ids must be an array")
            requested_folder_ids = [_validate_snowflake(value, "folder_ids") for value in folder_ids]
            current_folder_ids = [
                _folder_id(folder) for folder in current if _folder_id(folder) is not None
            ]
            if len(requested_folder_ids) != len(set(requested_folder_ids)):
                raise ValueError("folder_ids contains duplicates")
            if set(requested_folder_ids) != set(current_folder_ids):
                raise ValueError("folder_ids must contain every named folder exactly once")
            named = {
                _folder_id(folder): folder
                for folder in current
                if _folder_id(folder) is not None
            }
            iterator = iter(requested_folder_ids)
            reordered = []
            for folder in current:
                if _folder_id(folder) is None:
                    reordered.append(folder)
                else:
                    reordered.append(named[next(iterator)])
            del settings.guild_folders.folders[:]
            for folder in reordered:
                settings.guild_folders.folders.add().CopyFrom(folder)
            log_to_stderr(f"[FOLDERS] Reordering {len(requested_folder_ids)} named folders")
            await apply_rate_limit("action")
            await _save_settings(settings)
            return _text("Reordered server folders")

        order = arguments.get("folder_order")
        if not isinstance(order, list):
            raise ValueError("folder_order must be an array")

        def key_for(folder) -> tuple[str, object]:
            folder_id = _folder_id(folder)
            if folder_id is not None:
                return ("folder", folder_id)
            return ("ungrouped", tuple(folder.guild_ids))

        current_by_key = {key_for(folder): folder for folder in current}
        requested_keys: list[tuple[str, object]] = []
        for entry in order:
            if not isinstance(entry, dict):
                raise ValueError("Each folder_order entry must be an object")
            if entry.get("folder_id") is not None:
                requested_keys.append(("folder", _validate_snowflake(entry["folder_id"], "folder_id")))
            else:
                requested_keys.append(("ungrouped", tuple(_validate_guild_ids(entry.get("guild_ids")))))

        if len(requested_keys) != len(set(requested_keys)):
            raise ValueError("folder_order contains duplicate entries")
        if set(requested_keys) != set(current_by_key):
            raise ValueError(
                "folder_order must contain every current folder and ungrouped entry exactly once. "
                "Read the folders again and use that complete list."
            )

        del settings.guild_folders.folders[:]
        for key in requested_keys:
            settings.guild_folders.folders.add().CopyFrom(current_by_key[key])
        log_to_stderr(f"[FOLDERS] Reordering complete layout entries={len(requested_keys)}")
        await apply_rate_limit("action")
        await _save_settings(settings)
        return _text("Reordered server folders")
    except Exception as exc:
        return _text(f"Error reordering server folders: {exc}")
