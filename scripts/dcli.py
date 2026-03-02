#!/usr/bin/env python3
"""
Discord CLI Tool - Client for Discord daemon
Usage: python3 dcli.py <command> [args]

Commands:
  daemon <start|stop|restart|status>  - Manage daemon process
  send-message --channel ID --content "msg"
  read-messages --channel ID [--limit N]
  list-guilds
  list-channels --guild ID
  list-threads --channel ID [--archived]
  list-guild-threads --guild ID
  read-thread --thread ID [--limit N]
  user-info [--user ID]
"""
import os
import sys
import json
import socket
import subprocess
from pathlib import Path

SOCKET_PATH = Path("/tmp/discord-cli-daemon.sock")
PID_FILE = Path("/tmp/discord-cli-daemon.pid")


def is_daemon_running():
    """Check if daemon is running"""
    if not PID_FILE.exists():
        return False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except:
        return False


def start_daemon():
    """Auto-start daemon if not running"""
    if not is_daemon_running():
        print("Starting daemon...")
        script_dir = Path(__file__).parent
        daemon_script = script_dir / "daemon.py"
        subprocess.Popen([sys.executable, str(daemon_script), "start"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        # Wait for daemon to start
        import time
        for _ in range(20):  # Wait up to 10 seconds
            time.sleep(0.5)
            if SOCKET_PATH.exists():
                return True
        print("Warning: Daemon may not have started yet")
        return False
    return True


def send_request(command_data, timeout=30):
    """Send request to daemon via Unix socket"""
    if not is_daemon_running():
        start_daemon()
    
    if not SOCKET_PATH.exists():
        print("Error: Daemon socket not found. Is daemon running?")
        sys.exit(1)
    
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(timeout)
        client.connect(str(SOCKET_PATH))
        
        # Send request
        request = json.dumps(command_data).encode()
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        
        # Receive response
        response = b""
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            response += chunk
        
        client.close()
        return json.loads(response.decode())
    except socket.timeout:
        print("Error: Request timed out")
        sys.exit(1)
    except Exception as e:
        print(f"Error communicating with daemon: {e}")
        sys.exit(1)


def format_messages(messages, reverse=True, use_local_timezone=True):
    """Format messages for display"""
    import zoneinfo
    from datetime import datetime
    
    if reverse:
        messages = list(reversed(messages))
    
    # Get local timezone (default to UTC if not available)
    local_tz = None
    if use_local_timezone:
        try:
            local_tz = zoneinfo.ZoneInfo("localtime") if hasattr(zoneinfo, 'ZoneInfo') else None
        except Exception:
            local_tz = None
    
    for msg in messages:
        author = msg.get("author", "Unknown")
        content = msg.get("content", "")[:200] if msg.get("content") else "[No content]"
        created_at = msg.get("created_at", "")
        if created_at:
            # Parse ISO format and convert to local timezone
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if local_tz:
                    dt = dt.astimezone(local_tz)
                created_at = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                pass
        print(f"[{created_at}] {author}: {content}")


def cmd_send_message(channel_id, content):
    """Send a message"""
    result = send_request({
        "command": "send_message",
        "args": {"channel_id": channel_id, "content": content}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    print(f"✓ Message sent (ID: {result.get('message_id')})")


def cmd_read_messages(channel_id, limit):
    """Read messages from a channel"""
    result = send_request({
        "command": "read_messages",
        "args": {"channel_id": channel_id, "limit": limit}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    messages = result.get("messages", [])
    print(f"✓ Retrieved {len(messages)} messages:")
    print("-" * 60)
    format_messages(messages, reverse=False)


def cmd_list_guilds():
    """List all guilds"""
    result = send_request({
        "command": "list_guilds",
        "args": {}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    guilds = result.get("guilds", [])
    print(f"✓ Connected. Found {len(guilds)} guilds:")
    print("-" * 60)
    for guild in guilds:
        print(f"  {guild['name']} (ID: {guild['id']})")
        print(f"    Members: {guild['member_count']}, Channels: {guild['channel_count']}")


def cmd_list_channels(guild_id):
    """List channels in a guild"""
    result = send_request({
        "command": "list_channels",
        "args": {"guild_id": guild_id}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    channels = result.get("channels", [])
    print(f"✓ Channels ({len(channels)}):")
    print("-" * 60)
    for ch in channels:
        print(f"  #{ch['name']} (ID: {ch['id']})")


def cmd_list_threads(channel_id, archived):
    """List threads in a channel"""
    result = send_request({
        "command": "list_threads",
        "args": {"channel_id": channel_id, "archived": archived}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    threads = result.get("threads", [])
    print(f"✓ Threads ({len(threads)}):")
    print("-" * 60)
    for thread in threads:
        print(f"  {thread['name']} (ID: {thread['id']}, Status: {thread['status']})")


def cmd_list_guild_threads(guild_id):
    """List threads in a guild"""
    result = send_request({
        "command": "list_guild_threads",
        "args": {"guild_id": guild_id}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    threads = result.get("threads", [])
    print(f"✓ Active threads in guild ({len(threads)}):")
    print("-" * 60)
    for thread in threads:
        print(f"  {thread['name']} (ID: {thread['id']}, Parent: #{thread['parent']})")


def cmd_read_thread(thread_id, limit):
    """Read messages from a thread"""
    result = send_request({
        "command": "read_thread",
        "args": {"thread_id": thread_id, "limit": limit}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    messages = result.get("messages", [])
    thread_name = result.get("thread_name", "Unknown")
    print(f"✓ Retrieved {len(messages)} messages from thread '{thread_name}':")
    print("-" * 60)
    format_messages(messages, reverse=False)


def cmd_user_info(user_id):
    """Get user info"""
    result = send_request({
        "command": "user_info",
        "args": {"user_id": user_id}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    print("✓ User Information:")
    print("-" * 60)
    print(f"  Name: {result.get('name')}")
    print(f"  ID: {result.get('id')}")
    print(f"  Bot: {result.get('bot')}")


def cmd_daemon(action):
    """Manage daemon process"""
    script_dir = Path(__file__).parent
    daemon_script = script_dir / "daemon.py"
    
    if action == "start":
        if is_daemon_running():
            print("Daemon is already running")
        else:
            subprocess.run([sys.executable, str(daemon_script), "start"])
    elif action == "stop":
        subprocess.run([sys.executable, str(daemon_script), "stop"])
    elif action == "restart":
        subprocess.run([sys.executable, str(daemon_script), "restart"])
    elif action == "status":
        subprocess.run([sys.executable, str(daemon_script), "status"])
    else:
        print(f"Unknown daemon command: {action}")
        print("Usage: daemon <start|stop|restart|status>")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Discord CLI Tool (Client)")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Manage daemon process")
    daemon_parser.add_argument("action", choices=["start", "stop", "restart", "status"])
    
    # send-message command
    send_parser = subparsers.add_parser("send-message", help="Send a message")
    send_parser.add_argument("--channel", "-c", required=True, type=int, help="Channel ID")
    send_parser.add_argument("--content", "-m", required=True, help="Message content")
    
    # read-messages command
    read_parser = subparsers.add_parser("read-messages", help="Read messages from channel")
    read_parser.add_argument("--channel", "-c", required=True, type=int, help="Channel ID")
    read_parser.add_argument("--limit", "-l", type=int, default=10, help="Number of messages")
    
    # list-guilds command
    subparsers.add_parser("list-guilds", help="List all guilds")
    
    # list-channels command
    channels_parser = subparsers.add_parser("list-channels", help="List channels in a guild")
    channels_parser.add_argument("--guild", "-g", required=True, type=int, help="Guild ID")
    
    # list-threads command
    threads_parser = subparsers.add_parser("list-threads", help="List threads in a channel")
    threads_parser.add_argument("--channel", "-c", required=True, type=int, help="Channel ID")
    threads_parser.add_argument("--archived", "-a", action="store_true", help="Include archived threads")
    
    # list-guild-threads command
    guild_threads_parser = subparsers.add_parser("list-guild-threads", help="List all active threads in a guild")
    guild_threads_parser.add_argument("--guild", "-g", required=True, type=int, help="Guild ID")
    
    # read-thread command
    read_thread_parser = subparsers.add_parser("read-thread", help="Read messages from a thread")
    read_thread_parser.add_argument("--thread", "-t", required=True, type=int, help="Thread ID")
    read_thread_parser.add_argument("--limit", "-l", type=int, default=50, help="Number of messages")
    
    # user-info command
    user_parser = subparsers.add_parser("user-info", help="Get user information")
    user_parser.add_argument("--user", "-u", type=int, help="User ID (omit for self)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route commands
    if args.command == "daemon":
        cmd_daemon(args.action)
    elif args.command == "send-message":
        cmd_send_message(args.channel, args.content)
    elif args.command == "read-messages":
        cmd_read_messages(args.channel, args.limit)
    elif args.command == "list-guilds":
        cmd_list_guilds()
    elif args.command == "list-channels":
        cmd_list_channels(args.guild)
    elif args.command == "list-threads":
        cmd_list_threads(args.channel, args.archived)
    elif args.command == "list-guild-threads":
        cmd_list_guild_threads(args.guild)
    elif args.command == "read-thread":
        cmd_read_thread(args.thread, args.limit)
    elif args.command == "user-info":
        cmd_user_info(args.user)


if __name__ == "__main__":
    main()
