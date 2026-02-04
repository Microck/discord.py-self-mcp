import asyncio
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

DISCORD_URL = "https://discord.com/login"


def _detect_default_command() -> tuple[str, list[str]]:
    # Prefer the npm wrapper if installed; otherwise use the python console script;
    # fallback to running the module.
    if shutil.which("discord-selfbot-mcp"):
        return "discord-selfbot-mcp", []
    if shutil.which("discord-py-self-mcp"):
        return "discord-py-self-mcp", []
    return "python3", ["-m", "discord_py_self_mcp.main"]


def _default_client_config_candidates() -> list[dict]:
    home = Path.home()
    results: list[dict] = []

    # OpenCode
    results.append(
        {
            "label": "OpenCode",
            "path": str(home / ".config" / "opencode" / "opencode.json"),
            "mode": "opencode-auto",
        }
    )

    # Claude Desktop
    if sys.platform == "darwin":
        results.append(
            {
                "label": "Claude Desktop",
                "path": str(
                    home
                    / "Library"
                    / "Application Support"
                    / "Claude"
                    / "claude_desktop_config.json"
                ),
                "mode": "mcpServers",
            }
        )
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            results.append(
                {
                    "label": "Claude Desktop",
                    "path": str(
                        Path(appdata) / "Claude" / "claude_desktop_config.json"
                    ),
                    "mode": "mcpServers",
                }
            )
    else:
        results.append(
            {
                "label": "Claude Desktop",
                "path": str(home / ".config" / "Claude" / "claude_desktop_config.json"),
                "mode": "mcpServers",
            }
        )

    # Codex (best-effort common paths)
    results.extend(
        [
            {
                "label": "Codex",
                "path": str(home / ".config" / "codex" / "config.json"),
                "mode": "mcpServers",
            },
            {
                "label": "Codex",
                "path": str(home / ".config" / "codex" / "mcp.json"),
                "mode": "mcpServers",
            },
            {
                "label": "Codex",
                "path": str(home / ".codex" / "config.json"),
                "mode": "mcpServers",
            },
            {
                "label": "Codex",
                "path": str(home / ".codex" / "mcp.json"),
                "mode": "mcpServers",
            },
        ]
    )

    # Gemini CLI (best-effort common paths)
    results.extend(
        [
            {
                "label": "Gemini CLI",
                "path": str(home / ".config" / "gemini" / "config.json"),
                "mode": "mcpServers",
            },
            {
                "label": "Gemini CLI",
                "path": str(home / ".config" / "gemini" / "mcp.json"),
                "mode": "mcpServers",
            },
            {
                "label": "Gemini CLI",
                "path": str(home / ".config" / "gemini-cli" / "config.json"),
                "mode": "mcpServers",
            },
            {
                "label": "Gemini CLI",
                "path": str(home / ".gemini" / "config.json"),
                "mode": "mcpServers",
            },
            {
                "label": "Gemini CLI",
                "path": str(home / ".gemini" / "mcp.json"),
                "mode": "mcpServers",
            },
        ]
    )

    return results


def _read_json(path_str: str) -> dict:
    with open(path_str, "r", encoding="utf-8") as f:
        return json.load(f)


def _backup_file(path_str: str) -> str | None:
    p = Path(path_str)
    if not p.exists():
        return None
    stamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
    backup = p.with_name(p.name + f".bak.{stamp}")
    shutil.copyfile(p, backup)
    return str(backup)


def _write_json(path_str: str, data: dict) -> None:
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(path_str, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _upsert_server(existing: dict, token: str, mode: str) -> dict:
    root = existing if isinstance(existing, dict) else {}
    command, args = _detect_default_command()

    if mode == "opencode-mcp":
        mcp = root.get("mcp")
        if not isinstance(mcp, dict):
            mcp = {}
            root["mcp"] = mcp
        entry = {
            "command": [command] + args,
            "enabled": True,
            "type": "local",
            "environment": {"DISCORD_TOKEN": token},
        }
        mcp["discord-py-self"] = entry
        return root

    mcp_servers = root.get("mcpServers")
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}
        root["mcpServers"] = mcp_servers
    entry: dict = {"command": command, "env": {"DISCORD_TOKEN": token}}
    if args:
        entry["args"] = args
    mcp_servers["discord-py-self"] = entry
    return root


async def get_token_from_browser():
    try:
        import importlib

        async_playwright = importlib.import_module(
            "playwright.async_api"
        ).async_playwright
    except ImportError:
        print(
            "Playwright is not installed. Install it to use automatic token extraction:"
        )
        print("  pip install playwright")
        print("  playwright install chromium")
        return None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        await page.goto(DISCORD_URL)

        print("Please log in to Discord in the opened browser window.")
        print("The script will automatically detect your token once you are logged in.")

        token = None
        while not token:
            try:
                token = await page.evaluate(r"""
                    (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()
                """)
                if token:
                    break
            except:
                pass
            await asyncio.sleep(1)

        print(f"Token found: {token[:20]}...{token[-5:]}")
        await browser.close()
        return token


def generate_config(token: str) -> dict:
    # Most MCP clients spawn local servers via `command` + `env`.
    # This python package provides a console script: `discord-py-self-mcp`.
    command, args = _detect_default_command()
    entry: dict = {"command": command, "env": {"DISCORD_TOKEN": token}}
    if args:
        entry["args"] = args
    return {"mcpServers": {"discord-py-self": entry}}


async def async_main():
    print("=== Discord Selfbot MCP Setup ===")
    print("1. Extract token automatically (browser)")
    print("2. Enter token manually")

    choice = input("Choice (1/2): ")

    token = None
    if choice == "1":
        token = await get_token_from_browser()
        if not token:
            print("Falling back to manual token entry.")
            token = input("Enter your Discord token: ")
    else:
        token = input("Enter your Discord token: ")

    if not token:
        print("No token provided.")
        return

    print("\nGenerated MCP Configuration (paste into your MCP client settings):")
    print(json.dumps(generate_config(token), indent=2))

    candidates = [c for c in _default_client_config_candidates() if c.get("path")]
    existing_targets = [c for c in candidates if Path(c["path"]).exists()]
    options = existing_targets[:]
    options.append(
        {
            "label": "Local mcp.json (current dir)",
            "path": str(Path.cwd() / "mcp.json"),
            "mode": "mcpServers",
        }
    )

    print("\nWhere should I write this configuration?")
    for i, opt in enumerate(options, start=1):
        print(f"{i}. {opt['label']} -> {opt['path']}")
    print(f"{len(options) + 1}. Enter a custom path")
    print(f"{len(options) + 2}. Skip (do not write anything)")

    raw = input(f"Choice (1-{len(options) + 2}): ").strip()
    try:
        choice_num = int(raw)
    except ValueError:
        choice_num = len(options) + 2

    if 1 <= choice_num <= len(options):
        opt = options[choice_num - 1]
        target_path = opt["path"]
        mode = opt.get("mode", "mcpServers")
        existing = _read_json(target_path) if Path(target_path).exists() else {}
        actual_mode = mode
        if mode == "opencode-auto":
            actual_mode = (
                "opencode-mcp"
                if isinstance(existing, dict) and isinstance(existing.get("mcp"), dict)
                else "mcpServers"
            )

        backup = _backup_file(target_path)
        updated = _upsert_server(existing, token, actual_mode)
        _write_json(target_path, updated)
        print(f"\nWrote config to: {target_path}")
        if backup:
            print(f"Backup created: {backup}")
    elif choice_num == len(options) + 1:
        target_path = input("Enter config file path: ").strip()
        if target_path:
            existing = _read_json(target_path) if Path(target_path).exists() else {}
            backup = _backup_file(target_path)
            updated = _upsert_server(existing, token, "mcpServers")
            _write_json(target_path, updated)
            print(f"\nWrote config to: {target_path}")
            if backup:
                print(f"Backup created: {backup}")
    else:
        print("\nSkipped writing config.")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
