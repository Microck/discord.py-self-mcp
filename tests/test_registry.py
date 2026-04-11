import pytest
from mcp.types import TextContent

from discord_py_self_mcp.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_call_tool_lists_available_tools_for_unknown_name():
    registry = ToolRegistry()

    async def alpha_handler(arguments):
        return [TextContent(type="text", text=str(arguments))]

    registry.register("alpha", "Alpha tool", {"type": "object"})(alpha_handler)

    with pytest.raises(ValueError) as exc:
        await registry.call_tool("missing", {})

    assert str(exc.value) == "Unknown tool 'missing'. Available tools: alpha"
