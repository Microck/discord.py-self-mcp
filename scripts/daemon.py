"""
Discord CLI Daemon - Persistent Discord connection with auto-reload
Usage: python3 daemon.py <start|stop|restart|status>
Auto-restart on code change: Enabled
"""

import asyncio
import hashlib
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from secrets import compare_digest

env_paths = [
    Path(__file__).parent.parent / ".env",
    Path.cwd() / ".env",
]

for env_path in env_paths:
    if env_path.exists():
        from dotenv import load_dotenv

        load_dotenv(env_path)
        break

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("Error: DISCORD_TOKEN not found in .env file")
    sys.exit(1)

import discord

from discord_py_self_mcp.cli_runtime import (
    AUTH_FILE,
    LOG_FILE,
    PID_FILE,
    SOCKET_PATH,
    chmod_private,
    ensure_runtime_dir,
)
from discord_py_self_mcp.logging_utils import log_to_stderr
from discord_py_self_mcp.tool_utils import NON_MESSAGEABLE_TEXT, validate_message_content
from discord_py_self_mcp.tools.embed import serialize_message

SCRIPT_DIR = Path(__file__).parent
DAEMON_SCRIPT = SCRIPT_DIR / "daemon.py"
CHECK_INTERVAL = 2


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _load_or_create_auth_token() -> str:
    ensure_runtime_dir()
    if AUTH_FILE.exists():
        token = AUTH_FILE.read_text(encoding="utf-8").strip()
        if token:
            chmod_private(AUTH_FILE)
            return token

    token = secrets.token_hex(32)
    AUTH_FILE.write_text(token, encoding="utf-8")
    chmod_private(AUTH_FILE)
    return token


class DiscordDaemon:
    def __init__(self):
        self.client = discord.Client()
        self._connected = asyncio.Event()
        self._shutdown = asyncio.Event()
        self.server = None
        self.responses = {}
        self.last_code_hash = None
        self.code_check_task = None
        self.auth_token = _load_or_create_auth_token()

    def _parse_after_time(self, after_str):
        """Parse CLI time input into a timezone-aware datetime."""
        if not after_str:
            return None

        try:
            timestamp = int(after_str)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError):
            pass

        if isinstance(after_str, str) and after_str[-1] in ["h", "m", "d"]:
            try:
                value = int(after_str[:-1])
                unit = after_str[-1]
                now = datetime.now(timezone.utc)
                if unit == "h":
                    return now - timedelta(hours=value)
                if unit == "m":
                    return now - timedelta(minutes=value)
                if unit == "d":
                    return now - timedelta(days=value)
            except (ValueError, IndexError):
                pass

        try:
            return datetime.fromisoformat(after_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _history_after_object(self, after_value):
        if isinstance(after_value, datetime):
            after_dt = after_value
        else:
            after_dt = self._parse_after_time(after_value)
        if not after_dt:
            return None
        return discord.Object(id=discord.utils.time_snowflake(after_dt))

    def get_code_hash(self):
        """Calculate a stable hash of daemon.py to detect changes."""
        if not DAEMON_SCRIPT.exists():
            return None
        with open(DAEMON_SCRIPT, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

    async def monitor_code_changes(self):
        """Monitor daemon.py for changes and auto-restart."""
        self.last_code_hash = self.get_code_hash()
        while not self._shutdown.is_set():
            await asyncio.sleep(CHECK_INTERVAL)
            current_hash = self.get_code_hash()
            if current_hash != self.last_code_hash:
                log_to_stderr(
                    f"[{datetime.now()}] Code change detected. Restarting daemon..."
                )
                await self.restart_daemon()
                return

    async def restart_daemon(self):
        """Restart the daemon process."""
        for req_id in list(self.responses.keys()):
            self.responses[req_id] = {"error": "Daemon restarting due to code changes"}

        self._shutdown.set()
        await self.client.close()
        _safe_unlink(SOCKET_PATH)

        subprocess.Popen(
            [sys.executable, str(DAEMON_SCRIPT), "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        os._exit(0)

    async def connect(self):
        """Connect to Discord and wait for the initial ready signal."""

        @self.client.event
        async def on_ready():
            log_to_stderr(f"[{datetime.now()}] Connected as {self.client.user}")
            self._connected.set()

        @self.client.event
        async def on_disconnect():
            log_to_stderr(f"[{datetime.now()}] Disconnected from Discord")

        asyncio.create_task(self.client.start(TOKEN))
        await asyncio.wait_for(self._connected.wait(), timeout=30)

    async def handle_command(self, command_data):
        """Execute a command and return a JSON-serializable result."""
        cmd = command_data.get("command")
        args = command_data.get("args", {})

        try:
            if cmd == "list_guilds":
                return self._list_guilds()
            if cmd == "list_channels":
                return await self._list_channels(args.get("guild_id"))
            if cmd == "read_messages":
                return await self._read_messages(
                    args.get("channel_id"), args.get("limit", 10), args.get("after")
                )
            if cmd == "send_message":
                return await self._send_message(
                    args.get("channel_id"), args.get("content")
                )
            if cmd == "list_threads":
                return await self._list_threads(
                    args.get("channel_id"), args.get("archived", False)
                )
            if cmd == "read_thread":
                return await self._read_thread(
                    args.get("thread_id"), args.get("limit", 50), args.get("after")
                )
            if cmd == "list_guild_threads":
                return self._list_guild_threads(args.get("guild_id"))
            if cmd == "list_recent_threads":
                return self._list_recent_threads(
                    args.get("guild_id"), args.get("within_hours", 24)
                )
            if cmd == "read_recent_threads":
                return await self._read_recent_threads(
                    args.get("guild_id"),
                    args.get("within_hours", 4),
                    args.get("limit_per_thread", 30),
                )
            if cmd == "delete_message":
                return await self._delete_message(
                    args.get("channel_id"), args.get("message_id")
                )
            if cmd == "pin_message":
                return await self._pin_message(
                    args.get("channel_id"), args.get("message_id")
                )
            if cmd == "get_thread_info":
                return self._get_thread_info(args.get("thread_id"))
            if cmd == "archive_thread":
                return await self._archive_thread(
                    args.get("thread_id"), args.get("unarchive", False)
                )
            if cmd == "join_thread":
                return await self._join_thread(args.get("thread_id"))
            if cmd == "leave_thread":
                return await self._leave_thread(args.get("thread_id"))
            if cmd == "user_info":
                return self._get_user_info(args.get("user_id"))
            if cmd == "create_thread":
                return await self._create_thread(
                    args.get("channel_id"),
                    args.get("name"),
                    args.get("message_id"),
                    args.get("content"),
                )
            return {"error": f"Unknown command: {cmd}"}
        except Exception as exc:
            return {"error": str(exc)}

    def _list_guilds(self):
        guilds = []
        for guild in self.client.guilds:
            guilds.append(
                {
                    "id": guild.id,
                    "name": guild.name,
                    "member_count": guild.member_count,
                    "channel_count": len(guild.channels),
                }
            )
        return {"guilds": guilds}

    async def _list_channels(self, guild_id):
        guild = self.client.get_guild(guild_id)
        if not guild:
            try:
                guild = await self.client.fetch_guild(guild_id)
            except discord.NotFound:
                return {"error": "Guild not found"}
            except discord.HTTPException as exc:
                return {"error": f"Failed to fetch guild: {exc}"}

        channels = []
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channels.append({"id": channel.id, "name": channel.name})
        return {"channels": channels}

    async def _read_messages(self, channel_id, limit, after=None):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(
            channel_id
        )
        if not channel:
            return {"error": "Channel not found"}
        if not isinstance(channel, discord.abc.Messageable):
            return {"error": NON_MESSAGEABLE_TEXT}

        history_after = self._history_after_object(after)
        kwargs = {"limit": limit}
        if history_after:
            kwargs["after"] = history_after

        messages = []
        async for msg in channel.history(**kwargs):
            messages.append(serialize_message(msg))
        messages.reverse()
        return {"messages": messages}

    async def _send_message(self, channel_id, content):
        content_error = validate_message_content(content or "")
        if content_error:
            return {"error": content_error}

        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(
            channel_id
        )
        if not channel:
            return {"error": "Channel not found"}
        if not isinstance(channel, discord.abc.Messageable):
            return {"error": NON_MESSAGEABLE_TEXT}

        message = await channel.send(content)
        return {"message_id": message.id, "success": True}

    async def _list_threads(self, channel_id, archived=False):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(
            channel_id
        )
        if not channel:
            return {"error": "Channel not found"}

        threads = []
        for thread in channel.threads:
            threads.append({"id": thread.id, "name": thread.name, "status": "Active"})

        if archived:
            try:
                async for thread in channel.archived_threads(limit=100):
                    threads.append(
                        {"id": thread.id, "name": thread.name, "status": "Archived"}
                    )
            except (discord.Forbidden, discord.HTTPException) as exc:
                log_to_stderr(
                    f"[{datetime.now()}] Warning: failed to fetch archived threads: {exc}"
                )

        return {"threads": threads}

    async def _read_thread(self, thread_id, limit, after=None):
        thread = self.client.get_channel(thread_id) or await self.client.fetch_channel(
            thread_id
        )
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        history_after = self._history_after_object(after)
        kwargs = {"limit": limit}
        if history_after:
            kwargs["after"] = history_after

        messages = []
        async for msg in thread.history(**kwargs):
            messages.append(serialize_message(msg))
        messages.reverse()
        return {"messages": messages, "thread_name": thread.name}

    def _list_guild_threads(self, guild_id):
        guild = self.client.get_guild(guild_id)
        if not guild:
            return {"error": "Guild not found"}

        threads = []
        for thread in guild.threads:
            threads.append(
                {
                    "id": thread.id,
                    "name": thread.name,
                    "parent": thread.parent.name if thread.parent else "Unknown",
                }
            )
        return {"threads": threads}

    def _list_recent_threads(self, guild_id, within_hours=24):
        guild = self.client.get_guild(guild_id)
        if not guild:
            return {"error": "Guild not found"}

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=within_hours)
        threads = []
        for thread in guild.threads:
            last_message_time = None
            if thread.last_message:
                last_message_time = thread.last_message.created_at

            if last_message_time and last_message_time >= cutoff_time:
                threads.append(
                    {
                        "id": thread.id,
                        "name": thread.name,
                        "parent": thread.parent.name if thread.parent else "Unknown",
                        "last_message_at": last_message_time.isoformat(),
                        "message_count": thread.message_count,
                    }
                )

        threads.sort(key=lambda item: item["last_message_at"], reverse=True)
        return {"threads": threads}

    async def _read_recent_threads(self, guild_id, within_hours=4, limit_per_thread=30):
        guild = self.client.get_guild(guild_id)
        if not guild:
            return {"error": "Guild not found"}

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=within_hours)
        history_after = self._history_after_object(cutoff_time)
        result = {"threads": [], "total_messages": 0}

        for thread in guild.threads:
            last_message_time = None
            if thread.last_message:
                last_message_time = thread.last_message.created_at

            if last_message_time and last_message_time >= cutoff_time:
                messages = []
                kwargs = {"limit": limit_per_thread}
                if history_after:
                    kwargs["after"] = history_after
                async for msg in thread.history(**kwargs):
                    messages.append(
                        {
                            "id": msg.id,
                            "author": msg.author.name if msg.author else "Unknown",
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                        }
                    )
                messages.reverse()

                if messages:
                    result["threads"].append(
                        {
                            "id": thread.id,
                            "name": thread.name,
                            "parent": thread.parent.name if thread.parent else "Unknown",
                            "messages": messages,
                            "message_count": len(messages),
                        }
                    )
                    result["total_messages"] += len(messages)

        result["threads"].sort(
            key=lambda item: item["messages"][-1]["created_at"]
            if item["messages"]
            else "",
            reverse=True,
        )
        return result

    def _get_user_info(self, user_id):
        if user_id:
            return {"error": "Fetching specific users not supported in daemon mode"}

        user = self.client.user
        return {"name": user.name, "id": user.id, "bot": user.bot}

    async def _create_thread(self, channel_id, name, message_id, content=None):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(
            channel_id
        )
        if not channel:
            return {"error": "Channel not found"}

        if isinstance(channel, discord.ForumChannel):
            thread_content = content or name or "New thread"
            content_error = validate_message_content(thread_content)
            if content_error:
                return {"error": content_error}
            thread_with_message = await channel.create_thread(
                name=name,
                content=thread_content,
                reason="Created via CLI",
            )
            return {
                "thread_id": thread_with_message.thread.id,
                "thread_name": thread_with_message.thread.name,
                "success": True,
            }

        if isinstance(channel, discord.TextChannel):
            if not message_id:
                return {
                    "error": "message_id is required when creating a thread from a text channel"
                }
            message = await channel.fetch_message(message_id)
            if not message:
                return {"error": "Message not found"}
            thread = await message.create_thread(name=name or f"Thread-{message_id}")
            return {
                "thread_id": thread.id,
                "thread_name": thread.name,
                "success": True,
            }

        return {"error": "Channel must be a text channel or forum channel"}

    async def _delete_message(self, channel_id, message_id):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(
            channel_id
        )
        if not channel:
            return {"error": "Channel not found"}
        if not isinstance(channel, discord.abc.Messageable):
            return {"error": NON_MESSAGEABLE_TEXT}

        try:
            message = await channel.fetch_message(message_id)
            if message.author.id != self.client.user.id:
                return {"error": "Cannot delete messages from other users"}
            await message.delete()
            return {"success": True, "message_id": message_id}
        except discord.NotFound:
            return {"error": "Message not found"}
        except discord.Forbidden:
            return {"error": "No permission to delete this message"}

    async def _pin_message(self, channel_id, message_id):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(
            channel_id
        )
        if not channel:
            return {"error": "Channel not found"}

        try:
            message = await channel.fetch_message(message_id)
            await message.pin()
            return {"success": True, "message_id": message_id}
        except discord.NotFound:
            return {"error": "Message not found"}
        except discord.Forbidden:
            return {"error": "No permission to pin this message"}

    def _get_thread_info(self, thread_id):
        thread = self.client.get_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        return {
            "id": thread.id,
            "name": thread.name,
            "parent": thread.parent.name if thread.parent else "Unknown",
            "parent_id": thread.parent_id,
            "owner": thread.owner.name if thread.owner else "Unknown",
            "archived": thread.archived,
            "locked": thread.locked,
            "message_count": thread.message_count,
            "member_count": thread.member_count,
            "created_at": thread.created_at.isoformat() if thread.created_at else None,
        }

    async def _archive_thread(self, thread_id, unarchive=False):
        thread = self.client.get_channel(thread_id) or await self.client.fetch_channel(
            thread_id
        )
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        try:
            await thread.edit(archived=not unarchive)
            action = "unarchived" if unarchive else "archived"
            return {"success": True, "thread_name": thread.name, "action": action}
        except discord.Forbidden:
            return {"error": "No permission to modify this thread"}

    async def _join_thread(self, thread_id):
        thread = self.client.get_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        try:
            await thread.join()
            return {"success": True, "thread_name": thread.name}
        except discord.Forbidden:
            return {"error": "No permission to join this thread"}

    async def _leave_thread(self, thread_id):
        thread = self.client.get_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        try:
            await thread.leave()
            return {"success": True, "thread_name": thread.name}
        except discord.Forbidden:
            return {"error": "No permission to leave this thread"}

    async def handle_client(self, reader, writer):
        """Handle incoming client connections."""
        try:
            data = await reader.read(65536)
            if not data:
                return

            command_data = json.loads(data.decode())
            provided_auth = str(command_data.pop("auth", ""))
            if not compare_digest(provided_auth, self.auth_token):
                response = {"error": "Unauthorized daemon request"}
            else:
                response = await self.handle_command(command_data)

            writer.write(json.dumps(response).encode())
            await writer.drain()
        except Exception as exc:
            writer.write(json.dumps({"error": str(exc)}).encode())
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def start_server(self):
        """Start the private Unix socket server."""
        ensure_runtime_dir()
        _safe_unlink(SOCKET_PATH)

        self.server = await asyncio.start_unix_server(
            self.handle_client,
            path=str(SOCKET_PATH),
        )
        chmod_private(SOCKET_PATH)
        log_to_stderr(f"[{datetime.now()}] Daemon server started on {SOCKET_PATH}")

        async with self.server:
            self.code_check_task = asyncio.create_task(self.monitor_code_changes())
            try:
                await self._shutdown.wait()
            except asyncio.CancelledError:
                pass

    async def run(self):
        """Main daemon loop."""
        try:
            log_to_stderr(f"[{datetime.now()}] Connecting to Discord...")
            await self.connect()
            await self.start_server()
        except Exception as exc:
            log_to_stderr(f"[{datetime.now()}] Error: {exc}")
            raise
        finally:
            if self.code_check_task:
                self.code_check_task.cancel()
            await self.client.close()
            _safe_unlink(SOCKET_PATH)


def write_pid():
    """Write PID to file."""
    ensure_runtime_dir()
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    chmod_private(PID_FILE)


def read_pid():
    """Read PID from file."""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            return None
    return None


def is_process_running(pid):
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, TypeError):
        return False


def start_daemon():
    """Start the daemon."""
    ensure_runtime_dir()
    existing_pid = read_pid()
    if existing_pid and is_process_running(existing_pid):
        print(f"Daemon is already running (PID: {existing_pid})")
        return

    _safe_unlink(PID_FILE)
    print("Starting Discord CLI daemon...")

    if os.fork() > 0:
        time.sleep(1)
        new_pid = read_pid()
        if new_pid and is_process_running(new_pid):
            print(f"Daemon started successfully (PID: {new_pid})")
        else:
            print("Failed to start daemon")
        return

    os.setsid()
    os.umask(0o077)

    if os.fork() > 0:
        os._exit(0)

    write_pid()

    ensure_runtime_dir()
    LOG_FILE.touch(exist_ok=True)
    chmod_private(LOG_FILE)
    log_file = open(LOG_FILE, "a", encoding="utf-8")
    os.dup2(log_file.fileno(), sys.stdout.fileno())
    os.dup2(log_file.fileno(), sys.stderr.fileno())

    daemon = DiscordDaemon()
    asyncio.run(daemon.run())


def stop_daemon():
    """Stop the daemon."""
    pid = read_pid()
    if not pid:
        print("Daemon is not running")
        return

    if not is_process_running(pid):
        print(f"Daemon process not found (PID: {pid})")
        _safe_unlink(PID_FILE)
        return

    print(f"Stopping daemon (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            if not is_process_running(pid):
                break
            time.sleep(0.5)

        if is_process_running(pid):
            print("Force killing daemon...")
            os.kill(pid, signal.SIGKILL)

        print("Daemon stopped")
    except Exception as exc:
        print(f"Error stopping daemon: {exc}")
    finally:
        _safe_unlink(PID_FILE)
        _safe_unlink(SOCKET_PATH)


def restart_daemon():
    """Restart the daemon."""
    stop_daemon()
    time.sleep(1)
    start_daemon()


def daemon_status():
    """Check daemon status."""
    pid = read_pid()
    if pid and is_process_running(pid):
        print(f"Daemon is running (PID: {pid})")
        print(f"Socket: {SOCKET_PATH}")
        print(f"Log: {LOG_FILE}")
        return True

    print("Daemon is not running")
    _safe_unlink(PID_FILE)
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 daemon.py <start|stop|restart|status>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        start_daemon()
    elif command == "stop":
        stop_daemon()
    elif command == "restart":
        restart_daemon()
    elif command == "status":
        daemon_status()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python3 daemon.py <start|stop|restart|status>")
        sys.exit(1)


if __name__ == "__main__":
    main()
