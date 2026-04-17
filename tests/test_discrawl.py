import pytest

from discord_py_self_mcp.tools import discrawl


@pytest.mark.asyncio
async def test_run_discrawl_rejects_relative_binary_path():
    result = await discrawl.run_discrawl({"command": "status", "binary": "./discrawl"})

    assert (
        result[0].text
        == "binary must be the literal 'discrawl' or an absolute path to a discrawl executable"
    )
