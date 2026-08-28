import json
from datetime import datetime, timezone

import pytest
from discord_protos import PreloadedUserSettings

from discord_py_self_mcp.tools import channels, folders, overview


class FakeUser:
    def __init__(self, user_id=99, name="self"):
        self.id = user_id
        self.name = name
        self.global_name = None
        self.discriminator = "0"


class FakePermissions:
    administrator = False
    manage_guild = True
    manage_channels = True
    manage_messages = True


class FakeMe:
    guild_permissions = FakePermissions()


class FakeCategory:
    def __init__(self, name):
        self.name = name


class FakeType:
    def __init__(self, name):
        self.name = name


class FakeAsyncIterator:
    def __init__(self, values):
        self.values = iter(values)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.values)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeMessage:
    def __init__(self, message_id, content):
        self.id = message_id
        self.content = content
        self.clean_content = content
        self.author = FakeUser(200, "author")
        self.created_at = datetime(2026, 8, 28, tzinfo=timezone.utc)


class FakeChannel:
    def __init__(self, channel_id, name, type_name="text", category=None, messages=None):
        self.id = channel_id
        self.name = name
        self.type = FakeType(type_name)
        self.category = FakeCategory(category) if category else None
        self.messages = messages or []

    def history(self, *, limit):
        return FakeAsyncIterator(self.messages[:limit])


class FakeGuild:
    def __init__(self, guild_id, name, channels):
        self.id = guild_id
        self.name = name
        self.channels = channels
        self.description = "A useful server"
        self.member_count = 42
        self.me = FakeMe()
        self.owner_id = 99


class FakeClient:
    def __init__(self, guilds):
        self.guilds = guilds
        self.user = FakeUser()

    def is_ready(self):
        return True

    def get_guild(self, guild_id):
        return next((guild for guild in self.guilds if guild.id == guild_id), None)


def _settings():
    settings = PreloadedUserSettings()
    folder = settings.guild_folders.folders.add()
    folder.id.value = 700
    folder.name.value = "Projects"
    folder.guild_ids.append(1)
    return settings


@pytest.mark.asyncio
async def test_get_server_overviews_returns_compact_metadata_and_folder(monkeypatch):
    guild = FakeGuild(
        1,
        "Example",
        [
            FakeChannel(10, "general", category="Community"),
            FakeChannel(11, "ticket-100", category="Support"),
            FakeChannel(12, "ticket-101", category="Support"),
            FakeChannel(13, "ticket-102", category="Support"),
        ],
    )
    fake_client = FakeClient([guild])
    monkeypatch.setattr(overview, "client", fake_client)
    monkeypatch.setattr(folders, "client", fake_client)

    async def get_settings():
        return _settings()

    monkeypatch.setattr(overview, "_get_settings", get_settings)
    result = await overview.get_server_overviews({"guild_ids": ["1"]})

    payload = json.loads(result[0].text)
    server = payload["servers"][0]
    assert server["folder"] == {"id": "700", "name": "Projects", "color": None}
    assert server["description"] == "A useful server"
    assert server["permissions"]["owner"] is True
    assert server["channel_summary"]["notable_channels"][0]["name"] == "general"
    assert server["channel_summary"]["repetitive_channels"] == [{"pattern": "ticket-*", "count": 3}]


@pytest.mark.asyncio
async def test_sample_server_content_prefers_general_and_skips_ticket_channels(monkeypatch):
    general = FakeChannel(10, "general", messages=[FakeMessage(1, "Useful update")])
    ticket = FakeChannel(11, "ticket-123", messages=[FakeMessage(2, "Ignore me")])
    guild = FakeGuild(1, "Example", [ticket, general])
    fake_client = FakeClient([guild])
    rate_limit_calls = []
    monkeypatch.setattr(overview, "client", fake_client)

    async def rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(overview, "apply_rate_limit", rate_limit)
    result = await overview.sample_server_content(
        {"guild_ids": ["1"], "messages_per_guild": 5}
    )

    payload = json.loads(result[0].text)
    samples = payload["servers"][0]["recent_message_samples"]
    assert samples == [
        {
            "channel_id": "10",
            "channel_name": "general",
            "message_id": "1",
            "author": "author",
            "created_at": "2026-08-28T00:00:00+00:00",
            "content": "Useful update",
        }
    ]
    assert rate_limit_calls == ["action"]


@pytest.mark.asyncio
async def test_list_channels_supports_bulk_summary_mode(monkeypatch):
    guild = FakeGuild(1, "Example", [FakeChannel(10, "general", category="Community")])
    fake_client = FakeClient([guild])
    monkeypatch.setattr(channels, "client", fake_client)

    result = await channels.list_channels({"guild_ids": ["1"], "mode": "summary"})

    payload = json.loads(result[0].text)
    assert payload == {
        "guilds": [
            {
                "guild_id": "1",
                "guild_name": "Example",
                "channel_summary": {
                    "categories": ["Community"],
                    "notable_channels": [
                        {"id": "10", "name": "general", "type": "text", "category": "Community"}
                    ],
                    "counts": {"text": 1},
                    "repetitive_channels": [],
                },
            }
        ]
    }
