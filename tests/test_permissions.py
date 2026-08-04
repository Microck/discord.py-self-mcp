import json

import discord
import pytest

from discord_py_self_mcp.tools import permissions


class FakeClient:
    def __init__(self, guild=None, channel=None):
        self._guild = guild
        self._channel = channel

    def get_guild(self, guild_id):
        return self._guild

    def get_channel(self, channel_id):
        return self._channel


class FakeRole:
    def __init__(self, role_id=10, name="mod", position=5):
        self.id = role_id
        self.name = name
        self.position = position
        self.permissions = discord.Permissions(0)
        self.edits = []

    # Mirrors discord.Role ordering: equal positions are broken by id.
    def __lt__(self, other):
        if self.position == other.position:
            return self.id > other.id
        return self.position < other.position

    def __ge__(self, other):
        return not self < other

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class FakeMe:
    def __init__(self, top_role):
        self.id = 999
        self.top_role = top_role


class FakeGuild:
    def __init__(self, roles_list=None, members=None, channels=None, me=None):
        self.roles = roles_list or []
        self._members = members or {}
        self.channels = channels or []
        self.me = me
        self.owner_id = None

    def get_role(self, role_id):
        for role in self.roles:
            if role.id == role_id:
                return role
        return None

    def get_member(self, user_id):
        return self._members.get(user_id)


class FakeChannel:
    def __init__(self, name="general", guild=None, overwrites=None, view=True):
        self.id = 500
        self.name = name
        self.guild = guild
        self.overwrites = overwrites or {}
        self.calls = []
        self.call_kwargs = []
        self._view = view

    async def set_permissions(self, target, overwrite=..., **kwargs):
        self.calls.append((target, overwrite))
        self.call_kwargs.append(kwargs)

    def permissions_for(self, target):
        return discord.Permissions(discord.Permissions.all().value if self._view else 0)


def _guild_with_role(role, my_top_position=100):
    top = FakeRole(role_id=1, name="admin", position=my_top_position)
    return FakeGuild(roles_list=[role, top], me=FakeMe(top))


@pytest.mark.asyncio
async def test_set_role_permissions_accepts_flag_names(monkeypatch):
    role = FakeRole()
    monkeypatch.setattr(permissions, "client", FakeClient(guild=_guild_with_role(role)))

    result = await permissions.set_role_permissions(
        {"guild_id": "1", "role_id": "10", "permissions": ["kick_members"]}
    )

    assert role.edits[0]["permissions"].kick_members is True
    assert "Set permissions on role mod" in result[0].text


@pytest.mark.asyncio
async def test_set_role_permissions_blocks_role_above_own(monkeypatch):
    role = FakeRole(position=50)
    guild = _guild_with_role(role, my_top_position=20)
    monkeypatch.setattr(permissions, "client", FakeClient(guild=guild))

    result = await permissions.set_role_permissions(
        {"guild_id": "1", "role_id": "10", "permissions": "8"}
    )

    assert "at or above your highest role" in result[0].text
    assert role.edits == []


@pytest.mark.asyncio
async def test_set_channel_permissions_builds_overwrite(monkeypatch):
    role = FakeRole()
    guild = FakeGuild(roles_list=[role])
    channel = FakeChannel(guild=guild)
    monkeypatch.setattr(permissions, "client", FakeClient(channel=channel))

    result = await permissions.set_channel_permissions(
        {
            "channel_id": "500",
            "target_id": "10",
            "target_type": "role",
            "allow": ["view_channel"],
            "deny": ["send_messages"],
        }
    )

    target, overwrite = channel.calls[0]
    assert target is role
    assert overwrite.view_channel is True
    assert overwrite.send_messages is False
    assert "Set permissions for mod on #general" in result[0].text


@pytest.mark.asyncio
async def test_set_channel_permissions_rejects_bad_target_type(monkeypatch):
    channel = FakeChannel(guild=FakeGuild())
    monkeypatch.setattr(permissions, "client", FakeClient(channel=channel))

    result = await permissions.set_channel_permissions(
        {"channel_id": "500", "target_id": "10", "target_type": "everyone"}
    )

    assert "Invalid target_type 'everyone'" in result[0].text
    assert channel.calls == []


@pytest.mark.asyncio
async def test_patch_channel_permissions_preserves_other_flags(monkeypatch):
    role = FakeRole()
    overwrite = discord.PermissionOverwrite()
    overwrite.view_channel = True
    overwrite.send_messages = True
    overwrite.attach_files = True
    channel = FakeChannel(guild=FakeGuild(roles_list=[role]), overwrites={role: overwrite})
    monkeypatch.setattr(permissions, "client", FakeClient(channel=channel))

    result = await permissions.patch_channel_permissions(
        {
            "channel_id": "500",
            "target_id": "10",
            "target_type": "role",
            "set": {"attach_files": None},
        }
    )

    _, written = channel.calls[0]
    assert written.attach_files is None
    assert written.view_channel is True
    assert written.send_messages is True
    assert "attach_files=None" in result[0].text


@pytest.mark.asyncio
async def test_patch_channel_permissions_rejects_unknown_flag(monkeypatch):
    role = FakeRole()
    channel = FakeChannel(guild=FakeGuild(roles_list=[role]))
    monkeypatch.setattr(permissions, "client", FakeClient(channel=channel))

    result = await permissions.patch_channel_permissions(
        {
            "channel_id": "500",
            "target_id": "10",
            "target_type": "role",
            "set": {"send_glitter": True},
        }
    )

    assert "Unknown permission name(s): send_glitter" in result[0].text
    assert channel.calls == []


@pytest.mark.asyncio
async def test_patch_channel_permissions_requires_changes(monkeypatch):
    role = FakeRole()
    channel = FakeChannel(guild=FakeGuild(roles_list=[role]))
    monkeypatch.setattr(permissions, "client", FakeClient(channel=channel))

    result = await permissions.patch_channel_permissions(
        {"channel_id": "500", "target_id": "10", "target_type": "role", "set": {}}
    )

    assert result[0].text == "Nothing to change — 'set' is empty"
    assert channel.calls == []


@pytest.mark.asyncio
async def test_remove_channel_permissions_clears_overwrite(monkeypatch):
    role = FakeRole()
    channel = FakeChannel(guild=FakeGuild(roles_list=[role]))
    monkeypatch.setattr(permissions, "client", FakeClient(channel=channel))

    result = await permissions.remove_channel_permissions(
        {"channel_id": "500", "target_id": "10", "target_type": "role"}
    )

    assert channel.calls == [(role, None)]
    assert "Removed permission overwrite for mod" in result[0].text


@pytest.mark.asyncio
async def test_get_channel_permissions_lists_allow_and_deny(monkeypatch):
    role = FakeRole()
    overwrite = discord.PermissionOverwrite()
    overwrite.view_channel = True
    overwrite.send_messages = False
    channel = FakeChannel(guild=FakeGuild(roles_list=[role]), overwrites={role: overwrite})
    monkeypatch.setattr(permissions, "client", FakeClient(channel=channel))

    result = await permissions.get_channel_permissions({"channel_id": "500"})
    payload = json.loads(result[0].text)

    assert payload[0]["target_name"] == "mod"
    # view_channel is an alias; discord.py-self reports the canonical flag name.
    assert payload[0]["allowed"] == ["read_messages"]
    assert payload[0]["denied"] == ["send_messages"]


@pytest.mark.asyncio
async def test_get_channel_permissions_reports_missing_channel(monkeypatch):
    monkeypatch.setattr(permissions, "client", FakeClient(channel=None))

    result = await permissions.get_channel_permissions({"channel_id": "500"})

    assert result[0].text == "Channel not found"


@pytest.mark.asyncio
async def test_inspect_effective_permissions_splits_channels(monkeypatch):
    role = FakeRole()
    visible = FakeChannel(name="visible", view=True)
    hidden = FakeChannel(name="hidden", view=False)
    guild = FakeGuild(roles_list=[role], channels=[visible, hidden])
    # Take the Role branch so target.permissions is read instead of guild_permissions.
    monkeypatch.setattr(discord, "Role", FakeRole)
    monkeypatch.setattr(permissions, "client", FakeClient(guild=guild))

    result = await permissions.inspect_effective_permissions(
        {"guild_id": "1", "target_id": "10", "target_type": "role"}
    )
    payload = json.loads(result[0].text)

    assert payload["accessible_channels"] == ["visible"]
    assert payload["hidden_channels"] == ["hidden"]
    assert payload["accessible_channel_count"] == 1


@pytest.mark.asyncio
async def test_set_category_permissions_syncs_children(monkeypatch):
    role = FakeRole()
    guild = FakeGuild(roles_list=[role])
    child_a = FakeChannel(name="chat", guild=guild)
    child_b = FakeChannel(name="voice", guild=guild)

    class FakeCategory(FakeChannel):
        def __init__(self):
            super().__init__(name="staff", guild=guild)
            self.channels = [child_a, child_b]

    category = FakeCategory()
    monkeypatch.setattr(discord, "CategoryChannel", FakeCategory)
    monkeypatch.setattr(permissions, "client", FakeClient(channel=category))

    result = await permissions.set_category_permissions(
        {
            "category_id": "1",
            "target_id": "10",
            "target_type": "role",
            "deny": ["view_channel"],
        }
    )

    assert len(category.calls) == 1
    assert child_a.calls[0][0] is role
    assert child_b.calls[0][0] is role
    assert "synced 2 channel(s): chat, voice" in result[0].text


@pytest.mark.asyncio
async def test_set_category_permissions_forwards_reason(monkeypatch):
    role = FakeRole()
    guild = FakeGuild(roles_list=[role])
    child = FakeChannel(name="chat", guild=guild)

    class FakeCategory(FakeChannel):
        def __init__(self):
            super().__init__(name="staff", guild=guild)
            self.channels = [child]

    category = FakeCategory()
    monkeypatch.setattr(discord, "CategoryChannel", FakeCategory)
    monkeypatch.setattr(permissions, "client", FakeClient(channel=category))

    await permissions.set_category_permissions(
        {
            "category_id": "1",
            "target_id": "10",
            "target_type": "role",
            "deny": ["view_channel"],
            "reason": "tidying up",
        }
    )

    assert category.call_kwargs[0]["reason"] == "tidying up"
    assert child.call_kwargs[0]["reason"] == "tidying up"


@pytest.mark.asyncio
async def test_set_category_permissions_reports_partial_progress(monkeypatch):
    role = FakeRole()
    guild = FakeGuild(roles_list=[role])
    good = FakeChannel(name="chat", guild=guild)

    class Exploding(FakeChannel):
        async def set_permissions(self, target, overwrite=..., **kwargs):
            raise RuntimeError("500 Internal Server Error")

    bad = Exploding(name="voice", guild=guild)

    class FakeCategory(FakeChannel):
        def __init__(self):
            super().__init__(name="staff", guild=guild)
            self.channels = [good, bad]

    category = FakeCategory()
    monkeypatch.setattr(discord, "CategoryChannel", FakeCategory)
    monkeypatch.setattr(permissions, "client", FakeClient(channel=category))

    result = await permissions.set_category_permissions(
        {"category_id": "1", "target_id": "10", "target_type": "role", "deny": ["view_channel"]}
    )

    text = result[0].text
    assert "500 Internal Server Error" in text
    assert "the category was already updated" in text
    assert "chat" in text
    assert "still have their previous overwrite" in text


@pytest.mark.asyncio
async def test_set_category_permissions_can_skip_children(monkeypatch):
    role = FakeRole()
    guild = FakeGuild(roles_list=[role])
    child = FakeChannel(name="chat", guild=guild)

    class FakeCategory(FakeChannel):
        def __init__(self):
            super().__init__(name="staff", guild=guild)
            self.channels = [child]

    category = FakeCategory()
    monkeypatch.setattr(discord, "CategoryChannel", FakeCategory)
    monkeypatch.setattr(permissions, "client", FakeClient(channel=category))

    result = await permissions.set_category_permissions(
        {
            "category_id": "1",
            "target_id": "10",
            "target_type": "role",
            "sync_children": False,
        }
    )

    assert child.calls == []
    assert "synced" not in result[0].text
