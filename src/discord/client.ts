import { Client } from 'discord.js-selfbot-v13';
import type { Config } from '../core/config.js';
import { getLogger } from '../core/logger.js';
import { RateLimiter } from '../core/rateLimit/index.js';
import { mapDiscordError, type McpError } from '../core/errors/index.js';
import { createCaptchaSolver } from '../core/captcha/solver.js';

export interface DiscordContext {
  client: Client;
  rateLimiter: RateLimiter;
  config: Config;
  isReady: boolean;
  lastError: McpError | null;
}

let context: DiscordContext | null = null;

export async function initDiscordClient(config: Config): Promise<DiscordContext> {
  const logger = getLogger();
  
  if (context?.isReady) {
    logger.debug('Discord client already initialized');
    return context;
  }

  const captchaSolver = createCaptchaSolver(config);

  const client = new Client({
    checkUpdate: false,
    captchaSolver,
    captchaRetryLimit: config.captchaRetryLimit,
  } as Record<string, unknown>);

  const rateLimiter = new RateLimiter(config.rateLimitConcurrency);

  context = {
    client,
    rateLimiter,
    config,
    isReady: false,
    lastError: null,
  };

  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error('Discord client login timeout after 30s'));
    }, 30000);

    client.once('ready', () => {
      clearTimeout(timeout);
      context!.isReady = true;
      logger.info('Discord client ready', { userId: client.user?.id });
      resolve(context!);
    });

    client.on('error', (error) => {
      context!.lastError = mapDiscordError(error);
      logger.error('Discord client error', { error: error.message });
    });

    client.on('warn', (warning) => {
      logger.warn('Discord client warning', { warning });
    });

    client.login(config.discordToken).catch((error) => {
      clearTimeout(timeout);
      context!.lastError = mapDiscordError(error);
      context!.isReady = false;
      logger.error('Discord login failed', { error: error.message });
      reject(error);
    });
  });
}

export function getDiscordContext(): DiscordContext {
  if (!context) {
    throw new Error('Discord client not initialized. Call initDiscordClient first.');
  }
  return context;
}

export function isClientReady(): boolean {
  return context?.isReady ?? false;
}

export async function destroyDiscordClient(): Promise<void> {
  if (context?.client) {
    context.client.destroy();
    context.isReady = false;
    getLogger().info('Discord client destroyed');
  }
}
