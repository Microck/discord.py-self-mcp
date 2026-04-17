import pytest

from discord_py_self_mcp.tools import guilds


class FakeUser:
    def __init__(self, *, user_id=99, name="tester", global_name=None, discriminator="0"):
        self.id = user_id
        self.name = name
        self.global_name = global_name
        self.discriminator = discriminator


class FakeGuild:
    def __init__(self, name="Guild", guild_id=1):
        self.name = name
        self.id = guild_id


class FakeClient:
    def __init__(self, *, ready=True, user=None, guild_list=None):
        self._ready = ready
        self.user = user or FakeUser()
        self.guilds = guild_list or []

    def is_ready(self):
        return self._ready


@pytest.mark.asyncio
async def test_list_guilds_returns_not_ready_text(monkeypatch):
    monkeypatch.setattr(guilds, "client", FakeClient(ready=False))

    result = await guilds.list_guilds({})

    assert result[0].text == guilds.NOT_READY_TEXT


@pytest.mark.asyncio
async def test_get_user_info_prefers_global_name(monkeypatch):
    fake_user = FakeUser(user_id=123, name="handle", global_name="Display Name")
    monkeypatch.setattr(guilds, "client", FakeClient(user=fake_user))

    result = await guilds.get_user_info({})

    assert result[0].text == "User: Display Name (@handle) (123)"
