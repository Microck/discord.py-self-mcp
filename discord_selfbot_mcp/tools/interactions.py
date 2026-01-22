import discord
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
            "application_id": {"type": "string", "description": "Bot/Application ID (optional if can be inferred, but recommended)"}
        },
        "required": ["channel_id", "command_name"]
    }
)
async def send_slash_command(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        command_name = arguments["command_name"]
        options = arguments.get("options", {})
        application_id = arguments.get("application_id")

        channel = client.get_channel(channel_id)
        if not channel:
            return [TextContent(type="text", text="Channel not found")]

        # In discord.py-self, triggering slash commands often requires the application command object
        # or using channel.slash_commands methods if available.
        # Common pattern in dolfies/discord.py-self:
        # await channel.slash_command(command_name, arguments, application_id)
        # Or finding the command first.
        
        # We'll try the most direct method available in recent versions
        # Typically: search for the command in the channel or guild commands
        
        if not application_id:
             return [TextContent(type="text", text="application_id is currently required for reliability")]

        # This is a simplified wrapper. Real implementation depends heavily on specific library version features
        # Assuming trigger_slash_command or similar exists or constructing the interaction manually
        
        # For dolfies/discord.py-self 2.0+:
        # search_slash_command(guild_id, query=command_name, limit=1)
        
        commands = await channel.application_commands()
        target_command = None
        for cmd in commands:
            if cmd.name == command_name and (str(cmd.application_id) == application_id if application_id else True):
                target_command = cmd
                break
        
        if not target_command:
             return [TextContent(type="text", text=f"Command '{command_name}' not found in channel")]

        await target_command(channel, **options)
        return [TextContent(type="text", text=f"Executed slash command: /{command_name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error executing slash command: {str(e)}")]

@registry.register(
    name="click_button",
    description="Click a button on a message",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "custom_id": {"type": "string", "description": "Custom ID of the button (or label if ID unknown)"},
            "row": {"type": "integer", "description": "Row index (optional)"},
            "column": {"type": "integer", "description": "Column index (optional)"}
        },
        "required": ["channel_id", "message_id"]
    }
)
async def click_button(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        custom_id = arguments.get("custom_id")
        
        channel = client.get_channel(channel_id)
        if not channel:
             return [TextContent(type="text", text="Channel not found")]
             
        message = await channel.fetch_message(message_id)
        if not message:
             return [TextContent(type="text", text="Message not found")]

        # Iterate through components to find the button
        for row_idx, action_row in enumerate(message.components):
            for col_idx, component in enumerate(action_row.children):
                if isinstance(component, discord.Button):
                    if (custom_id and component.custom_id == custom_id) or \
                       (custom_id and component.label == custom_id) or \
                       (arguments.get("row") == row_idx and arguments.get("column") == col_idx):
                        
                        await component.click()
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
            "custom_id": {"type": "string", "description": "Custom ID of the menu (optional)"},
            "values": {"type": "array", "items": {"type": "string"}, "description": "Values to select"},
            "row": {"type": "integer"},
            "column": {"type": "integer"}
        },
        "required": ["channel_id", "message_id", "values"]
    }
)
async def select_menu(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        values = arguments["values"]
        custom_id = arguments.get("custom_id")
        
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)

        for row_idx, action_row in enumerate(message.components):
            for col_idx, component in enumerate(action_row.children):
                if isinstance(component, discord.SelectMenu):
                    if (custom_id and component.custom_id == custom_id) or \
                       (arguments.get("row") == row_idx and arguments.get("column") == col_idx) or \
                       (not custom_id and not arguments.get("row")): # Default to first menu if no specifier
                        
                        await component.choose(values)
                        return [TextContent(type="text", text=f"Selected values {values} in menu")]

        return [TextContent(type="text", text="Menu not found")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error selecting menu: {str(e)}")]
