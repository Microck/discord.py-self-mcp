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
