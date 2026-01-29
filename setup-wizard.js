#!/usr/bin/env node

const { chromium } = require('playwright');
const readline = require('readline');
const path = require('path');

const DISCORD_URL = 'https://discord.com/login';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(prompt) {
  return new Promise(resolve => rl.question(prompt, resolve));
}

async function getTokenFromBrowser() {
  console.log('Opening browser...');

  const browser = await chromium.launch({
    headless: false,
    args: ['--disable-blink-features=AutomationControlled']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });

  const page = await context.newPage();
  await page.goto(DISCORD_URL);

  console.log('Please log in to Discord in the opened browser window.');
  console.log('The script will automatically detect your token once you are logged in.');

  let token = null;
  while (!token) {
    try {
      token = await page.evaluate(`
        (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()
      `);
      if (token) {
        break;
      }
    } catch (e) {
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  console.log(`Token found: ${token.substring(0, 20)}...${token.substring(token.length - 5)}`);
  await browser.close();
  return token;
}

function generateConfig(token) {
  return {
    mcpServers: {
      'discord-selfbot': {
        command: 'discord-selfbot-mcp',
        env: {
          DISCORD_TOKEN: token
        }
      }
    }
  };
}

async function main() {
  console.log('=== Discord Selfbot MCP Setup ===');
  console.log('1. Extract token automatically (browser)');
  console.log('2. Enter token manually');

  const choice = await question('Choice (1/2): ');

  let token = null;
  if (choice === '1') {
    token = await getTokenFromBrowser();
  } else {
    token = await question('Enter your Discord token: ');
  }

  if (!token) {
    console.log('No token provided.');
    rl.close();
    process.exit(1);
  }

  console.log('\nGenerated MCP Configuration:');
  console.log(JSON.stringify(generateConfig(token), null, 2));

  const save = await question('\nSave to mcp.json? (y/n): ');
  if (save.toLowerCase() === 'y') {
    const fs = require('fs');
    fs.writeFileSync('mcp.json', JSON.stringify(generateConfig(token), null, 2));
    console.log('Saved to mcp.json');
  }

  rl.close();
}

main().catch(err => {
  console.error('Error:', err.message);
  rl.close();
  process.exit(1);
});
