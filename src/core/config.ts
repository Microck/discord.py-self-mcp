import { z } from 'zod';

const configSchema = z.object({
  discordToken: z.string().min(1, 'DISCORD_TOKEN is required'),
  dangerMode: z.boolean().default(false),
  maxRetries: z.number().default(3),
  rateLimitConcurrency: z.number().default(3),
  logLevel: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  allowDMs: z.boolean().default(true),
  allowRelationships: z.boolean().default(false),
  allowVoice: z.boolean().default(true),
  redactContent: z.boolean().default(false),
  allowedGuilds: z.array(z.string()).optional(),
  captchaService: z.enum(['capsolver', 'capmonster', 'nopecha', 'none']).default('none'),
  captchaApiKey: z.string().optional(),
  captchaRetryLimit: z.number().default(3),
});

export type Config = z.infer<typeof configSchema>;

export function loadConfig(): Config {
  const raw = {
    discordToken: process.env.DISCORD_TOKEN ?? '',
    dangerMode: process.env.DANGER_MODE === 'true',
    maxRetries: parseInt(process.env.MAX_RETRIES ?? '3', 10),
    rateLimitConcurrency: parseInt(process.env.RATE_LIMIT_CONCURRENCY ?? '3', 10),
    logLevel: process.env.LOG_LEVEL ?? 'info',
    allowDMs: process.env.ALLOW_DMS !== 'false',
    allowRelationships: process.env.ALLOW_RELATIONSHIPS === 'true',
    allowVoice: process.env.ALLOW_VOICE !== 'false',
    redactContent: process.env.REDACT_CONTENT === 'true',
    allowedGuilds: process.env.ALLOWED_GUILDS?.split(',').filter(Boolean),
    captchaService: process.env.CAPTCHA_SERVICE ?? 'none',
    captchaApiKey: process.env.CAPTCHA_API_KEY,
    captchaRetryLimit: parseInt(process.env.CAPTCHA_RETRY_LIMIT ?? '3', 10),
  };

  return configSchema.parse(raw);
}
