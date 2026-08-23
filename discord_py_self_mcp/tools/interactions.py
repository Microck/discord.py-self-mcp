import asyncio
import discord
import inspect
from mcp.types import TextContent
from .registry import registry
from ..bot import client
from .. import modal_store
from ..tool_utils import NON_MESSAGEABLE_TEXT, apply_rate_limit


# Discord pushes the modal on a separate gateway event, so the click and the
# modal are two events. Five seconds is slack for a gateway round trip.
MODAL_WAIT_SECONDS = 5.0


def _describe_modal(modal) -> str:
    lines = [
        f"Modal opened: custom_id={modal.custom_id!r} title={modal.title!r}",
        "Fields (pass these to submit_modal):",
    ]
    found = False
    for row in modal.components or []:
        for field in getattr(row, "children", []):
            if not hasattr(field, "custom_id"):
                continue
            found = True
            bits = [f"  - {field.custom_id!r}"]
            label = getattr(field, "label", None)
            if label:
                bits.append(f"label={label!r}")
            bits.append(
                "required" if getattr(field, "required", False) else "optional"
            )
            min_length = getattr(field, "min_length", None)
            max_length = getattr(field, "max_length", None)
            if min_length is not None:
                bits.append(f"min_length={min_length}")
            if max_length is not None:
                bits.append(f"max_length={max_length}")
            lines.append(" ".join(bits))
    if not found:
        lines.append("  (no text inputs)")
    return "\n".join(lines)


async def _wait_for_modal():
    """Await the next modal, or None if none arrives in time."""
    try:
        return await client.wait_for("modal", timeout=MODAL_WAIT_SECONDS)
    except asyncio.TimeoutError:
        return None


EPHEMERAL_FLAG = 1 << 6


def _is_ephemeral(message) -> bool:
    return bool(getattr(message.flags, "value", 0) & EPHEMERAL_FLAG)


def _cached_message(message_id: int):
    for message in client.cached_messages:
        if message.id == message_id:
            return message
    return None


async def _resolve_message(channel, message_id: int):
    """Fetch a message, falling back to the gateway cache.

    Ephemeral interaction responses are never persisted, so the REST route
    404s on them. They do arrive over the gateway and land in the client's
    message cache, and their components stay usable, so the cache is the only
    way to reach a button on an interaction reply.
    """
    try:
        return await channel.fetch_message(message_id)
    except discord.NotFound:
        cached = _cached_message(message_id)
        if cached is None:
            raise
        return cached


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

        message = await _resolve_message(channel, message_id)
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
                        waiter = asyncio.ensure_future(_wait_for_modal())
                        click_error = None
                        result = None
                        try:
                            result = await component.click()
                        except Exception as e:
                            # A button that opens a modal answers with
                            # INTERACTION_MODAL_CREATE, which the library's
                            # response matching does not accept as an ack, so
                            # click() intermittently raises InvalidData even
                            # though the modal arrives. Decide on the modal,
                            # not on this exception.
                            click_error = e
                        if isinstance(result, str):
                            waiter.cancel()
                            return [
                                TextContent(
                                    type="text", text=f"Button is a URL: {result}"
                                )
                            ]
                        if click_error is not None:
                            # Modal-opening buttons answer with
                            # INTERACTION_MODAL_CREATE, which the library's
                            # ack matching rejects, so click() raises even
                            # though the modal arrives. That exception is the
                            # only advance signal a modal may be coming, so
                            # the full window is spent only here.
                            modal = await waiter
                        else:
                            # A cleanly acked click received a normal
                            # interaction response, so no modal follows it.
                            # Ordinary buttons must not pay the modal window.
                            waiter.cancel()
                            modal = None
                        if modal is not None:
                            return [
                                TextContent(
                                    type="text",
                                    text="Button clicked.\n"
                                    + _describe_modal(modal),
                                )
                            ]
                        if click_error is not None:
                            raise click_error
                        return [
                            TextContent(type="text", text="Button clicked")
                        ]

        return [TextContent(type="text", text="Button not found")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error clicking button: {str(e)}")]


async def _channel_for(channel_id: int):
    """Resolve a messageable channel or return an error TextContent list."""
    channel = client.get_channel(channel_id)
    if not channel:
        try:
            channel = await client.fetch_channel(channel_id)
        except discord.NotFound:
            return None, [TextContent(type="text", text="Channel not found")]
        except discord.Forbidden:
            return None, [
                TextContent(type="text", text="Access denied to channel")
            ]
    if not isinstance(channel, discord.abc.Messageable):
        return None, [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]
    return channel, None


def _command_kind(command) -> str:
    if isinstance(command, discord.UserCommand):
        return "user"
    if isinstance(command, discord.MessageCommand):
        return "message"
    return "slash"


async def _find_context_command(channel, name, kind, application_id):
    commands = await _collect_commands(channel.application_commands())
    wanted = discord.UserCommand if kind == "user" else discord.MessageCommand
    available = []
    id_mismatch = False
    for command in commands:
        if not isinstance(command, wanted):
            continue
        available.append(command.name)
        if command.name != name:
            continue
        if application_id and str(
            getattr(command, "application_id", "")
        ) != str(application_id):
            # The name exists but belongs to another application: keep it
            # visible in `available` while flagging the mismatch so the
            # caller can say why the command was not run.
            id_mismatch = True
            continue
        return command, available, None
    return None, available, (
        f"Command {name!r} exists but is not registered by application "
        f"{application_id}. Pass the right application_id or omit it to "
        "match any application."
        if id_mismatch
        else None
    )


@registry.register(
    name="list_application_commands",
    description=(
        "List the application commands available in a channel: slash "
        "commands, plus the user and message commands that live in the "
        "right-click 'Apps' menu. Use it to discover names for "
        "send_slash_command, send_user_command and send_message_command."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "kind": {
                "type": "string",
                "enum": ["slash", "user", "message", "all"],
                "description": "Filter by command kind (default all)",
            },
        },
        "required": ["channel_id"],
    },
)
async def list_application_commands(arguments: dict):
    try:
        channel, error = await _channel_for(int(arguments["channel_id"]))
        if error:
            return error

        kind = arguments.get("kind") or "all"
        commands = await _collect_commands(channel.application_commands())

        lines = []
        for command in commands:
            actual = _command_kind(command)
            if kind != "all" and actual != kind:
                continue
            lines.append(
                f"- {actual}: {command.name!r} "
                f"application_id={getattr(command, 'application_id', None)}"
            )

        if not lines:
            return [
                TextContent(
                    type="text",
                    text=f"No {kind} commands available in this channel",
                )
            ]
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error listing application commands: {type(e).__name__}: {e}",
            )
        ]


@registry.register(
    name="send_user_command",
    description=(
        "Invoke a user context-menu command (right-click a user -> Apps). "
        "Find names with list_application_commands."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "user_id": {
                "type": "string",
                "description": "The user the command targets",
            },
            "command_name": {"type": "string"},
            "application_id": {
                "type": "string",
                "description": "Disambiguate when two apps share a name (optional)",
            },
        },
        "required": ["channel_id", "user_id", "command_name"],
    },
)
async def send_user_command(arguments: dict):
    try:
        channel, error = await _channel_for(int(arguments["channel_id"]))
        if error:
            return error

        name = arguments["command_name"]
        command, available, mismatch = await _find_context_command(
            channel, name, "user", arguments.get("application_id")
        )
        if command is None:
            listing = ", ".join(sorted(available)) or "none"
            reason = f" {mismatch}" if mismatch else ""
            return [
                TextContent(
                    type="text",
                    text=(
                        f"User command {name!r} not found.{reason} "
                        f"Available user commands: {listing}"
                    ),
                )
            ]

        user_id = int(arguments["user_id"])
        user = client.get_user(user_id)
        if user is None:
            try:
                user = await client.fetch_user(user_id)
            except discord.NotFound:
                return [TextContent(type="text", text="User not found")]

        await apply_rate_limit("action")
        await command(user, channel=channel)
        return [
            TextContent(
                type="text",
                text=f"Executed user command {name!r} on {user}",
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error executing user command: {type(e).__name__}: {e}",
            )
        ]


@registry.register(
    name="send_message_command",
    description=(
        "Invoke a message context-menu command (right-click a message -> "
        "Apps). Find names with list_application_commands."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {
                "type": "string",
                "description": "The message the command targets",
            },
            "command_name": {"type": "string"},
            "application_id": {
                "type": "string",
                "description": "Disambiguate when two apps share a name (optional)",
            },
        },
        "required": ["channel_id", "message_id", "command_name"],
    },
)
async def send_message_command(arguments: dict):
    try:
        channel, error = await _channel_for(int(arguments["channel_id"]))
        if error:
            return error

        name = arguments["command_name"]
        command, available, mismatch = await _find_context_command(
            channel, name, "message", arguments.get("application_id")
        )
        if command is None:
            listing = ", ".join(sorted(available)) or "none"
            reason = f" {mismatch}" if mismatch else ""
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Message command {name!r} not found.{reason} "
                        f"Available message commands: {listing}"
                    ),
                )
            ]

        try:
            message = await _resolve_message(channel, int(arguments["message_id"]))
        except discord.NotFound:
            return [TextContent(type="text", text="Message not found")]

        await apply_rate_limit("action")
        await command(message, channel=channel)
        return [
            TextContent(
                type="text",
                text=f"Executed message command {name!r} on {message.id}",
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error executing message command: {type(e).__name__}: {e}",
            )
        ]


@registry.register(
    name="list_ephemeral_messages",
    description=(
        "List recent ephemeral interaction replies (the private 'only you can "
        "see this' messages a bot sends in response to a click or command). "
        "They cannot be read with read_messages because Discord never "
        "persists them. Use this to get the message_id of a reply whose "
        "buttons you want to click."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {
                "type": "string",
                "description": "Only list replies in this channel (optional)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum replies to return, newest first (default 10)",
            },
        },
        "required": [],
    },
)
async def list_ephemeral_messages(arguments: dict):
    try:
        channel_id = arguments.get("channel_id")
        channel_id = int(channel_id) if channel_id else None
        limit = arguments.get("limit") or 10

        found = []
        for message in reversed(client.cached_messages):
            if not _is_ephemeral(message):
                continue
            if channel_id is not None and message.channel.id != channel_id:
                continue
            found.append(message)
            if len(found) >= limit:
                break

        if not found:
            return [
                TextContent(
                    type="text",
                    text=(
                        "No ephemeral replies cached. They are only captured "
                        "while this server is connected, so trigger the "
                        "interaction first, then call this."
                    ),
                )
            ]

        lines = []
        for message in found:
            buttons = [
                c.custom_id
                for row in (message.components or [])
                for c in getattr(row, "children", [])
                if getattr(c, "custom_id", None)
            ]
            summary = message.content or ""
            if not summary and message.embeds:
                embed = message.embeds[0]
                summary = embed.title or embed.description or "(embed)"
            lines.append(
                f"- message_id={message.id} channel_id={message.channel.id} "
                f"author={message.author} content={summary[:120]!r} "
                f"buttons={buttons}"
            )
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=(
                    "Error listing ephemeral messages: "
                    f"{type(e).__name__}: {str(e)}"
                ),
            )
        ]


def _modal_fields(modal) -> dict:
    fields = {}
    for row in modal.components or []:
        for field in getattr(row, "children", []):
            custom_id = getattr(field, "custom_id", None)
            if custom_id is not None:
                fields[custom_id] = field
    return fields


@registry.register(
    name="submit_modal",
    description=(
        "Answer and submit a modal that Discord opened in response to an "
        "earlier click_button or send_slash_command. Use the custom_id and "
        "field names that click_button reported."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "custom_id": {
                "type": "string",
                "description": "Custom ID of the modal, as reported by click_button",
            },
            "values": {
                "type": "object",
                "description": (
                    "Map of field custom_id to the string value to submit. "
                    "Omit optional fields to leave them empty."
                ),
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["custom_id", "values"],
    },
)
async def submit_modal(arguments: dict):
    try:
        custom_id = arguments["custom_id"]
        values = arguments.get("values")

        if not isinstance(values, dict):
            return [TextContent(type="text", text="values must be an object")]

        modal = modal_store.take(custom_id)
        if modal is None:
            pending = ", ".join(sorted(modal_store.known_ids())) or "none"
            return [
                TextContent(
                    type="text",
                    text=(
                        f"No pending modal with custom_id {custom_id!r}. It may "
                        f"have expired, or the button was never clicked. Click "
                        f"the button again to reopen it. Pending modals: {pending}"
                    ),
                )
            ]

        fields = _modal_fields(modal)
        unknown = sorted(set(values) - set(fields))

        missing = sorted(
            field_id
            for field_id, field in fields.items()
            if getattr(field, "required", False) and not values.get(field_id)
        )
        if unknown:
            # Reject before submitting: an unknown key almost always means a
            # mistyped field id, and submitting would leave that field empty
            # irreversibly. Same restoration path as missing-required below.
            modal_store.put(modal)
            valid = ", ".join(sorted(fields)) or "none"
            return [
                TextContent(
                    type="text",
                    text=(
                        "Unknown field(s): "
                        f"{', '.join(unknown)}. Modal was not submitted. "
                        f"Valid fields: {valid}"
                    ),
                )
            ]
        if missing:
            # Put it back so the caller can retry without re-clicking.
            modal_store.put(modal)
            return [
                TextContent(
                    type="text",
                    text=(
                        "Missing required field(s): "
                        f"{', '.join(missing)}. Modal was not submitted."
                    ),
                )
            ]

        for field_id, field in fields.items():
            if field_id in values:
                try:
                    field.answer(values[field_id])
                except ValueError as e:
                    modal_store.put(modal)
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Invalid value for {field_id!r}: {e}. "
                                "Modal was not submitted."
                            ),
                        )
                    ]

        # A rate-limit failure here happens before anything is sent, so the
        # modal goes back and the caller can retry. Past this point the entry
        # stays consumed: once the answers have been handed to Discord, a
        # second attempt could submit the interaction twice.
        try:
            await apply_rate_limit("action")
        except Exception:
            modal_store.put(modal)
            raise
        await modal.submit()

        msg = f"Modal {custom_id!r} submitted"
        return [TextContent(type="text", text=msg)]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error submitting modal: {type(e).__name__}: {str(e)}",
            )
        ]


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
        message = await _resolve_message(channel, message_id)

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
