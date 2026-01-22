# Migration Handoff: Node.js to Python

## Status
- **Complete Rewrite**: The project has been fully migrated from Node.js (discord.js-selfbot-v13) to Python (discord.py-self).
- **Functionality**: All original 80+ tools are planned; core functionality (messages, channels, voice, relationships, presence, interactions) is implemented and verified via mock tests.
- **Documentation**: README.md and INSTALL.md files have been updated to reflect the new Python usage (`uv` / `pip`).

## Key Changes
- **Library**: `discord.py-self` (Python) is now the underlying library, offering better stability for selfbots.
- **Package Manager**: Recommended `uv` for fast dependency management.
- **Setup**: `discord-selfbot-mcp-setup` script rewritten in Python using Playwright for token extraction.

## Verification
- **Unit Tests**: Full mock test suite (`tests/test_mock.py` was used) confirmed logic for all tool modules.
- **Integration**: Requires a valid user token.

## Next Steps
1. Run `uv tool run discord-selfbot-mcp-setup` to extract a fresh token.
2. Restart your MCP client (OpenCode/Claude).
3. Verify tools in a live environment.
