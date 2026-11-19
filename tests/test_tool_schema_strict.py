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


def _walk(node):
    """Yield every dict/list in a schema so nested anyOf cannot hide."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def test_send_message_file_paths_is_a_plain_string_array():
    schema = registry.tools["send_message"].inputSchema

    assert not [n for n in _walk(schema) if "anyOf" in n]
    file_paths = schema["properties"]["file_paths"]
    assert file_paths["type"] == "array"
    assert file_paths["items"] == {"type": "string"}
    # content stays required so existing callers keep the same contract
    assert schema["required"] == ["channel_id", "content"]


def test_send_thread_message_file_paths_is_a_plain_string_array():
    schema = registry.tools["send_thread_message"].inputSchema

    assert not [n for n in _walk(schema) if "anyOf" in n]
    assert schema["properties"]["file_paths"]["items"] == {"type": "string"}
    assert schema["required"] == ["thread_id", "content"]
