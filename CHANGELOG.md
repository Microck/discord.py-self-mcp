# 1.0.0 (2026-04-11)


### Bug Fixes

* allow newer discord.py-self versions ([84a1c61](https://github.com/Microck/discord.py-self-mcp/commit/84a1c61b598fc20e2f229b8cf77661708feab346))
* convert Discord timestamps to local timezone ([e94eebd](https://github.com/Microck/discord.py-self-mcp/commit/e94eebda0a419e4661c2b541e100922b5e46b5b7))
* correct npm wrapper python detection and clean repo artifacts ([cd6be9b](https://github.com/Microck/discord.py-self-mcp/commit/cd6be9bdd5c97ec33f78ee705b9b647d1ef44cb3))
* **daemon:** address PR review issues ([b23db0a](https://github.com/Microck/discord.py-self-mcp/commit/b23db0a105c11dceb3a321259340bb7834f56323))
* **discrawl:** prefer local discrawl-self binary ([5a14232](https://github.com/Microck/discord.py-self-mcp/commit/5a1423217e2585bf6e672bfd6c07f9baa6119fbf))
* display readable mentions in messages using clean_content ([046ae17](https://github.com/Microck/discord.py-self-mcp/commit/046ae1755ab8237829abc1e7286fe5fa3409559e))
* handle None content in search_messages ([bb1c832](https://github.com/Microck/discord.py-self-mcp/commit/bb1c8328cbf1db1ba8511fca67449b6a735ef2fc))
* improve npm wrapper Python version detection ([af313e4](https://github.com/Microck/discord.py-self-mcp/commit/af313e43e085e709cdb2e8a212866b5910d03e0c))
* **release:** align node auth env ([16e899e](https://github.com/Microck/discord.py-self-mcp/commit/16e899e32a9b75469225bc3b49f55c7c686b921d))
* **release:** keep npm token fallback ([9b59b48](https://github.com/Microck/discord.py-self-mcp/commit/9b59b485885b6bf1b1690e7d61e189b80cea9083))
* **release:** use npm trusted publishing ([892102d](https://github.com/Microck/discord.py-self-mcp/commit/892102d63037539bc189eb1cbc04660464d4815b))
* remove duplicate discord import ([d9d974f](https://github.com/Microck/discord.py-self-mcp/commit/d9d974f36c5b783786a6f436c221ffbec3921913))
* remove leaked Discord token from README, add security gitignore rules ([f618f2d](https://github.com/Microck/discord.py-self-mcp/commit/f618f2d0454187506ac244940cac7faad41cf65a))
* remove message content truncation limit ([3c3a28c](https://github.com/Microck/discord.py-self-mcp/commit/3c3a28c8cc41ca6789c438e2dd6f827c7518ec04))
* resolve TextChannel application_commands error ([1ff61b8](https://github.com/Microck/discord.py-self-mcp/commit/1ff61b86ef2eaa8ac4834d104b892d7a0b894ca3))
* restore previous interactions.py logic ([0bacc29](https://github.com/Microck/discord.py-self-mcp/commit/0bacc290dde8e3dde536730832a5a143bbf231b1))
* suppress logging output to avoid interfering with MCP stdio ([a48a320](https://github.com/Microck/discord.py-self-mcp/commit/a48a320282e431fa5daa9b25e04d7aabadfa4789))
* update for discord.py-self 2.1.0 and npm wrapper ([98576e9](https://github.com/Microck/discord.py-self-mcp/commit/98576e9d4052ec7f0069ae454c35277da3e567ae))
* update hcaptcha-challenger import to use correct API ([339382d](https://github.com/Microck/discord.py-self-mcp/commit/339382d943b1d18ad90d9196e01864e79184c6e4))
* use Gemini API key instead of Groq for hcaptcha-challenger ([afa246a](https://github.com/Microck/discord.py-self-mcp/commit/afa246a4d7875dca25a3ece503f5a26144f38d10))


### Features

* add 5 advanced tools (profile, interactions, invites, guild creation) ([2ead667](https://github.com/Microck/discord.py-self-mcp/commit/2ead667b382866eea88f302dcfcf39f300824786))
* add embed text extraction utility ([5a92b6d](https://github.com/Microck/discord.py-self-mcp/commit/5a92b6d057ff8972a3e3ff20141c8c3b2b504568))
* add experimental hCaptcha solver ([930842c](https://github.com/Microck/discord.py-self-mcp/commit/930842cd2717bec3ea1eb911148827b5e4a90736))
* add non-interactive setup mode for agents ([5ba68b1](https://github.com/Microck/discord.py-self-mcp/commit/5ba68b16907f124ed7fe8813a4a450ed03fe7869))
* add OpenCode/Claude Code support to setup wizard ([92120d8](https://github.com/Microck/discord.py-self-mcp/commit/92120d82570239440aac3b1a3131f59a8b0cbeb7))
* add quickstart setup wizard ([3a7648e](https://github.com/Microck/discord.py-self-mcp/commit/3a7648e54c8f3c2419ac84d5d79d22dfa0f25bd4))
* add Skill CLI mode with daemon for local development ([efb090d](https://github.com/Microck/discord.py-self-mcp/commit/efb090d6134c5971ef886f7964d7903823258c15))
* add thread message reading and listing tools ([a5ca06f](https://github.com/Microck/discord.py-self-mcp/commit/a5ca06fea02c8e5f38a2d56fde2caf55e4608394))
* add typed discrawl MCP tools ([41bf834](https://github.com/Microck/discord.py-self-mcp/commit/41bf834a660ba62401a771c0a516c368579166d1))
* bot testing tools + system browser captcha fallback ([7e4f7b9](https://github.com/Microck/discord.py-self-mcp/commit/7e4f7b9fc8c7086f95d57cd79acf50fcc23c0bb9))
* complete Discord selfbot MCP with 55 tools ([5ca9533](https://github.com/Microck/discord.py-self-mcp/commit/5ca9533e07d0c04868fd3f3b671055f57937c4f4))
* complete missing tools (messages, threads, menus) and update docs ([b1a40cc](https://github.com/Microck/discord.py-self-mcp/commit/b1a40cccd93fc5621017f6925171c85c087ad18b))
* complete missing tools and verify with live test ([92f9322](https://github.com/Microck/discord.py-self-mcp/commit/92f9322ef3faa9d37789238a7803b8b365ceb5b0))
* **discord-cli:** add time filtering and thread management commands ([096ae5d](https://github.com/Microck/discord.py-self-mcp/commit/096ae5d872f9e29edeeab4cee39e25534ef302da))
* enable voice support dependencies ([b99ac79](https://github.com/Microck/discord.py-self-mcp/commit/b99ac79bf6ef6127e5869e09af3759d12212d2d2))
* enhance friend request tool to search cache ([75fa8d2](https://github.com/Microck/discord.py-self-mcp/commit/75fa8d284a8c3dbab4d0d206bc37c71a4c1850fe))
* extract embed text in read_messages ([cdc18c5](https://github.com/Microck/discord.py-self-mcp/commit/cdc18c5c97b691308065de08d0fcf72158439e2f))
* extract embed text in search_messages ([2ad49c8](https://github.com/Microck/discord.py-self-mcp/commit/2ad49c8ddde4e2c9cb6d824638882090cc75e81e))
* implement all discord-py-self tools (interactions, presence, voice, channels, relationships) ([f760b47](https://github.com/Microck/discord.py-self-mcp/commit/f760b477f9f325a810403e98625c9d858a1daeeb))
* implement missing tools (reactions, members, invites, profile) ([dfcf616](https://github.com/Microck/discord.py-self-mcp/commit/dfcf616d4b1c00f41cfb95e36ff9a18bad60400c))
* improve captcha solver and bot handling ([359afa8](https://github.com/Microck/discord.py-self-mcp/commit/359afa89ee21329e8549ae6b43fe72b4a14be075))
* improve setup wizard and main entry point ([f5102a4](https://github.com/Microck/discord.py-self-mcp/commit/f5102a485ce669b652cc7f1612313f8a0b9344c4))
* migrate from Node.js to Python using discord.py-self ([9871913](https://github.com/Microck/discord.py-self-mcp/commit/9871913382c701b3d1779c967ced4ad95c8d4ee4))
* **release:** automate npm publishing and version sync ([cd7e8d8](https://github.com/Microck/discord.py-self-mcp/commit/cd7e8d808a53bd843001b5af9a0d6b32728a83eb))
* replace hCaptcha solver with hcaptcha-challenger and add rate limiting ([e54b4cf](https://github.com/Microck/discord.py-self-mcp/commit/e54b4cf30be2b42c411e5f206598b4b78e2e16bf))
* support forum channels in create-thread and add parent_id to get-thread-info ([3f33088](https://github.com/Microck/discord.py-self-mcp/commit/3f33088fee452a236b18e00aefc0f56ddc356101))


### Reverts

* layout change for badges ([5f28ac4](https://github.com/Microck/discord.py-self-mcp/commit/5f28ac4d677cee4716845ed59a32e7abab0a3134))

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
