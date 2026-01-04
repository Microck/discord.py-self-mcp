import { z } from 'zod';
import { createTool, success, failure, registerToolGroup } from '../../mcp/registry.js';
import { formatGuild } from '../../core/formatting/index.js';
import { forbiddenError, notFoundError } from '../../core/errors/index.js';

const acceptInviteTool = createTool(
  'accept_invite',
  'Join a server using an invite code. If captcha is required, it will be solved automatically if CAPTCHA_SERVICE and CAPTCHA_API_KEY are configured.',
  z.object({
    invite_code: z.string().describe('The invite code (e.g. "discord.gg/code" or just "code")'),
  }),
  async (ctx, input) => {
    const code = input.invite_code.split('/').pop() ?? input.invite_code;

    try {
      const joined = await ctx.client.acceptInvite(code, {
        bypassOnboarding: true,
        bypassVerify: true,
      });
      
      if ('name' in joined && 'id' in joined) {
        return success({
          guild: formatGuild(joined as import('discord.js-selfbot-v13').Guild),
          message: `Joined guild: ${joined.name}`,
        });
      }
      
      return success({
        channel_id: joined.id,
        message: `Joined channel/group DM`,
      });
    } catch (error) {
      if ((error as { code?: number }).code === 10006) {
        return failure(notFoundError('Invite', code));
      }
      
      const message = error instanceof Error ? error.message : String(error);
      
      if (message.includes('captcha') || message.includes('CAPTCHA')) {
        return failure(forbiddenError(
          'Captcha required. Configure CAPTCHA_SERVICE (capsolver/capmonster/nopecha) and CAPTCHA_API_KEY to auto-solve.'
        ));
      }
      
      return failure(forbiddenError(`Failed to accept invite: ${message}`));
    }
  }
);

export const inviteTools = {
  name: 'invites',
  tools: [acceptInviteTool],
};

registerToolGroup(inviteTools);
