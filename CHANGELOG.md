## [1.2.8](https://github.com/Microck/discord.py-self-mcp/compare/v1.2.7...v1.2.8) (2026-04-25)


### Bug Fixes

* expose message attachments in daemon cli ([2a5ecfd](https://github.com/Microck/discord.py-self-mcp/commit/2a5ecfd6a0a875c20295d65f99e37a3f8e21e3d8))

## [1.2.7](https://github.com/Microck/discord.py-self-mcp/compare/v1.2.6...v1.2.7) (2026-04-23)


### Bug Fixes

* harden rate limiting and thread parity ([71e5a87](https://github.com/Microck/discord.py-self-mcp/commit/71e5a871d0228d4beabd748d742ceadde3100cf8))

## [1.2.6](https://github.com/Microck/discord.py-self-mcp/compare/v1.2.5...v1.2.6) (2026-04-17)


### Bug Fixes

* harden daemon runtime and align tool behavior ([4708265](https://github.com/Microck/discord.py-self-mcp/commit/47082654530b866af8cb4ded705e531e76c8b71f))

## [1.2.5](https://github.com/Microck/discord.py-self-mcp/compare/v1.2.4...v1.2.5) (2026-04-17)


### Bug Fixes

* add attachment access for message media ([b270b61](https://github.com/Microck/discord.py-self-mcp/commit/b270b613c538e6ef9177b7caa2e954b32d3c73a7)), closes [#16](https://github.com/Microck/discord.py-self-mcp/issues/16)

## [1.2.4](https://github.com/Microck/discord.py-self-mcp/compare/v1.2.3...v1.2.4) (2026-04-17)


### Bug Fixes

* improve token extraction with localStorage fallback ([36eb54a](https://github.com/Microck/discord.py-self-mcp/commit/36eb54afd6ec1b2fb687424aa6e934ffd17eb6dd))

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
