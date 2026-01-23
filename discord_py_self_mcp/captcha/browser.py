import asyncio
import json
import random
import re
import jwt
import tls_client
from camoufox.async_api import AsyncCamoufox
from typing import Optional, Dict

async def get_hsw_token(req: str, site: str, sitekey: str, proxy: Optional[Dict] = None) -> Optional[str]:
    try:
        browser_options = {
            'headless': True,
            'os': 'windows',
            'locale': ['en-US', 'en']
        }
        
        if proxy:
            # Format proxy for Camoufox
            # proxy dict from solver is {'http': url, 'https': url}
            # Camoufox expects {'server': 'http://ip:port', 'username': ..., 'password': ...}
            # We need to parse the proxy string again if we don't have the broken down components
            # For simplicity, if we get a structured proxy dict, we try to extract it.
            # But the solver passes the full dict.
            # Let's assume proxy is passed as a dict with 'server', 'username', 'password' OR we handle it here.
            # Actually, `solver.py` passes the proxy string to `hsw` in the original code.
            # My `solver.py` will likely handle proxies internally.
            
            # If proxy is a dict compatible with playwright/camoufox:
            browser_options['proxy'] = proxy

        # Create TLS session for initial requests
        session = tls_client.Session(client_identifier="chrome_130", random_tls_extension_order=True)
        if proxy and 'server' in proxy:
            # TLS client needs string format http://user:pass@host:port
            p_server = proxy['server'].replace('http://', '').replace('https://', '')
            p_auth = f"{proxy.get('username','')}:{proxy.get('password','')}" if proxy.get('username') else ""
            p_str = f"http://{p_auth}@{p_server}" if p_auth else f"http://{p_server}"
            session.proxies = {'http': p_str, 'https': p_str}

        async with AsyncCamoufox(**browser_options) as browser:
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}, # Default safe size
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # Mock the site
            await page.route(f"https://{site}/", lambda r: r.fulfill(
                status=200, 
                content_type="text/html", 
                body="<html><head></head><body></body></html>"
            ))
            
            await page.goto(f"https://{site}/", wait_until='domcontentloaded', timeout=10000)

            # Get version
            js_resp = session.get('https://js.hcaptcha.com/1/api.js')
            version_matches = re.findall(r'v1\/([A-Za-z0-9]+)\/static', js_resp.text)
            version = version_matches[1] if len(version_matches) > 1 else version_matches[0]

            # Get HSW script URL
            check_resp = session.post('https://api2.hcaptcha.com/checksiteconfig', params={
                'v': version,
                'host': site,
                'sitekey': sitekey,
                'sc': '1', 'swa': '1', 'spst': '1'
            })
            
            req_token = check_resp.json()["c"]["req"]
            decoded = jwt.decode(req_token, options={"verify_signature": False})
            hsw_url = f"https://newassets.hcaptcha.com{decoded['l']}/hsw.js"
            hsw_js = session.get(hsw_url).text

            # Inject HSW
            await page.evaluate("Object.defineProperty(navigator, 'webdriver', {get: () => false})")
            
            # Try to inject via script tag first, then fallback to eval
            try:
                await page.add_script_tag(content=hsw_js)
            except Exception:
                await page.evaluate(hsw_js)

            # Wait for hsw function
            for _ in range(50):
                is_ready = await page.evaluate("typeof hsw === 'function'")
                if is_ready: break
                await asyncio.sleep(0.1)
            else:
                return None # Failed to load HSW

            # Generate token
            result = await page.evaluate(f"hsw('{req}')")
            return result

    except Exception as e:
        print(f"HSW Error: {e}")
        return None
