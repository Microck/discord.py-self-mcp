import json
import time
import asyncio
import re
import tls_client
from typing import Dict, Optional, Any
from .browser import get_hsw_token
from .motion import motion_data
from .agent import AIAgent

class HCaptchaSolver:
    def __init__(self, sitekey: str, host: str, rqdata: str = None, proxy: str = None, debug: bool = False):
        self.sitekey = sitekey
        self.host = host.split("//")[-1].split("/")[0]
        self.rqdata = rqdata
        self.proxy_str = proxy
        self.debug = debug
        self.ai_agent = AIAgent()
        
        # Initialize session
        self.session = tls_client.Session(client_identifier="chrome_130", random_tls_extension_order=True)
        self.session.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        }
        
        if proxy:
            # Handle proxy string format username:password@ip:port or ip:port
            p_url = f"http://{proxy}"
            self.session.proxies = {'http': p_url, 'https': p_url}

        self.motion = motion_data(self.session.headers["user-agent"], f"https://{self.host}")
        self.HCAPTCHA_VERSION = self._get_version()

    def _log(self, msg: str):
        if self.debug: print(f"[SOLVER] {msg}")

    def _get_version(self) -> str:
        try:
            resp = self.session.get('https://hcaptcha.com/1/api.js?render=explicit&onload=hcaptchaOnLoad')
            matches = re.findall(r'v1/([A-Za-z0-9]+)/static', resp.text)
            return matches[1] if len(matches) > 1 else "c3663008fb8d8104807d55045f8251cbe96a2f84"
        except:
            return "c3663008fb8d8104807d55045f8251cbe96a2f84"

    async def solve(self) -> Dict:
        self._log("Starting solve process...")
        
        # 1. Get site config
        config = self._get_site_config()
        if not config: return {"success": False, "error": "Failed to get site config"}
        
        # 2. Get HSW token
        if 'c' not in config: return {"success": False, "error": "Invalid config"}
        hsw = await get_hsw_token(config['c']['req'], self.host, self.sitekey, self._get_proxy_dict())
        if not hsw: return {"success": False, "error": "Failed to generate HSW token"}
        
        # 3. Fetch challenge
        challenge = await self._fetch_challenge(config, hsw)
        if not challenge: return {"success": False, "error": "Failed to fetch challenge"}
        
        # Check for passive pass
        if challenge.get('generated_pass_UUID'):
            return {"success": True, "token": challenge['generated_pass_UUID']}
            
        # 4. Solve challenge with AI
        ai_result = await self.ai_agent.solve_challenge(challenge)
        answers = self._format_answers(ai_result, challenge)
        
        # 5. Submit solution
        result = await self._submit(challenge, answers, hsw)
        return result

    def _get_proxy_dict(self) -> Optional[Dict]:
        if not self.proxy_str: return None
        # Simple parser, assumes http proxy
        if '@' in self.proxy_str:
            auth, server = self.proxy_str.split('@')
            user, pwd = auth.split(':')
            return {'server': f'http://{server}', 'username': user, 'password': pwd}
        return {'server': f'http://{self.proxy_str}'}

    def _get_site_config(self) -> Optional[Dict]:
        params = {
            'v': self.HCAPTCHA_VERSION, 'sitekey': self.sitekey,
            'host': self.host, 'sc': '1', 'swa': '1', 'spst': '1'
        }
        if self.rqdata: params['rqdata'] = self.rqdata
        
        resp = self.session.post("https://api2.hcaptcha.com/checksiteconfig", params=params)
        if resp.status_code == 200:
            data = resp.json()
            if 'rqdata' in data: self.rqdata = data['rqdata']
            return data
        return None

    async def _fetch_challenge(self, config: Dict, hsw_token: str) -> Optional[Dict]:
        data = {
            'v': self.HCAPTCHA_VERSION, 'sitekey': self.sitekey,
            'host': self.host, 'hl': 'en-US',
            'motionData': json.dumps(self.motion.get_captcha()),
            'n': hsw_token, 'c': json.dumps(config['c'])
        }
        if self.rqdata: data['rqdata'] = self.rqdata
        
        resp = self.session.post(f"https://api.hcaptcha.com/getcaptcha/{self.sitekey}", data=data)
        if resp.status_code == 200:
            return resp.json()
        return None

    def _format_answers(self, ai_result: Dict, challenge: Dict) -> Dict:
        # Simplified formatting based on request_type
        # The AI agent now returns formatted answers (x, y dicts) or similar
        # We just need to map them to task keys if necessary
        req_type = challenge.get('request_type')
        tasklist = challenge.get('tasklist', [])
        ai_answers = ai_result.get('answers', [])
        
        formatted = {}
        
        if req_type == 'image_label_binary':
            # Map grid coordinates to task keys
            # ai_answers is list of {x: col, y: row}
            # tasklist is flat list of 9 items
            selected_indices = {a['y'] * 3 + a['x'] for a in ai_answers}
            for i, task in enumerate(tasklist):
                formatted[task['task_key']] = "true" if i in selected_indices else "false"
                
        elif req_type == 'image_label_area_select':
            # Single task usually
            for i, task in enumerate(tasklist):
                pt = ai_answers[i] if i < len(ai_answers) else {'x': 200, 'y': 150}
                formatted[task['task_key']] = [{"entity_name": 0, "entity_type": "default", "entity_coords": [pt['x'], pt['y']]}]
                
        elif req_type == 'image_drag_drop':
             main = tasklist[0]
             formatted[main['task_key']] = []
             for ans in ai_answers:
                 formatted[main['task_key']].append({
                     "entity_name": ans.get('entity_id'),
                     "entity_type": "default",
                     "entity_coords": [ans.get('to_x'), ans.get('to_y')]
                 })
                 
        return formatted

    async def _submit(self, challenge: Dict, answers: Dict, hsw_token: str) -> Dict:
        data = {
            'v': self.HCAPTCHA_VERSION, 'sitekey': self.sitekey,
            'serverdomain': self.host, 'job_mode': challenge['request_type'],
            'motionData': json.dumps(self.motion.check_captcha()),
            'n': hsw_token, 'c': json.dumps(challenge['c']),
            'answers': answers
        }
        if self.rqdata: data['rqdata'] = self.rqdata
        
        url = f"https://api.hcaptcha.com/checkcaptcha/{self.sitekey}/{challenge['key']}"
        resp = self.session.post(url, data=json.dumps(data), headers={
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://newassets.hcaptcha.com',
            'referer': 'https://newassets.hcaptcha.com/'
        })
        
        if resp.status_code == 200:
            res = resp.json()
            if res.get('pass'):
                return {"success": True, "token": res.get('generated_pass_UUID')}
            return {"success": False, "error": "Rejected"}
        return {"success": False, "error": f"HTTP {resp.status_code}"}
