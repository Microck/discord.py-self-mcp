# Migration Handoff: Node.js to Python

## Status
- **Complete Rewrite**: The project has been fully migrated from Node.js (discord.js-selfbot-v13) to Python (discord.py-self).
- **Functionality**: Core functionality (messages, channels, voice, relationships, presence, interactions) is implemented.
- **Documentation**: README.md updated with feature tables and emojis.

## Verification
### ✅ Verified Live (Real Token)
- **Authentication**: Successful login as `_23blank__#0`.
- **Read Operations**: 
  - `get_user_info`: OK
  - `list_guilds`: OK
  - `list_channels`: OK

### 🛡️ Verified Logic (Mock Tests)
- **Write Operations**: Verified code paths for:
  - `send_message`, `edit_message`, `delete_message`
  - `create_channel`, `delete_channel`
  - `create_thread`, `archive_thread`
  - `join_voice_channel`, `leave_voice_channel`
  - `add_friend`, `remove_friend`

### ⚠️ Limitations
- **Guild Creation**: Live test for creating a sandbox guild failed with `403 Forbidden` (likely CAPTCHA/account limits). Destructive tests were not run on live servers to protect user data.
- **Voice**: Requires `ffmpeg` or `opus` library installed on the system to function fully.

## Next Steps
1. **Install**: `uv tool install git+https://github.com/Microck/discord-selfbot-mcp.git`
2. **Configure**: Use the generated `mcp.json` or run `discord-selfbot-mcp-setup`.
3. **Usage**: Connect via OpenCode or Claude Desktop.
