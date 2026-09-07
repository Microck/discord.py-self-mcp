import base64
import json

import pytest
from discord_protos import PreloadedUserSettings

from discord_py_self_mcp.tools import folders


class FakeGuild:
    def __init__(self, guild_id, name):
        self.id = guild_id
        self.name = name


class FakeHTTP:
    def __init__(self, settings, *, out_of_date=False):
        self.settings = settings
        self.out_of_date = out_of_date
        self.calls = []

    async def request(self, route, *, json=None):
        self.calls.append((route, json))
        if route.method == "GET":
            return {"settings": _encode(self.settings)}
        return {"out_of_date": self.out_of_date}


class FakeClient:
    def __init__(self, settings):
        self.http = FakeHTTP(settings)
        self.guilds = [
            FakeGuild(1, "One"),
            FakeGuild(2, "Two"),
            FakeGuild(3, "Three"),
            FakeGuild(4, "Four"),
        ]

    def is_ready(self):
        return True


def _encode(settings):
    return base64.b64encode(settings.SerializeToString()).decode("ascii")


def _decode_patch(client):
    route, payload = client.http.calls[-1]
    assert route.method == "PATCH"
    return PreloadedUserSettings.FromString(base64.b64decode(payload["settings"])), payload


def _settings():
    settings = PreloadedUserSettings()
    settings.versions.data_version = 17
    work = settings.guild_folders.folders.add()
    work.guild_ids.extend([1, 2])
    work.id.value = 700
    work.name.value = "Work"
    root = settings.guild_folders.folders.add()
    root.guild_ids.append(3)
    return settings


async def _no_rate_limit(action_type):
    return None


@pytest.mark.asyncio
async def test_list_server_folders_returns_current_layout_with_guild_names(monkeypatch):
    fake_client = FakeClient(_settings())
    monkeypatch.setattr(folders, "client", fake_client)

    result = await folders.list_server_folders({})

    payload = json.loads(result[0].text)
    assert payload["folders"][0] == {
        "folder_id": "700",
        "name": "Work",
        "color": None,
        "guild_ids": ["1", "2"],
        "guilds": [{"id": "1", "name": "One"}, {"id": "2", "name": "Two"}],
    }
    assert len(fake_client.http.calls) == 1
    assert fake_client.http.calls[0][0].method == "GET"


@pytest.mark.asyncio
async def test_create_server_folder_preserves_other_folders_and_data_version(monkeypatch):
    fake_client = FakeClient(_settings())
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)
    monkeypatch.setattr(folders.secrets, "randbelow", lambda maximum: 900)

    result = await folders.create_server_folder(
        {"name": "Games", "guild_ids": ["2", "3"], "color": "#5865F2"}
    )

    saved, request = _decode_patch(fake_client)
    assert result[0].text == "Created server folder 'Games' (id=901) with 2 server(s)"
    assert request["required_data_version"] == 17
    assert [(list(folder.guild_ids), folders._folder_id(folder)) for folder in saved.guild_folders.folders] == [
        ([1], 700),
        ([2, 3], 901),
    ]
    created = saved.guild_folders.folders[1]
    assert created.name.value == "Games"
    assert created.color.value == 0x5865F2


@pytest.mark.asyncio
async def test_move_server_to_folder_preserves_destination_and_other_entries(monkeypatch):
    settings = _settings()
    other = settings.guild_folders.folders.add()
    other.guild_ids.append(4)
    other.id.value = 800
    other.name.value = "Other"
    fake_client = FakeClient(settings)
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)

    result = await folders.move_server_to_folder({"guild_id": "1", "folder_id": "800"})

    saved, _ = _decode_patch(fake_client)
    assert result[0].text == "Moved server 1 to folder 800"
    assert [(list(folder.guild_ids), folders._folder_id(folder)) for folder in saved.guild_folders.folders] == [
        ([2], 700),
        ([3], None),
        ([4, 1], 800),
    ]


@pytest.mark.asyncio
async def test_move_server_without_folder_makes_it_ungrouped(monkeypatch):
    fake_client = FakeClient(_settings())
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)

    result = await folders.move_server_to_folder({"guild_id": "2"})

    saved, _ = _decode_patch(fake_client)
    assert result[0].text == "Moved server 2 to the ungrouped sidebar"
    assert [(list(folder.guild_ids), folders._folder_id(folder)) for folder in saved.guild_folders.folders] == [
        ([1], 700),
        ([3], None),
        ([2], None),
    ]


@pytest.mark.asyncio
async def test_move_server_already_in_single_member_destination_is_idempotent(monkeypatch):
    settings = PreloadedUserSettings()
    folder = settings.guild_folders.folders.add()
    folder.guild_ids.append(1)
    folder.id.value = 700
    fake_client = FakeClient(settings)
    monkeypatch.setattr(folders, "client", fake_client)

    result = await folders.move_server_to_folder({"guild_id": "1", "folder_id": "700"})

    assert result[0].text == "Server 1 is already in folder 700"
    assert [call[0].method for call in fake_client.http.calls] == ["GET"]


@pytest.mark.asyncio
async def test_rename_server_folder(monkeypatch):
    fake_client = FakeClient(_settings())
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)

    result = await folders.rename_server_folder({"folder_id": "700", "name": "Projects"})

    saved, _ = _decode_patch(fake_client)
    assert result[0].text == "Renamed folder 700 to 'Projects'"
    assert saved.guild_folders.folders[0].name.value == "Projects"


@pytest.mark.asyncio
async def test_reorder_server_folders_requires_complete_current_layout(monkeypatch):
    fake_client = FakeClient(_settings())
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)

    result = await folders.reorder_server_folders(
        {"folder_order": [{"guild_ids": ["3"]}, {"folder_id": "700"}]}
    )

    saved, _ = _decode_patch(fake_client)
    assert result[0].text == "Reordered server folders"
    assert [(list(folder.guild_ids), folders._folder_id(folder)) for folder in saved.guild_folders.folders] == [
        ([3], None),
        ([1, 2], 700),
    ]


@pytest.mark.asyncio
async def test_save_reports_concurrent_settings_change(monkeypatch):
    fake_client = FakeClient(_settings())
    fake_client.http.out_of_date = True
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)

    result = await folders.rename_server_folder({"folder_id": "700", "name": "Projects"})

    assert "changed on another Discord client" in result[0].text


@pytest.mark.asyncio
async def test_apply_server_folder_layout_dry_run_reports_changes_without_saving(monkeypatch):
    fake_client = FakeClient(_settings())
    monkeypatch.setattr(folders, "client", fake_client)

    result = await folders.apply_server_folder_layout(
        {
            "folders": [
                {
                    "folder_id": "700",
                    "name": "Projects",
                    "color": "#5865F2",
                    "guild_ids": ["3"],
                }
            ],
            "ungrouped_guild_ids": ["2"],
            "dry_run": True,
        }
    )

    plan = json.loads(result[0].text)
    assert plan["dry_run"] is True
    assert plan["will_rename"] == [{"from": "Work", "to": "Projects"}]
    assert {move["guild_id"] for move in plan["will_move"]} == {"2", "3"}
    assert [call[0].method for call in fake_client.http.calls] == ["GET"]


@pytest.mark.asyncio
async def test_apply_server_folder_layout_saves_once_and_preserves_unlisted_servers(monkeypatch):
    fake_client = FakeClient(_settings())
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)
    monkeypatch.setattr(folders.secrets, "randbelow", lambda maximum: 900)

    result = await folders.apply_server_folder_layout(
        {"folders": [{"name": "Games", "guild_ids": ["2", "3"]}]}
    )

    plan = json.loads(result[0].text)
    saved, _ = _decode_patch(fake_client)
    assert plan["dry_run"] is False
    assert plan["will_create"] == ["Games"]
    assert [(list(folder.guild_ids), folders._folder_id(folder)) for folder in saved.guild_folders.folders] == [
        ([2, 3], 901),
        ([1], 700),
    ]


@pytest.mark.asyncio
async def test_reorder_server_folders_accepts_compact_folder_ids(monkeypatch):
    settings = _settings()
    other = settings.guild_folders.folders.add()
    other.guild_ids.append(4)
    other.id.value = 800
    fake_client = FakeClient(settings)
    monkeypatch.setattr(folders, "client", fake_client)
    monkeypatch.setattr(folders, "apply_rate_limit", _no_rate_limit)

    result = await folders.reorder_server_folders({"folder_ids": ["800", "700"]})

    saved, _ = _decode_patch(fake_client)
    assert result[0].text == "Reordered server folders"
    assert [(list(folder.guild_ids), folders._folder_id(folder)) for folder in saved.guild_folders.folders] == [
        ([4], 800),
        ([3], None),
        ([1, 2], 700),
    ]
