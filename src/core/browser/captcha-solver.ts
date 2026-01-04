import { chromium, type Browser, type BrowserContext } from 'playwright';
import type { Client } from 'discord.js-selfbot-v13';
import { join } from 'path';
import { homedir } from 'os';
import { mkdir, access } from 'fs/promises';
import { getLogger } from '../logger.js';

interface CaptchaSolverOptions {
  inviteCode: string;
  client: Client;
  token: string;
  timeoutMs?: number;
}

interface CaptchaSolverResult {
  success: boolean;
  guildId?: string;
  guildName?: string;
  error?: string;
}

const USER_DATA_DIR = join(homedir(), '.discord-selfbot-mcp', 'browser-data');
const STORAGE_STATE_PATH = join(USER_DATA_DIR, 'storage-state.json');

async function storageStateExists(): Promise<boolean> {
  try {
    await access(STORAGE_STATE_PATH);
    return true;
  } catch {
    return false;
  }
}

export async function solveCaptchaInBrowser(
  options: CaptchaSolverOptions
): Promise<CaptchaSolverResult> {
  const { inviteCode, client, token, timeoutMs = 300000 } = options;
  const logger = getLogger();
  
  let browser: Browser | null = null;
  let context: BrowserContext | null = null;
  
  try {
    await mkdir(USER_DATA_DIR, { recursive: true });
    
    logger.warn('>>> CLOSE DISCORD APP BEFORE CONTINUING (prevents protocol hijack) <<<');
    
    logger.info('Launching browser for manual captcha solving...');
    
    browser = await chromium.launch({
      headless: false,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--no-default-browser-check',
        '--disable-features=ExternalProtocolDialog',
      ],
    });
    
    const hasStorageState = await storageStateExists();
    
    context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      ...(hasStorageState ? { storageState: STORAGE_STATE_PATH } : {}),
    });
    
    const page = await context.newPage();
    
    logger.info('Navigating to Discord login to inject token...');
    await page.goto('https://discord.com/login', { waitUntil: 'networkidle' });
    
    await page.evaluate((discordToken) => {
      localStorage.setItem('token', JSON.stringify(discordToken));
    }, token);
    
    logger.info('Token injected. Navigating to invite...');
    
    const inviteUrl = `https://discord.com/invite/${inviteCode}`;
    logger.info(`Opening: ${inviteUrl}`);
    logger.warn('>>> SOLVE THE CAPTCHA AND CLICK "Accept Invite" IN THE BROWSER <<<');
    
    await page.goto(inviteUrl, { waitUntil: 'networkidle' });
    
    const initialGuildIds = new Set(client.guilds.cache.keys());
    
    logger.info(`Waiting for guild join... (timeout: ${timeoutMs / 1000}s)`);
    
    const result = await pollForGuildJoin(client, initialGuildIds, timeoutMs);
    
    await context.storageState({ path: STORAGE_STATE_PATH }).catch(() => {});
    
    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error(`Captcha solver error: ${message}`);
    return {
      success: false,
      error: message,
    };
  } finally {
    if (context) {
      await context.storageState({ path: STORAGE_STATE_PATH }).catch(() => {});
    }
    if (browser) {
      await browser.close().catch(() => {});
    }
  }
}

async function pollForGuildJoin(
  client: Client,
  initialGuildIds: Set<string>,
  timeoutMs: number
): Promise<CaptchaSolverResult> {
  const logger = getLogger();
  const startTime = Date.now();
  const pollInterval = 1000;
  
  return new Promise((resolve) => {
    const checkGuilds = () => {
      for (const [guildId, guild] of client.guilds.cache) {
        if (!initialGuildIds.has(guildId)) {
          logger.info(`Joined guild: ${guild.name} (${guildId})`);
          resolve({
            success: true,
            guildId,
            guildName: guild.name,
          });
          return;
        }
      }
      
      if (Date.now() - startTime >= timeoutMs) {
        logger.warn('Timeout waiting for guild join');
        resolve({
          success: false,
          error: 'Timeout. Close browser and try again.',
        });
        return;
      }
      
      setTimeout(checkGuilds, pollInterval);
    };
    
    checkGuilds();
  });
}
