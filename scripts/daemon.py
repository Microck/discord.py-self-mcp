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
from datetime import datetime
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
                return self._list_channels(args.get("guild_id"))
            elif cmd == "read_messages":
                return await self._read_messages(args.get("channel_id"), args.get("limit", 10))
            elif cmd == "send_message":
                return await self._send_message(args.get("channel_id"), args.get("content"))
            elif cmd == "list_threads":
                return await self._list_threads(args.get("channel_id"), args.get("archived", False))
            elif cmd == "read_thread":
                return await self._read_thread(args.get("thread_id"), args.get("limit", 50))
            elif cmd == "list_guild_threads":
                return self._list_guild_threads(args.get("guild_id"))
            elif cmd == "user_info":
                return self._get_user_info(args.get("user_id"))
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
    
    def _list_channels(self, guild_id):
        guild = self.client.get_guild(guild_id) or self.client.fetch_guild(guild_id)
        if not guild:
            return {"error": "Guild not found"}
        
        channels = []
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channels.append({"id": channel.id, "name": channel.name})
        return {"channels": channels}
    
    async def _read_messages(self, channel_id, limit):
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}
        
        messages = []
        async for msg in channel.history(limit=limit):
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
            except:
                pass
        
        return {"threads": threads}
    
    async def _read_thread(self, thread_id, limit):
        thread = self.client.get_channel(thread_id) or await self.client.fetch_channel(thread_id)
        if not thread or not isinstance(thread, discord.Thread):
            return {"error": "Thread not found"}
        
        messages = []
        async for msg in thread.history(limit=limit):
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
    os.umask(0)
    
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
