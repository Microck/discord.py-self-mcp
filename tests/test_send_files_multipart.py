"""End-to-end checks against the real discord.py-self multipart builder.

The tool tests use fakes, which cannot prove that the payload the library puts on
the wire is what we intend. These exercise ``discord.http.handle_message_parameters``
directly, with no network.
"""

import asyncio
import io
import json
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from discord.http import handle_message_parameters

from discord_py_self_mcp import file_utils
from discord_py_self_mcp.file_utils import build_files


@pytest.fixture(autouse=True)
def uploads_enabled(tmp_path, monkeypatch):
    root = tmp_path / "uploads"
    root.mkdir(exist_ok=True)
    monkeypatch.setenv("UPLOAD_DIRS", str(root))
    return root


@pytest.fixture
def upload(uploads_enabled):
    path = uploads_enabled / "report.xlsx"
    path.write_bytes(b"sheet-bytes")
    return str(path)


def payload_json(params):
    """The JSON the library posts alongside the file parts."""
    # when a message carries files the payload is serialised into the multipart
    # body and params.payload is set to None
    part = next(p for p in params.multipart if p["name"] == "payload_json")
    return json.loads(part["data"])


def test_attachment_only_send_sends_an_explicit_null(upload):
    files, error = build_files([upload])
    assert error is None

    params = handle_message_parameters(content=None, files=files)

    # this is how discord.py-self represents a caption-less message; an empty
    # string is a different value and is what the tools convert away from
    assert payload_json(params)["content"] is None
    assert len(params.files) == 1


def test_empty_string_caption_is_what_the_tools_avoid(upload):
    files, _ = build_files([upload])

    params = handle_message_parameters(content="", files=files)

    assert payload_json(params)["content"] == ""


def test_caption_and_files_are_both_serialised(upload):
    files, error = build_files([upload])
    assert error is None

    params = handle_message_parameters(content="here you go", files=files)

    assert payload_json(params)["content"] == "here you go"
    assert len(params.files) == 1


def test_uploaded_bytes_are_exactly_what_was_on_disk(upload):
    files, _ = build_files([upload])

    params = handle_message_parameters(content=None, files=files)
    part = next(p for p in params.multipart if p["name"] == "files[0]")

    assert part["filename"] == "report.xlsx"
    assert part["data"].read() == b"sheet-bytes"


@pytest.mark.parametrize("send_fails", [False, True])
async def test_payload_buffer_is_released_after_send(upload, send_fails):
    buffers = []

    async def send(content, *, files):
        with handle_message_parameters(content=content, files=files) as params:
            fp = params.files[0].fp
            buffers.append(fp)
            assert fp.read() == b"sheet-bytes"
            if send_fails:
                raise RuntimeError("upload failed")
        return SimpleNamespace(attachments=[])

    sending = file_utils.send_with_files(
        SimpleNamespace(send=send), "report", [upload], {}, AsyncMock()
    )
    if send_fails:
        with pytest.raises(RuntimeError, match="upload failed"):
            await sending
    else:
        await sending
    assert buffers[0].closed


async def test_cancelled_read_cleans_up_before_reusing_slot(upload, monkeypatch):
    slots = asyncio.Semaphore(1)
    monkeypatch.setattr(file_utils, "_upload_slots", slots)
    ready = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    buffers = []
    real_build = file_utils.build_files

    def build(paths):
        files, error = real_build(paths)
        assert error is None
        if buffers:
            assert buffers[0].closed
        buffers.append(files[0].fp)
        loop.call_soon_threadsafe(ready.set)
        assert release.wait(5)
        return files, error

    monkeypatch.setattr(file_utils, "build_files", build)
    channel = SimpleNamespace(send=AsyncMock())
    limiter = AsyncMock()
    first = asyncio.create_task(file_utils.send_with_files(channel, "one", [upload], {}, limiter))
    try:
        await asyncio.wait_for(ready.wait(), 5)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert slots.locked()
    finally:
        release.set()
    await file_utils.send_with_files(channel, "two", [upload], {}, limiter)
    assert len(buffers) == 2 and all(fp.closed for fp in buffers)
    channel.send.assert_awaited_once()
    limiter.assert_awaited_once_with("message")


def test_later_read_error_closes_prepared_buffers(upload, uploads_enabled, monkeypatch):
    second = uploads_enabled / "later.txt"
    second.write_bytes(b"second")
    buffers = []
    real_file = file_utils.discord.File

    def capture(buffer, **kwargs):
        buffers.append(buffer)
        return real_file(buffer, **kwargs)

    def fail_later(path, mode):
        if path == str(second):
            raise PermissionError("read failed")
        return io.open(path, mode)

    monkeypatch.setattr(file_utils.discord, "File", capture)
    monkeypatch.setattr(file_utils, "open", fail_later, raising=False)
    files, error = build_files([upload, str(second)])
    assert files == [] and error
    assert len(buffers) == 1 and buffers[0].closed


def test_source_descriptors_are_closed_after_building(upload, monkeypatch):
    # files are read into memory, so nothing stays open for the lifetime of the
    # send and there is nothing to close on an early return
    opened = []
    real_open = io.open

    def recording_open(f, *a, **kw):
        handle = real_open(f, *a, **kw)
        opened.append(handle)
        return handle

    monkeypatch.setattr(file_utils, "open", recording_open, raising=False)
    files, error = build_files([upload])

    assert error is None
    assert len(files) == 1
    # the payload is an in-memory buffer, not a live file handle
    assert hasattr(files[0].fp, "getvalue")
    # and every descriptor opened on the way in is closed again
    assert opened and all(handle.closed for handle in opened)


def test_in_memory_file_matches_the_path_form(uploads_enabled):
    """The tools hand the library a BytesIO rather than a pathname.

    That is only safe while discord.File treats the two forms equivalently, so the
    properties the upload path depends on are pinned here against the real class.
    """
    import hashlib

    import discord

    payload = b"the-exact-bytes"
    path = uploads_enabled / "report.xlsx"
    path.write_bytes(payload)

    from_path = discord.File(str(path))
    built, error = build_files([str(path)])
    assert error is None
    assert len(built) == 1
    from_memory = built[0]

    assert from_memory.filename == from_path.filename == "report.xlsx"
    assert from_memory.size == from_path.size == len(payload)
    assert from_memory.md5.hexdigest() == hashlib.md5(payload).hexdigest()
    assert from_memory.to_upload_dict(0) == from_path.to_upload_dict(0)

    # http.py retries uploads by calling reset(seek=tries); each attempt must see
    # the whole file from the start
    for tries in (0, 1, 2):
        from_memory.reset(seek=tries)
        assert from_memory.fp.read() == payload

    # the buffer is not owned by the File, so the library closing it cannot
    # invalidate a retry
    assert from_memory._owner is False
    from_memory.close()
    from_memory.reset(seek=1)
    assert from_memory.fp.read() == payload


def test_build_files_rejects_relative_paths_without_reading(uploads_enabled, monkeypatch):
    (uploads_enabled / "here.txt").write_bytes(b"x")
    monkeypatch.chdir(uploads_enabled)

    files, error = build_files(["here.txt"])

    assert files == []
    assert error.startswith("file_paths must be absolute")
