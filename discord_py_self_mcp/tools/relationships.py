from mcp.types import TextContent

from ..bot import client
from .registry import registry


@registry.register(
    name="list_friends",
    description="List all friends",
    input_schema={
        "type": "object",
        "properties": {}
    }
)
async def list_friends(arguments: dict):
    try:
        friends = client.friends
        if not friends:
             return [TextContent(type="text", text="No friends found (or list is empty)")]

        friend_list = [f"{f.name}#{f.discriminator} ({f.id})" for f in friends]
        return [TextContent(type="text", text="\n".join(friend_list))]
    except AttributeError:
         return [TextContent(type="text", text="Client does not support friends list (or not logged in)")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing friends: {str(e)}")]

@registry.register(
    name="send_friend_request",
    description="Send a friend request to a user",
    input_schema={
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "discriminator": {"type": "string", "description": "Optional if using new username system (0)"}
        },
        "required": ["username"]
    }
)
async def send_friend_request(arguments: dict):
    try:
        username = arguments["username"]
        discriminator = arguments.get("discriminator")

        # 1. Search in local cache (users shared in guilds)
        target_user = None
        for user in client.users:
            if user.name == username:
                if discriminator:
                    if user.discriminator == discriminator:
                        target_user = user
                        break
                else:
                    # New username system or no discrim provided
                    if user.discriminator == "0":
                        target_user = user
                        break

        if target_user:
            await target_user.send_friend_request()
            return [TextContent(type="text", text=f"Sent friend request to {target_user.name} (found in cache)")]

        return [TextContent(type="text", text=f"User '{username}' not found in cached guilds. Please use 'add_friend' with their User ID.")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

@registry.register(
    name="add_friend",
    description="Add a friend by User ID",
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"}
        },
        "required": ["user_id"]
    }
)
async def add_friend(arguments: dict):
    try:
        user_id = int(arguments["user_id"])
        user = await client.fetch_user(user_id)
        await user.send_friend_request()
        return [TextContent(type="text", text=f"Sent friend request to {user.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error adding friend: {str(e)}")]

@registry.register(
    name="remove_friend",
    description="Remove a friend",
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"}
        },
        "required": ["user_id"]
    }
)
async def remove_friend(arguments: dict):
    try:
        user_id = int(arguments["user_id"])
        user = client.get_user(user_id) or await client.fetch_user(user_id)
        await user.remove_friend()
        return [TextContent(type="text", text=f"Removed friend {user.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error removing friend: {str(e)}")]
