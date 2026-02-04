import discord
import inspect
from mcp.types import TextContent
from .registry import registry
from ..bot import client


@registry.register(
    name="send_slash_command",
    description="Send a slash command",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "command_name": {"type": "string"},
            "options": {"type": "object", "description": "Command options/arguments"},
            "application_id": {
                "type": "string",
                "description": "Bot/Application ID (optional if can be inferred, but recommended)",
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

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except Exception:
                channel = None
        if not channel:
            return [TextContent(type="text", text="Channel not found")]

        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text="Channel is not messageable")]

        if not isinstance(options, dict):
            return [TextContent(type="text", text="options must be an object")]

        parts = [p for p in command_name.split(" ") if p]
        if not parts:
            return [TextContent(type="text", text="Command name is empty")]
        root_name = parts[0]
        subcommand_parts = parts[1:]

        async def _collect_commands(result):
            if inspect.isawaitable(result):
                result = await result
            if result is None:
                return []
            if hasattr(result, "__aiter__"):
                return [cmd async for cmd in result]
            return list(result)

        commands = []
        slash_commands = getattr(channel, "slash_commands", None)
        if callable(slash_commands):
            try:
                commands = await _collect_commands(slash_commands(query=root_name))
            except Exception:
                commands = []

        application_commands = getattr(channel, "application_commands", None)
        if not commands and callable(application_commands):
            try:
                commands = await _collect_commands(application_commands())
            except Exception:
                commands = []

        if commands:
            commands = [
                cmd for cmd in commands if isinstance(cmd, discord.SlashCommand)
            ]

        matching = [cmd for cmd in commands if getattr(cmd, "name", None) == root_name]
        if application_id:
            matching = [
                cmd
                for cmd in matching
                if str(getattr(cmd, "application_id", "")) == str(application_id)
            ]

        if not matching:
            return [
                TextContent(
                    type="text", text=f"Command '{root_name}' not found in channel"
                )
            ]

        if len(matching) > 1 and not application_id:
            choices = ", ".join(
                f"{cmd.name} (app_id={getattr(cmd, 'application_id', 'unknown')})"
                for cmd in matching
            )
            return [
                TextContent(
                    type="text",
                    text=f"Multiple commands named '{root_name}' found. Provide application_id. Options: {choices}",
                )
            ]

        target_command = matching[0]

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

        await target_command(channel, **options)
        return [
            TextContent(type="text", text=f"Executed slash command: /{' '.join(parts)}")
        ]

    except Exception as e:
        return [
            TextContent(type="text", text=f"Error executing slash command: {str(e)}")
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
            return [TextContent(type="text", text="Channel is not messageable")]

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
            return [TextContent(type="text", text="Channel is not messageable")]
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

                        await component.choose(*selected_options)
                        return [
                            TextContent(
                                type="text", text=f"Selected values {values} in menu"
                            )
                        ]

        return [TextContent(type="text", text="Menu not found")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error selecting menu: {str(e)}")]
