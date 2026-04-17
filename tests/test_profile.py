import pytest

from discord_py_self_mcp.tools import profile
from discord_py_self_mcp.tools.registry import registry


class FakeUser:
    def __init__(self):
        self.calls = []

    async def edit(self, **kwargs):
        self.calls.append(kwargs)


class FakeClient:
    def __init__(self):
        self.user = FakeUser()


@pytest.mark.asyncio
async def test_edit_profile_schema_only_exposes_supported_fields():
    schema = registry.tools["edit_profile"].inputSchema

    assert sorted(schema["properties"]) == ["accent_color", "bio"]
    assert "password" not in schema["properties"]


@pytest.mark.asyncio
async def test_edit_profile_uses_accent_colour_kwarg(monkeypatch):
    fake_client = FakeClient()

    async def noop_rate_limit(action_type):
        return None

    monkeypatch.setattr(profile, "client", fake_client)
    monkeypatch.setattr(profile, "apply_rate_limit", noop_rate_limit)

    result = await profile.edit_profile({"accent_color": 16711680, "bio": "hello"})

    assert result[0].text == "Profile updated"
    assert fake_client.user.calls == [{"bio": "hello", "accent_colour": 16711680}]
