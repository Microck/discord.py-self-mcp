## [1.2.3](https://github.com/Microck/discord.py-self-mcp/compare/v1.2.2...v1.2.3) (2026-04-11)


### Bug Fixes

* **server:** harden startup and role handling ([c4a6b31](https://github.com/Microck/discord.py-self-mcp/commit/c4a6b315c3f66866227d4135dab8bcd2670fa30e))
* **server:** harden startup and role handling ([7ba517c](https://github.com/Microck/discord.py-self-mcp/commit/7ba517c5514b4236d9bde2eed79fb3efc8ad624c))

## [1.2.2](https://github.com/Microck/discord.py-self-mcp/compare/v1.2.1...v1.2.2) (2026-04-11)


### Bug Fixes

* **release:** align node auth env ([16e899e](https://github.com/Microck/discord.py-self-mcp/commit/16e899e32a9b75469225bc3b49f55c7c686b921d))
* **release:** keep npm token fallback ([9b59b48](https://github.com/Microck/discord.py-self-mcp/commit/9b59b485885b6bf1b1690e7d61e189b80cea9083))
* **release:** use npm trusted publishing ([892102d](https://github.com/Microck/discord.py-self-mcp/commit/892102d63037539bc189eb1cbc04660464d4815b))

# Changelog

All notable changes to this project will be documented in this file.

## 1.2.1

- Discrawl MCP tools now prefer a sibling `../discrawl-self/bin/discrawl` build before falling back to `discrawl` on `PATH`.
- Updated README, SKILL, and `server.json` guidance to document the fork-first discrawl lookup and `DISCRAWL_BIN` override behavior.

## 1.0.4

- Setup wizards can update common MCP client config files (with backups).
- Unified install guide and updated README/manual config templates.
- Fixed npm setup wizard server key and expanded templates for python-only usage.
- Added `GROQ_API_KEY` to `server.json` environment variable hints.
