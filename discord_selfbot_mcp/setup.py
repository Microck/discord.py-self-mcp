import asyncio
import os
import sys
import json
import subprocess
from playwright.async_api import async_playwright

DISCORD_URL = 'https://discord.com/login'

async def get_token_from_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

def generate_config(token):
    return {
        "mcpServers": {
            "discord-selfbot": {
                "command": "uv",
                "args": ["run", "discord-selfbot-mcp"],
                "env": {
                    "DISCORD_TOKEN": token
                }
            }
        }
    }

async def main():
    print("=== Discord Selfbot MCP Setup ===")
    print("1. Extract token automatically (browser)")
    print("2. Enter token manually")
    
    choice = input("Choice (1/2): ")
    
    token = None
    if choice == '1':
        token = await get_token_from_browser()
    else:
        token = input("Enter your Discord token: ")
        
    if not token:
        print("No token provided.")
        return

    print("\nGenerated MCP Configuration (for .opencode.json or mcp.json):")
    print(json.dumps(generate_config(token), indent=2))
    
    save = input("\nSave to mcp.json? (y/n): ")
    if save.lower() == 'y':
        with open("mcp.json", "w") as f:
            json.dump(generate_config(token), f, indent=2)
        print("Saved to mcp.json")

if __name__ == "__main__":
    asyncio.run(main())
