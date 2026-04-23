from discord_py_self_mcp.logging_utils import mask_secret


def test_mask_secret_hides_secret_shape():
    assert mask_secret("super-secret-token") == "<configured>"
    assert mask_secret("") == "<missing>"
