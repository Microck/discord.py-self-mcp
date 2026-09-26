from discord_py_self_mcp.tools import channels, folders
from discord_py_self_mcp.tools.registry import registry


def test_list_channels_schema_avoids_anyof_for_provider_compatibility():
    schema = registry.tools["list_channels"].inputSchema

    assert "anyOf" not in schema
    assert {"guild_id", "guild_ids"} <= set(schema["properties"])


def test_reorder_server_folders_schema_avoids_anyof_for_provider_compatibility():
    schema = registry.tools["reorder_server_folders"].inputSchema

    assert "anyOf" not in schema
    assert {"folder_ids", "folder_order"} <= set(schema["properties"])
