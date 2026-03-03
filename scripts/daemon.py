#!/usr/bin/env python3
"""
Discord CLI Daemon - Persistent Discord connection with auto-reload
Usage: python3 daemon.py <start|stop|restart|status>
Auto-restart on code change: Enabled
"""
import os
import sys
import asyncio
import json
import socket
import signal
import hashlib
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from threading import Thread, Event

# Load environment variables FIRST
# Priority: 1) Script directory (package location) 2) Current working directory
env_paths = [
    Path(__file__).parent.parent / ".env",  # Package installation directory
    Path.cwd() / ".env",                    # Fallback to current working directory
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

# Configuration
PID_FILE = Path("/tmp/discord-cli-daemon.pid")
SOCKET_PATH = Path("/tmp/discord-cli-daemon.sock")
SCRIPT_DIR = Path(__file__).parent
DAEMON_SCRIPT = SCRIPT_DIR / "daemon.py"
CHECK_INTERVAL = 2  # Check for code changes every 2 seconds

class DiscordDaemon:
    def __init__(self):
        self.client = discord.Client()
        self._connected = asyncio.Event()
        self._shutdown = asyncio.Event()
        self.server = None
        self.command_queue = asyncio.Queue()
        self.responses = {}
        self.last_code_hash = None
        self.code_check_task = None
        
    def _parse_after_time(self, after_str):
        """Parse time string to datetime object.
        Supports formats:
        - ISO datetime: 2024-01-01T00:00:00
        - Relative time: 4h, 30m, 1d
        - Unix timestamp: 1704067200
        """
        if not after_str:
            return None
        
        # Try Unix timestamp first
        try:
            timestamp = int(after_str)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError):
            pass
        
        # Try relative time format (e.g., "4h", "30m", "1d")
        if after_str[-1] in ['h', 'm', 'd']:
            try:
                value = int(after_str[:-1])
                unit = after_str[-1]
                now = datetime.now(timezone.utc)
                if unit == 'h':
                    return now - timedelta(hours=value)
                elif unit == 'm':
                    return now - timedelta(minutes=value)
                elif unit == 'd':
                    return now - timedelta(days=value)
            except (ValueError, IndexError):
                pass
        
        # Try ISO format
        try:
            return datetime.fromisoformat(after_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def get_code_hash(self):
        """Calculate hash of daemon.py to detect changes"""
        if not DAEMON_SCRIPT.exists():
            return None
        with open(DAEMON_SCRIPT, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    async def monitor_code_changes(self):
        """Monitor daemon.py for changes and auto-restart"""
        self.last_code_hash = self.get_code_hash()
        while not self._shutdown.is_set():
            await asyncio.sleep(CHECK_INTERVAL)
            current_hash = self.get_code_hash()
            if current_hash != self.last_code_hash:
                print(f"[{datetime.now()}] Code change detected! Restarting daemon...")
                await self.restart_daemon()
                return
    
    async def restart_daemon(self):
        """Restart the daemon process"""
        # Notify all pending requests
        for req_id in list(self.responses.keys()):
            self.responses[req_id] = {"error": "Daemon restarting due to code changes"}
        
        # Trigger shutdown
        self._shutdown.set()
        await self.client.close()
        
        # Remove socket file
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        
        # Start new daemon process
        subprocess.Popen([sys.executable, str(DAEMON_SCRIPT), "start"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        start_new_session=True)
        
        # Exit current process
        os._exit(0)
    
    async def connect(self):
        """Connect to Discord and start listening"""
        @self.client.event
        async def on_ready():
            print(f"[{datetime.now()}] Connected as {self.client.user}")
            self._connected.set()
        
        @self.client.event
        async def on_disconnect():
            print(f"[{datetime.now()}] Disconnected from Discord")
        
        # Start connection
        connect_task = asyncio.create_task(self.client.start(TOKEN))
        await asyncio.wait_for(self._connected.wait(), timeout=30)
        return connect_task
    
    async def handle_command(self, command_data):
        """Execute a command and return result"""
        cmd = command_data.get("command")
        args = command_data.get("args", {})
        
        try:
            if cmd == "list_guilds":
                return self._list_guilds()
            elif cmd == "list_channels":
                return await self._list_channels(args.get("guild_id"))
            elif cmd == "read_messages":
                return await self._read_messages(args.get("channel_id"), args.get("limit", 10), args.get("after"))
            elif cmd == "send_message":
                return await self._send_message(args.get("channel_id"), args.get("content"))
            elif cmd == "list_threads":
                return await self._list_threads(args.get("channel_id"), args.get("archived", False))
            elif cmd == "read_thread":
                return await self._read_thread(args.get("thread_id"), args.get("limit", 50), args.get("after"))
            elif cmd == "list_guild_threads":
                return self._list_guild_threads(args.get("guild_id"))
            elif cmd == "list_recent_threads":
                return self._list_recent_threads(args.get("guild_id"), args.get("within_hours", 24))
            elif cmd == "read_recent_threads":
                return await self._read_recent_threads(args.get("guild_id"), args.get("within_hours", 4), args.get("limit_per_thread", 30))
            elif cmd == "delete_message":
                return await self._delete_message(args.get("channel_id"), args.get("message_id"))
            elif cmd == "pin_message":
                return await self._pin_message(args.get("channel_id"), args.get("message_id"))
            elif cmd == "get_thread_info":
                return self._get_thread_info(args.get("thread_id"))
            elif cmd == "archive_thread":
                return await self._archive_thread(args.get("thread_id"), args.get("unarchive", False))
            elif cmd == "join_thread":
                return await self._join_thread(args.get("thread_id"))
            elif cmd == "leave_thread":
                return await self._leave_thread(args.get("thread_id"))
            elif cmd == "user_info":
                return self._get_user_info(args.get("user_id"))
            elif cmd == "create_thread":
                return await self._create_thread(args.get("channel_id"), args.get("name"), args.get("message_id"), args.get("content"))
            else:
                return {"error": f"Unknown command: {cmd}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _list_guilds(self):
        guilds = []
        for guild in self.client.guilds:
            guilds.append({
                "id": guild.id,
                "name": guild.name,
                "member_count": guild.member_count,
                "channel_count": len(guild.channels)
            })
        return {"guilds": guilds}
    
    async def _list_channels(self, guild_id):
        guild = self.client.get_guild(guild_id)
        if not guild:
            try:
                guild = await self.client.fetch_guild(guild_id)
            except discord.NotFound:
                return {"error": "Guild not found"}
            except discord.HTTPException as e:
                return {"error": f"Failed to fetch guild: {e}"}
        
        channels = []
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channels.append({"id": channel.id, "name": channel.name})
        return {"channels": channels}
    
    async def _read_messages(self, channel_id, limit, after=None):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}
        
        # Parse after time
        after_dt = self._parse_after_time(after) if after else None
        
        messages = []
        kwargs = {"limit": limit}
        if after_dt:
            kwargs["after"] = after_dt
        
        async for msg in channel.history(**kwargs):
            messages.append({
                "id": msg.id,
                "author": msg.author.name if msg.author else "Unknown",
                "content": msg.clean_content if msg.clean_content else msg.content,
                "created_at": msg.created_at.isoformat()
            })
        messages.reverse()
        return {"messages": messages}
    
    async def _send_message(self, channel_id, content):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}
        
        message = await channel.send(content)
        return {"message_id": message.id, "success": True}
    
    async def _list_threads(self, channel_id, archived=False):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}
        
        threads = []
        for thread in channel.threads:
            threads.append({"id": thread.id, "name": thread.name, "status": "Active"})
        
        if archived:
            try:
                async for thread in channel.archived_threads(limit=100):
                    threads.append({"id": thread.id, "name": thread.name, "status": "Archived"})
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"[{datetime.now()}] Warning: Failed to fetch archived threads: {e}")
        
        return {"threads": threads}
    
    async def _read_thread(self, thread_id, limit, after=None):
        thread = self.client.get_channel(thread_id) or await self.client.fetch_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}
        
        # Parse after time
        after_dt = self._parse_after_time(after) if after else None
        
        messages = []
        kwargs = {"limit": limit}
        if after_dt:
            kwargs["after"] = after_dt
        
        async for msg in thread.history(**kwargs):
            messages.append({
                "id": msg.id,
                "author": msg.author.name if msg.author else "Unknown",
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            })
        messages.reverse()
        return {"messages": messages, "thread_name": thread.name}
    
    def _list_guild_threads(self, guild_id):
        guild = self.client.get_guild(guild_id)
        if not guild:
            return {"error": "Guild not found"}
        
        threads = []
        for thread in guild.threads:
            threads.append({
                "id": thread.id,
                "name": thread.name,
                "parent": thread.parent.name if thread.parent else "Unknown"
            })
        return {"threads": threads}
    
    def _list_recent_threads(self, guild_id, within_hours=24):
        """List threads with recent activity (within specified hours).

        Args:
            guild_id: Guild ID
            within_hours: Only show threads with activity within this many hours
        """
        guild = self.client.get_guild(guild_id)
        if not guild:
            return {"error": "Guild not found"}

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=within_hours)

        threads = []
        for thread in guild.threads:
            # Get last message time if available
            last_message_time = None
            if thread.last_message:
                last_message_time = thread.last_message.created_at

            # Include thread if it has activity within cutoff time
            if last_message_time and last_message_time >= cutoff_time:
                threads.append({
                    "id": thread.id,
                    "name": thread.name,
                    "parent": thread.parent.name if thread.parent else "Unknown",
                    "last_message_at": last_message_time.isoformat(),
                    "message_count": thread.message_count
                })

        # Sort by last message time (most recent first)
        threads.sort(key=lambda x: x["last_message_at"], reverse=True)
        return {"threads": threads}
    
    async def _read_recent_threads(self, guild_id, within_hours=4, limit_per_thread=30):
        """Read messages from all threads with recent activity.

        Args:
            guild_id: Guild ID
            within_hours: Only read threads with activity within this many hours
            limit_per_thread: Max messages to read per thread

        Returns:
            Dict with thread messages organized by thread
        """
        guild = self.client.get_guild(guild_id)
        if not guild:
            return {"error": "Guild not found"}

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=within_hours)
        result = {"threads": [], "total_messages": 0}
        
        for thread in guild.threads:
            # Check if thread has recent activity
            last_message_time = None
            if thread.last_message:
                last_message_time = thread.last_message.created_at
            
            if last_message_time and last_message_time >= cutoff_time:
                # Read messages from this thread
                messages = []
                async for msg in thread.history(limit=limit_per_thread, after=cutoff_time):
                    messages.append({
                        "id": msg.id,
                        "author": msg.author.name if msg.author else "Unknown",
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat()
                    })
                messages.reverse()
                
                if messages:
                    result["threads"].append({
                        "id": thread.id,
                        "name": thread.name,
                        "parent": thread.parent.name if thread.parent else "Unknown",
                        "messages": messages,
                        "message_count": len(messages)
                    })
                    result["total_messages"] += len(messages)
        
        # Sort threads by last activity
        result["threads"].sort(
            key=lambda x: x["messages"][-1]["created_at"] if x["messages"] else "",
            reverse=True
        )
        
        return result
    
    def _get_user_info(self, user_id):
        if user_id:
            # Can't easily fetch arbitrary users without gateway intents
            return {"error": "Fetching specific users not supported in daemon mode"}
        
        user = self.client.user
        return {
            "name": user.name,
            "id": user.id,
            "bot": user.bot
        }
    
    async def _create_thread(self, channel_id, name, message_id, content=None):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}

        # Support both TextChannel and ForumChannel
        if isinstance(channel, discord.ForumChannel):
            # For forum channels, create a thread with an initial message
            if not content:
                content = name or "New thread"
            thread_with_message = await channel.create_thread(name=name, content=content, reason="Created via CLI")
            return {"thread_id": thread_with_message.thread.id, "thread_name": thread_with_message.thread.name, "success": True}
        elif isinstance(channel, discord.TextChannel):
            if message_id:
                message = await channel.fetch_message(message_id)
                if not message:
                    return {"error": "Message not found"}
                thread = await message.create_thread(name=name or f"Thread-{message_id}")
                return {"thread_id": thread.id, "thread_name": thread.name, "success": True}
            else:
                thread = await channel.create_thread(name=name, reason="Created via CLI")
                return {"thread_id": thread.id, "thread_name": thread.name, "success": True}
        else:
            return {"error": "Channel must be a text channel or forum channel"}

    async def _delete_message(self, channel_id, message_id):
        """Delete a message from a channel."""
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}

        try:
            message = await channel.fetch_message(message_id)
            await message.delete()
            return {"success": True, "message_id": message_id}
        except discord.NotFound:
            return {"error": "Message not found"}
        except discord.Forbidden:
            return {"error": "No permission to delete this message"}

    async def _pin_message(self, channel_id, message_id):
        """Pin a message in a channel."""
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
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
        """Get detailed information about a thread."""
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
            "created_at": thread.created_at.isoformat() if thread.created_at else None
        }

    async def _archive_thread(self, thread_id, unarchive=False):
        """Archive or unarchive a thread."""
        thread = self.client.get_channel(thread_id) or await self.client.fetch_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        try:
            await thread.edit(archived=not unarchive)
            action = "unarchived" if unarchive else "archived"
            return {"success": True, "thread_name": thread.name, "action": action}
        except discord.Forbidden:
            return {"error": "No permission to modify this thread"}

    async def _join_thread(self, thread_id):
        """Join a thread."""
        thread = self.client.get_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        try:
            await thread.join()
            return {"success": True, "thread_name": thread.name}
        except discord.Forbidden:
            return {"error": "No permission to join this thread"}

    async def _leave_thread(self, thread_id):
        """Leave a thread."""
        thread = self.client.get_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}

        try:
            await thread.leave()
            return {"success": True, "thread_name": thread.name}
        except discord.Forbidden:
            return {"error": "No permission to leave this thread"}
    
    async def handle_client(self, reader, writer):
        """Handle incoming client connections"""
        try:
            data = await reader.read(65536)
            if not data:
                return
            
            command_data = json.loads(data.decode())
            result = await self.handle_command(command_data)
            
            response = json.dumps(result).encode()
            writer.write(response)
            await writer.drain()
        except Exception as e:
            error_response = json.dumps({"error": str(e)}).encode()
            writer.write(error_response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def start_server(self):
        """Start Unix socket server"""
        # Remove old socket file
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        
        self.server = await asyncio.start_unix_server(
            self.handle_client,
            path=str(SOCKET_PATH)
        )
        
        print(f"[{datetime.now()}] Daemon server started on {SOCKET_PATH}")
        
        async with self.server:
            # Start code monitoring
            self.code_check_task = asyncio.create_task(self.monitor_code_changes())
            
            # Keep server running
            try:
                await self._shutdown.wait()
            except asyncio.CancelledError:
                pass
    
    async def run(self):
        """Main daemon loop"""
        try:
            # Connect to Discord
            print(f"[{datetime.now()}] Connecting to Discord...")
            connect_task = await self.connect()
            
            # Start socket server
            await self.start_server()
            
        except Exception as e:
            print(f"[{datetime.now()}] Error: {e}")
            raise
        finally:
            await self.client.close()
            if SOCKET_PATH.exists():
                SOCKET_PATH.unlink()


def write_pid():
    """Write PID to file"""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def read_pid():
    """Read PID from file"""
    if PID_FILE.exists():
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    return None

def is_process_running(pid):
    """Check if a process is running"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def start_daemon():
    """Start the daemon"""
    existing_pid = read_pid()
    if existing_pid and is_process_running(existing_pid):
        print(f"Daemon is already running (PID: {existing_pid})")
        return
    
    # Remove old PID file
    if PID_FILE.exists():
        PID_FILE.unlink()
    
    print("Starting Discord CLI daemon...")
    
    # Fork to background
    if os.fork() > 0:
        # Parent process
        time.sleep(1)
        new_pid = read_pid()
        if new_pid and is_process_running(new_pid):
            print(f"Daemon started successfully (PID: {new_pid})")
        else:
            print("Failed to start daemon")
        return
    
    # Child process - daemonize
    os.setsid()
    os.umask(0o077)  # Restrict permissions: only owner can read/write/execute
    
    if os.fork() > 0:
        os._exit(0)
    
    # Grandchild process - the actual daemon
    write_pid()
    
    # Redirect stdout/stderr to log file
    log_file = open("/tmp/discord-cli-daemon.log", "a")
    os.dup2(log_file.fileno(), sys.stdout.fileno())
    os.dup2(log_file.fileno(), sys.stderr.fileno())
    
    # Run daemon
    daemon = DiscordDaemon()
    asyncio.run(daemon.run())

def stop_daemon():
    """Stop the daemon"""
    pid = read_pid()
    if not pid:
        print("Daemon is not running")
        return
    
    if not is_process_running(pid):
        print(f"Daemon process not found (PID: {pid})")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return
    
    print(f"Stopping daemon (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for process to stop
        for _ in range(10):
            if not is_process_running(pid):
                break
            time.sleep(0.5)
        
        if is_process_running(pid):
            print("Force killing daemon...")
            os.kill(pid, signal.SIGKILL)
        
        print("Daemon stopped")
    except Exception as e:
        print(f"Error stopping daemon: {e}")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()

def restart_daemon():
    """Restart the daemon"""
    stop_daemon()
    time.sleep(1)
    start_daemon()

def daemon_status():
    """Check daemon status"""
    pid = read_pid()
    if pid and is_process_running(pid):
        print(f"Daemon is running (PID: {pid})")
        print(f"Socket: {SOCKET_PATH}")
        return True
    else:
        print("Daemon is not running")
        if PID_FILE.exists():
            PID_FILE.unlink()
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
