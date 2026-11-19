import os

import pytest

from scripts import dcli


def test_cmd_get_message_attachments_saves_requested_downloads(
    monkeypatch, tmp_path, capsys
):
    def fake_send_request(payload):
        assert payload == {
            "command": "get_message_attachments",
            "args": {
                "channel_id": 123,
                "message_id": 456,
                "download_content": True,
            },
        }
        return {
            "message_id": 456,
            "attachments": [
                {
                    "index": 0,
                    "filename": "photo.png",
                    "content_type": "image/png",
                    "size": 12,
                    "url": "https://cdn.discordapp.com/photo.png",
                }
            ],
            "downloads": [
                {
                    "index": 0,
                    "filename": "photo.png",
                    "content_type": "image/png",
                    "content_base64": "aGVsbG8=",
                }
            ],
        }

    monkeypatch.setattr(dcli, "send_request", fake_send_request)

    dcli.cmd_get_message_attachments(
        123, 456, download=True, output_dir=str(tmp_path)
    )

    output = capsys.readouterr().out
    saved_file = tmp_path / "attachment-0-photo.png"

    assert saved_file.read_bytes() == b"hello"
    assert "Found 1 attachment(s) on message 456" in output
    assert str(saved_file) in output


def test_cmd_get_message_attachments_requires_output_dir_when_downloading(capsys):
    dcli.cmd_get_message_attachments(123, 456, download=True)

    assert (
        "Error: --output-dir is required when --download is used"
        in capsys.readouterr().out
    )


def test_cmd_send_message_plain_text_uses_the_text_command(monkeypatch, capsys):
    calls = []

    def fake_send_request(payload, timeout=None):
        calls.append((payload, timeout))
        return {"message_id": 999, "success": True}

    monkeypatch.setattr(dcli, "send_request", fake_send_request)

    dcli.cmd_send_message(123, "hello")

    payload, timeout = calls[0]
    assert payload == {
        "command": "send_message",
        "args": {"channel_id": 123, "content": "hello"},
    }
    assert timeout is None
    assert "Message sent (ID: 999)" in capsys.readouterr().out


def test_cmd_send_message_with_files_uses_a_dedicated_command(
    monkeypatch, tmp_path, capsys
):
    calls = []

    def fake_send_request(payload, timeout=None):
        calls.append((payload, timeout))
        return {"message_id": 999, "success": True, "attachments": ["notes.txt"]}

    monkeypatch.setattr(dcli, "send_request", fake_send_request)
    (tmp_path / "notes.txt").write_bytes(b"hi")

    dcli.cmd_send_message(123, "report", file_paths=[str(tmp_path / "notes.txt")])

    payload, timeout = calls[0]
    assert payload["command"] == "send_message_with_files"
    assert payload["args"]["file_paths"] == [str(tmp_path / "notes.txt")]
    assert timeout == dcli.UPLOAD_TIMEOUT_SECONDS

    out = capsys.readouterr().out
    assert "Message sent (ID: 999)" in out
    assert "Attachments (1): notes.txt" in out


def test_cmd_send_message_absolutises_relative_paths(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        dcli,
        "send_request",
        lambda payload, timeout=None: calls.append(payload)
        or {"message_id": 1, "success": True},
    )
    monkeypatch.chdir(tmp_path)

    dcli.cmd_send_message(123, "x", file_paths=["notes.txt"])

    sent = calls[0]["args"]["file_paths"]
    assert sent == [str(tmp_path / "notes.txt")]


def test_cmd_send_message_keeps_dotdot_in_a_relative_path(monkeypatch, tmp_path):
    # abspath() collapses "..", which can change the intended file when a leading
    # component is a directory symlink, so the spelling must survive
    calls = []
    monkeypatch.setattr(
        dcli,
        "send_request",
        lambda payload, timeout=None: calls.append(payload)
        or {"message_id": 1, "success": True},
    )
    monkeypatch.chdir(tmp_path)

    dcli.cmd_send_message(123, "x", file_paths=[os.path.join("a", "..", "notes.txt")])

    sent = calls[0]["args"]["file_paths"]
    assert sent == [os.path.join(str(tmp_path), "a", "..", "notes.txt")]
    assert ".." in sent[0]


def test_cmd_send_message_keeps_absolute_path_spelling_intact(monkeypatch, tmp_path):
    # abspath() collapses "..", which can change the intended file when a leading
    # component is a directory symlink, so absolute spellings are preserved
    calls = []
    monkeypatch.setattr(
        dcli,
        "send_request",
        lambda payload, timeout=None: calls.append(payload)
        or {"message_id": 1, "success": True},
    )

    spelling = str(tmp_path / "a" / ".." / "notes.txt")
    dcli.cmd_send_message(123, "x", file_paths=[spelling])

    assert calls[0]["args"]["file_paths"] == [spelling]


@pytest.mark.skipif(os.name != "nt", reason="Windows drive-relative paths")
def test_cmd_send_message_rejects_drive_relative_paths(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        dcli,
        "send_request",
        lambda payload, timeout=None: calls.append(payload)
        or {"message_id": 1, "success": True},
    )

    # isabs() says yes to both, but they resolve against the daemon's drive
    for spelling in ("\\notes.txt", "D:notes.txt"):
        with pytest.raises(SystemExit):
            dcli.cmd_send_message(123, "x", file_paths=[spelling])

    assert calls == []
    assert "not fully qualified" in capsys.readouterr().out


def test_cmd_send_message_accepts_a_fully_qualified_windows_path(monkeypatch):
    if os.name != "nt":
        pytest.skip("Windows path form")

    calls = []
    monkeypatch.setattr(
        dcli,
        "send_request",
        lambda payload, timeout=None: calls.append(payload)
        or {"message_id": 1, "success": True},
    )

    dcli.cmd_send_message(123, "x", file_paths=["C:\\uploads\\notes.txt"])

    assert calls[0]["args"]["file_paths"] == ["C:\\uploads\\notes.txt"]


def test_cmd_send_message_rejects_empty_file_path(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        dcli,
        "send_request",
        lambda payload, timeout=None: calls.append(payload)
        or {"message_id": 1, "success": True},
    )

    with pytest.raises(SystemExit):
        dcli.cmd_send_message(123, "x", file_paths=[""])

    # abspath("") would have become the working directory, i.e. a real path
    assert calls == []
    assert "non-empty path" in capsys.readouterr().out


def test_cmd_send_message_against_old_daemon_sends_nothing(
    monkeypatch, capsys, tmp_path
):
    calls = []

    def old_daemon(payload, timeout=None):
        calls.append(payload["command"])
        # a daemon from before file support does not know the command
        return {"error": f"Unknown command: {payload['command']}"}

    monkeypatch.setattr(dcli, "send_request", old_daemon)

    with pytest.raises(SystemExit):
        dcli.cmd_send_message(
            123, "report", file_paths=[os.path.join(str(tmp_path), "notes.txt")]
        )

    out = capsys.readouterr().out
    assert "does not support file attachments" in out
    assert calls == ["send_message_with_files"]


def test_cmd_send_message_propagates_a_real_error(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        dcli,
        "send_request",
        lambda payload, timeout=None: {"error": "File not found: Unknown command.txt"},
    )

    with pytest.raises(SystemExit):
        dcli.cmd_send_message(
            123, "x", file_paths=[os.path.join(str(tmp_path), "missing.png")]
        )

    assert "File not found: Unknown command.txt" in capsys.readouterr().out
