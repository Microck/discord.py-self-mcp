import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies
mcp = MagicMock()
mcp.server = MagicMock()
mcp.server.stdio = MagicMock()
mcp.types = MagicMock()

sys.modules['mcp'] = mcp
sys.modules['mcp.server'] = mcp.server
sys.modules['mcp.server.stdio'] = mcp.server.stdio
sys.modules['mcp.types'] = mcp.types

# Setup decorator mocks to pass through functions
def passthrough_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

mcp.server.Server.return_value.list_tools.side_effect = passthrough_decorator
mcp.server.Server.return_value.call_tool.side_effect = passthrough_decorator

discord = MagicMock()
discord.Client = MagicMock
sys.modules['discord'] = discord
sys.modules['discord.ext'] = MagicMock()

# Now import the real modules
from discord_selfbot_mcp import main
from discord_selfbot_mcp.tools import registry, messages, guilds

class TestMCPServerLogic(unittest.IsolatedAsyncioTestCase):
    async def test_registry_calls(self):
        # We need to verify that main.list_tools calls registry.get_tool_definitions
        # registry is the module, registry.registry is the object
        with patch('discord_selfbot_mcp.tools.registry.registry.get_tool_definitions') as mock_get_tools:
            await main.list_tools()
            mock_get_tools.assert_called_once()
            
    async def test_message_tools(self):
        # Test the send_message function directly
        mock_client = MagicMock()
        mock_channel = AsyncMock()
        mock_client.get_channel.return_value = mock_channel
        
        # We need to patch the client imported in the messages module
        with patch('discord_selfbot_mcp.tools.messages.client', mock_client):
            await messages.send_message({'channel_id': '123', 'content': 'hello'})
            mock_client.get_channel.assert_called_with(123)
            mock_channel.send.assert_called_with('hello')

if __name__ == '__main__':
    unittest.main()
