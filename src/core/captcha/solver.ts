import type { Config } from '../config.js';
import { getLogger } from '../logger.js';

interface CaptchaData {
  captcha_key: string[];
  captcha_sitekey: string;
  captcha_service: string;
  captcha_rqdata?: string;
  captcha_rqtoken?: string;
}

type CaptchaSolverFn = (captcha: CaptchaData, userAgent: string) => Promise<string>;

async function solveWithCapSolver(
  apiKey: string,
  captcha: CaptchaData,
  userAgent: string
): Promise<string> {
  const logger = getLogger();
  logger.info('Solving captcha with CapSolver...');
  
  const createTaskRes = await fetch('https://api.capsolver.com/createTask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      clientKey: apiKey,
      task: {
        type: 'HCaptchaTaskProxyLess',
        websiteURL: 'https://discord.com',
        websiteKey: captcha.captcha_sitekey,
        userAgent,
        isInvisible: true,
        enterprisePayload: captcha.captcha_rqdata ? { rqdata: captcha.captcha_rqdata } : undefined,
      },
    }),
  });
  
  const createData = await createTaskRes.json() as { errorId: number; taskId?: string; errorDescription?: string };
  
  if (createData.errorId !== 0) {
    throw new Error(`CapSolver create task failed: ${createData.errorDescription}`);
  }
  
  const taskId = createData.taskId;
  
  for (let i = 0; i < 120; i++) {
    await new Promise(r => setTimeout(r, 1000));
    
    const resultRes = await fetch('https://api.capsolver.com/getTaskResult', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clientKey: apiKey, taskId }),
    });
    
    const resultData = await resultRes.json() as { 
      status: string; 
      solution?: { gRecaptchaResponse: string };
      errorDescription?: string;
    };
    
    if (resultData.status === 'ready' && resultData.solution) {
      logger.info('CapSolver: Captcha solved');
      return resultData.solution.gRecaptchaResponse;
    }
    
    if (resultData.status === 'failed') {
      throw new Error(`CapSolver failed: ${resultData.errorDescription}`);
    }
  }
  
  throw new Error('CapSolver timeout');
}

async function solveWithCapMonster(
  apiKey: string,
  captcha: CaptchaData,
  userAgent: string
): Promise<string> {
  const logger = getLogger();
  logger.info('Solving captcha with CapMonster...');
  
  const createTaskRes = await fetch('https://api.capmonster.cloud/createTask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      clientKey: apiKey,
      task: {
        type: 'HCaptchaTaskProxyless',
        websiteURL: 'https://discord.com',
        websiteKey: captcha.captcha_sitekey,
        userAgent,
        isInvisible: true,
        data: captcha.captcha_rqdata,
      },
    }),
  });
  
  const createData = await createTaskRes.json() as { errorId: number; taskId?: number; errorDescription?: string };
  
  if (createData.errorId !== 0) {
    throw new Error(`CapMonster create task failed: ${createData.errorDescription}`);
  }
  
  const taskId = createData.taskId;
  
  for (let i = 0; i < 120; i++) {
    await new Promise(r => setTimeout(r, 1000));
    
    const resultRes = await fetch('https://api.capmonster.cloud/getTaskResult', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clientKey: apiKey, taskId }),
    });
    
    const resultData = await resultRes.json() as { 
      status: string; 
      solution?: { gRecaptchaResponse: string };
      errorDescription?: string;
    };
    
    if (resultData.status === 'ready' && resultData.solution) {
      logger.info('CapMonster: Captcha solved');
      return resultData.solution.gRecaptchaResponse;
    }
    
    if (resultData.status === 'failed') {
      throw new Error(`CapMonster failed: ${resultData.errorDescription}`);
    }
  }
  
  throw new Error('CapMonster timeout');
}

async function solveWithNopeCHA(
  apiKey: string,
  captcha: CaptchaData,
  userAgent: string
): Promise<string> {
  const logger = getLogger();
  logger.info('Solving captcha with NopeCHA...');
  
  const createRes = await fetch('https://api.nopecha.com/token/', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      type: 'hcaptcha',
      sitekey: captcha.captcha_sitekey,
      url: 'https://discord.com',
      data: captcha.captcha_rqdata,
      useragent: userAgent,
    }),
  });
  
  const createData = await createRes.json() as { data?: string; error?: string };
  
  if (createData.error) {
    throw new Error(`NopeCHA failed: ${createData.error}`);
  }
  
  if (createData.data) {
    logger.info('NopeCHA: Captcha solved');
    return createData.data;
  }
  
  throw new Error('NopeCHA: No token returned');
}

export function createCaptchaSolver(config: Config): CaptchaSolverFn | undefined {
  const { captchaService, captchaApiKey } = config;
  
  if (captchaService === 'none' || !captchaApiKey) {
    return undefined;
  }
  
  const logger = getLogger();
  logger.info(`Captcha solver configured: ${captchaService}`);
  
  return async (captcha: CaptchaData, userAgent: string): Promise<string> => {
    switch (captchaService) {
      case 'capsolver':
        return solveWithCapSolver(captchaApiKey, captcha, userAgent);
      case 'capmonster':
        return solveWithCapMonster(captchaApiKey, captcha, userAgent);
      case 'nopecha':
        return solveWithNopeCHA(captchaApiKey, captcha, userAgent);
      default:
        throw new Error(`Unknown captcha service: ${captchaService}`);
    }
  };
}
