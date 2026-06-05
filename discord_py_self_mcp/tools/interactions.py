import discord
import inspect
from mcp.types import TextContent
from .registry import registry
from ..bot import client
from ..tool_utils import NON_MESSAGEABLE_TEXT, apply_rate_limit


async def _collect_commands(result):
    if inspect.isawaitable(result):
        result = await result
    if result is None:
        return []
    if hasattr(result, "__aiter__"):
        return [cmd async for cmd in result]
    return list(result)


def _infer_application_id(channel, application_id):
    """Resolve the application id to use for command lookup.

    Explicit values win. Otherwise, in a DM with a bot we can safely default to
    the recipient's id - that is the application whose commands are usable there.
    """
    if application_id:
        return str(application_id)
    recipient = getattr(channel, "recipient", None)
    if recipient is not None and getattr(recipient, "bot", False):
        return str(recipient.id)
    return None


async def _resolve_via_application(channel, application_id, root_name):
    """Resolve a root SlashCommand by listing the application's registered
    commands (GET /applications/{id}/commands).

    This is the reliable path for guild-installed bots: the per-channel "/"
    command search index (application-commands/search) returns nothing for many
    of them, even though their commands work in the Discord client and are
    fully invokable. Returns (command_or_None, available_command_names).
    """
    raw = await client.http.get_application_commands(int(application_id))
    if not isinstance(raw, list):
        return None, []
    # type 1 == CHAT_INPUT (slash). 2/3 are user/message context-menu commands.
    chat_input = [c for c in raw if c.get("type", 1) == 1]
    names = [c.get("name") for c in chat_input if c.get("name")]
    match = next((c for c in chat_input if c.get("name") == root_name), None)
    if not match:
        return None, names
    state = getattr(client, "_connection", None)
    command = discord.SlashCommand(state=state, data=match, channel=channel)
    return command, names


async def _resolve_via_search(channel, application_id, root_name):
    """Fallback: resolve via the channel "/" command search index.

    Works when the app id is unknown and the bot is indexed for the channel.
    Returns the list of matching root SlashCommands (so the caller can detect
    ambiguity across applications).
    """
    commands = []
    slash_commands = getattr(channel, "slash_commands", None)
    if callable(slash_commands):
        commands = await _collect_commands(slash_commands(query=root_name))
    commands = [c for c in commands if isinstance(c, discord.SlashCommand)]
    matching = [c for c in commands if getattr(c, "name", None) == root_name]
    if application_id:
        matching = [
            c
            for c in matching
            if str(getattr(c, "application_id", "")) == str(application_id)
        ]
    return matching


@registry.register(
    name="send_slash_command",
    description=(
        "Invoke (send) an application slash command in a channel or DM. For a "
        "bot's commands, pass application_id (the bot's user/application ID); in "
        "a DM with a bot it is inferred automatically. Subcommands are given "
        "space-separated in command_name (e.g. 'group sub')."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "command_name": {
                "type": "string",
                "description": "Command name, optionally with subcommands, e.g. 'remind' or 'config set'",
            },
            "options": {"type": "object", "description": "Command options/arguments by name"},
            "application_id": {
                "type": "string",
                "description": "Bot/Application ID. Strongly recommended; auto-inferred only in a DM with a bot.",
            },
        },
        "required": ["channel_id", "command_name"],
    },
)
async def send_slash_command(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        command_name = arguments["command_name"].strip()
        options = arguments.get("options") or {}
        application_id = arguments.get("application_id")

        if command_name.startswith("/"):
            command_name = command_name[1:]

        if not isinstance(options, dict):
            return [TextContent(type="text", text="options must be an object")]

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except Exception:
                channel = None
        if not channel:
            return [TextContent(type="text", text="Channel not found")]

        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]

        parts = [p for p in command_name.split(" ") if p]
        if not parts:
            return [TextContent(type="text", text="Command name is empty")]
        root_name = parts[0]
        subcommand_parts = parts[1:]

        # Resolve the root command. Prefer the application command listing when an
        # application id is known (explicit or inferred from a bot DM); fall back
        # to the channel "/" search index only when there is no app id or the
        # listing failed.
        resolved_app_id = _infer_application_id(channel, application_id)
        target_command = None
        available_names = []
        app_error = None
        app_listed = False

        if resolved_app_id:
            try:
                target_command, available_names = await _resolve_via_application(
                    channel, resolved_app_id, root_name
                )
                app_listed = True
            except Exception as e:
                app_error = f"{type(e).__name__}: {e}"

        if target_command is None and not app_listed:
            try:
                matching = await _resolve_via_search(channel, application_id, root_name)
            except Exception as e:
                detail = app_error or f"{type(e).__name__}: {e}"
                return [
                    TextContent(
                        type="text",
                        text=f"Could not fetch commands for '/{root_name}': {detail}",
                    )
                ]
            if len(matching) > 1 and not application_id:
                choices = ", ".join(
                    f"{c.name} (app_id={getattr(c, 'application_id', 'unknown')})"
                    for c in matching
                )
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"Multiple commands named '{root_name}' found. Provide "
                            f"application_id. Options: {choices}"
                        ),
                    )
                ]
            target_command = matching[0] if matching else None

        if target_command is None:
            if available_names:
                hint = (
                    " Available for this application: "
                    + ", ".join("/" + n for n in available_names)
                    + "."
                )
            elif not resolved_app_id:
                hint = (
                    " Tip: pass application_id (the bot's ID) - the channel '/' "
                    "search index returns nothing for many guild-installed bots."
                )
            else:
                hint = ""
            suffix = f" ({app_error})" if app_error else ""
            return [
                TextContent(
                    type="text", text=f"Command '/{root_name}' not found.{hint}{suffix}"
                )
            ]

        # Navigate subcommands / groups.
        if subcommand_parts:
            current = target_command
            for part in subcommand_parts:
                children = getattr(current, "children", []) or []
                next_child = next(
                    (
                        child
                        for child in children
                        if getattr(child, "name", None) == part
                    ),
                    None,
                )
                if not next_child:
                    available = (
                        ", ".join(child.name for child in children)
                        if children
                        else "none"
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Subcommand '{part}' not found under '{current.name}'. Available: {available}",
                        )
                    ]
                current = next_child

            if getattr(current, "is_group", None) and current.is_group():
                return [
                    TextContent(
                        type="text",
                        text="Subcommand group provided without a leaf subcommand",
                    )
                ]
            target_command = current
        elif getattr(target_command, "is_group", None) and target_command.is_group():
            children = getattr(target_command, "children", []) or []
            available = (
                ", ".join(child.name for child in children) if children else "none"
            )
            return [
                TextContent(
                    type="text",
                    text=f"'/{root_name}' is a command group; specify a subcommand. Available: {available}",
                )
            ]

        # Surface (rather than silently drop) options the command does not define.
        known_opts = {o.name for o in getattr(target_command, "options", []) or []}
        unknown = [k for k in options if k not in known_opts]

        await apply_rate_limit("action")
        interaction = await target_command(channel, **options)

        msg = f"Executed slash command: /{' '.join(parts)}"
        interaction_id = getattr(interaction, "id", None)
        if interaction_id:
            msg += f" (interaction {interaction_id})"
        if unknown:
            valid = ", ".join(sorted(known_opts)) or "none"
            msg += f". Ignored unknown option(s) {unknown}; valid options: {valid}"
        return [TextContent(type="text", text=msg)]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error executing slash command: {type(e).__name__}: {str(e)}",
            )
        ]


@registry.register(
    name="click_button",
    description="Click a button on a message",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "custom_id": {
                "type": "string",
                "description": "Custom ID of the button (or label if ID unknown)",
            },
            "row": {"type": "integer", "description": "Row index (optional)"},
            "column": {"type": "integer", "description": "Column index (optional)"},
        },
        "required": ["channel_id", "message_id"],
    },
)
async def click_button(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        custom_id = arguments.get("custom_id")

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]

        message = await channel.fetch_message(message_id)
        if not message:
            return [TextContent(type="text", text="Message not found")]

        # Iterate through components to find the button
        for row_idx, action_row in enumerate(message.components or []):
            for col_idx, component in enumerate(action_row.children):
                if isinstance(component, discord.Button):
                    if component.disabled:
                        continue
                    if (
                        (custom_id and component.custom_id == custom_id)
                        or (custom_id and component.label == custom_id)
                        or (
                            arguments.get("row") == row_idx
                            and arguments.get("column") == col_idx
                        )
                    ):
                        await apply_rate_limit("action")
                        result = await component.click()
                        if isinstance(result, str):
                            return [
                                TextContent(
                                    type="text", text=f"Button is a URL: {result}"
                                )
                            ]
                        return [TextContent(type="text", text="Button clicked")]

        return [TextContent(type="text", text="Button not found")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error clicking button: {str(e)}")]


@registry.register(
    name="select_menu",
    description="Select an option in a menu",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "custom_id": {
                "type": "string",
                "description": "Custom ID of the menu (optional)",
            },
            "values": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Values to select",
            },
            "row": {"type": "integer"},
            "column": {"type": "integer"},
        },
        "required": ["channel_id", "message_id", "values"],
    },
)
async def select_menu(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        values = arguments["values"]
        custom_id = arguments.get("custom_id")

        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            return [TextContent(type="text", text="values must be a list")]

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]
        message = await channel.fetch_message(message_id)

        for row_idx, action_row in enumerate(message.components or []):
            for col_idx, component in enumerate(action_row.children):
                if isinstance(component, discord.SelectMenu):
                    if (
                        (custom_id and component.custom_id == custom_id)
                        or (
                            arguments.get("row") == row_idx
                            and arguments.get("column") == col_idx
                        )
                        or (not custom_id and not arguments.get("row"))
                    ):  # Default to first menu if no specifier
                        selected_options = []
                        if component.options:
                            for value in values:
                                match = next(
                                    (
                                        opt
                                        for opt in component.options
                                        if opt.value == value or opt.label == value
                                    ),
                                    None,
                                )
                                if not match:
                                    available = ", ".join(
                                        opt.value for opt in component.options
                                    )
                                    return [
                                        TextContent(
                                            type="text",
                                            text=f"Value '{value}' not found in menu options. Available: {available}",
                                        )
                                    ]
                                selected_options.append(match)
                        else:
                            selected_options = [
                                discord.SelectOption(label=str(value), value=str(value))
                                for value in values
                            ]

                        await apply_rate_limit("action")
                        await component.choose(*selected_options)
                        return [
                            TextContent(
                                type="text", text=f"Selected values {values} in menu"
                            )
                        ]

        return [TextContent(type="text", text="Menu not found")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error selecting menu: {str(e)}")]
