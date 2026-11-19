"""The npm scripts can be updated independently of the installed Python package."""

import io
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from textwrap import dedent

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def packaged_scripts(tmp_path):
    # Use the actual pre-upload release. Its regular package takes precedence
    # over the test runner's editable install in the fresh interpreter.
    if not shutil.which("git") or not (ROOT / ".git").exists():
        pytest.skip("the packaged-script compatibility test needs a git checkout")
    tag = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "refs/tags/v1.8.1"],
        cwd=ROOT, capture_output=True,
    )
    if tag.returncode:
        pytest.skip("fetch tag v1.8.1 to run the packaged-script compatibility test")
    archive = subprocess.run(
        ["git", "archive", "--format=zip", "v1.8.1", "discord_py_self_mcp"],
        cwd=ROOT, capture_output=True, check=True,
    )
    installed = tmp_path / "site-packages"
    with zipfile.ZipFile(io.BytesIO(archive.stdout)) as release:
        release.extractall(installed)
    scripts = tmp_path / "npm" / "scripts"
    scripts.mkdir(parents=True)
    for script in ("dcli.py", "daemon.py"):
        shutil.copyfile(ROOT / "scripts" / script, scripts / script)
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(map(str, (installed, scripts))),
        "XDG_RUNTIME_DIR": str(tmp_path / "runtime"),
    }

    def run(*args):
        result = subprocess.run(
            [sys.executable, *args], cwd=tmp_path, env=env, capture_output=True,
            text=True, timeout=90,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    return scripts, run


def test_packaged_cli_can_inspect_daemon_with_previous_release(packaged_scripts):
    scripts, run = packaged_scripts
    assert "Daemon is not running" in run(scripts / "dcli.py", "daemon", "status")


@pytest.mark.parametrize("source", ["disabled", "installed", "inherited"])
def test_packaged_daemon_reads_only_trusted_upload_settings(tmp_path, source):
    scripts = tmp_path / "npm" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts" / "daemon.py", scripts / "daemon.py")
    installed = tmp_path / "python"
    shutil.copytree(
        ROOT / "discord_py_self_mcp", installed / "discord_py_self_mcp",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    if source != "disabled":
        (installed / ".env").write_text(
            f"UPLOAD_DIRS='{allowed.as_posix()}'\n"
            "TEST_INSTALL_LIMIT=1024\nMAX_UPLOAD_BYTES=${TEST_INSTALL_LIMIT}\n",
            encoding="utf-8",
        )
    (tmp_path / ".env").write_text(
        f"UPLOAD_DIRS='{tmp_path.as_posix()}'\nuPloAd_Dirs='{tmp_path.as_posix()}'\n"
        "MAX_UPLOAD_BYTES=1234\nMax_Upload_Bytes=1234\nMax_Upload_Total_Bytes=2468\n"
        "TEST_INSTALL_LIMIT=5678\nLEGACY_SETTING=yes\n",
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(map(str, (scripts, installed)))}
    for name in ("UPLOAD_DIRS", "MAX_UPLOAD_BYTES", "MAX_UPLOAD_TOTAL_BYTES",
                 "TEST_INSTALL_LIMIT", "LEGACY_SETTING", "PYTHON_DOTENV_DISABLED"):
        env.pop(name, None)
    expected = [] if source == "disabled" else [str(allowed)]
    if source == "inherited":
        inherited = tmp_path / "operator"
        inherited.mkdir()
        env["UPLOAD_DIRS"] = str(inherited)
        expected = [str(inherited)]
    result = subprocess.run(
        [sys.executable, "-c", dedent(f"""\
            import os
            import daemon
            from discord_py_self_mcp import file_utils
            assert os.environ["LEGACY_SETTING"] == "yes"
            assert file_utils._upload_roots() == {expected!r}
            assert file_utils.max_upload_bytes() == {8 * 1024 ** 2 if source == "disabled" else 1024}
            assert file_utils.max_upload_total_bytes() == file_utils.MAX_UPLOAD_TOTAL_BYTES_DEFAULT
        """)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stderr


def test_packaged_daemon_with_previous_release_only_refuses_uploads(packaged_scripts):
    _, run = packaged_scripts
    run("-c", dedent("""\
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, Mock

        import daemon

        channel = Mock(spec=daemon.discord.abc.Messageable)
        channel.send = AsyncMock(return_value=SimpleNamespace(id=42))
        server = daemon.DiscordDaemon.__new__(daemon.DiscordDaemon)
        server.client = Mock()
        server.client.get_channel.return_value = channel
        args = {"channel_id": 1, "content": "hello"}
        plain = asyncio.run(server.handle_command({"command": "send_message", "args": args}))
        assert plain == {"message_id": 42, "success": True}, plain
        upload = asyncio.run(server.handle_command({
            "command": "send_message_with_files", "args": {**args, "file_paths": ["notes.txt"]},
        }))
        assert "file attachments are unavailable" in upload["error"], upload
        channel.send.assert_awaited_once_with("hello")
    """))
