import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import hcaptcha_challenger
from hcaptcha_challenger.agent.challenger import AgentV
from hcaptcha_challenger import models
from loguru import logger


class HCaptchaSolver:
    def __init__(
        self,
        sitekey: str = "a9b5fb07-92ff-493f-86fe-352a2803b3df",
        host: str = "discord.com",
        rqdata: Optional[str] = None,
        proxy: Optional[str] = None,
        debug: bool = False,
        playwright_browser=None,
        gemini_api_key: Optional[str] = None,
    ):
        """Initialize the hCaptcha solver.

        Args:
            sitekey: The hCaptcha sitekey for the target site.
            host: The hostname of the site presenting the CAPTCHA.
            rqdata: Optional request data for the CAPTCHA challenge.
            proxy: Optional proxy string (``user:pass@host:port`` or
                ``host:port``).
            debug: Whether to enable debug logging.
            playwright_browser: An optional pre-launched Playwright browser
                instance.
            gemini_api_key: The Google Gemini API key used for visual
                challenge solving.
        """
        self.sitekey = sitekey
        self.host = host
        self.rqdata = rqdata
        self.proxy_str = proxy
        self.debug = debug
        self.playwright_browser = playwright_browser
        self.gemini_api_key = gemini_api_key

        self._initialized = False
        self._agent: Optional[AgentV] = None
        self._page = None

    def _log(self, msg: str):
        """Print a debug message when debug mode is enabled.

        Args:
            msg: The message to log.
        """
        if self.debug:
            print(f"[HCAPTCHA-CHALLENGER] {msg}")

    async def _ensure_initialized(self):
        """Lazily initialize the Playwright browser and hCaptcha agent.

        This is an async method that launches a headless Chromium browser
        (if one was not provided) and creates the :class:`AgentV` instance
        used to solve challenges.
        """
        if self._initialized:
            return

        self._log("Initializing hcaptcha-challenger...")

        from hcaptcha_challenger.agent.challenger import AgentConfig

        tmp_dir = Path(os.getenv("TEMP_DIR", "/tmp/hcaptcha"))
        tmp_dir.mkdir(parents=True, exist_ok=True)

        if self.playwright_browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self.playwright_browser = await self._playwright.chromium.launch(
                headless=True,
                proxy=self._get_playwright_proxy() if self.proxy_str else None,
            )

        context = await self.playwright_browser.new_context(
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        )
        self._page = await context.new_page()

        agent_config = AgentConfig(
            GEMINI_API_KEY=self.gemini_api_key,
            cache_dir=tmp_dir / ".cache",
            challenge_dir=tmp_dir / ".challenge",
            captcha_response_dir=tmp_dir / ".captcha",
            enable_challenger_debug=self.debug,
        )

        self._agent = AgentV(page=self._page, agent_config=agent_config)

        self._initialized = True
        self._log("Initialized successfully")

    def _get_playwright_proxy(self) -> Optional[Dict]:
        """Parse the proxy string into a Playwright-compatible proxy dict.

        Supports ``user:pass@host:port`` and ``host:port`` formats.

        Returns:
            Optional[Dict]: A proxy configuration dictionary for
                Playwright, or ``None`` if no proxy is set.
        """
        if not self.proxy_str:
            return None

        if "@" in self.proxy_str:
            auth, server = self.proxy_str.split("@")
            user, pwd = auth.split(":")
            return {"server": f"http://{server}", "username": user, "password": pwd}
        return {"server": f"http://{self.proxy_str}"}

    async def solve(self) -> Dict[str, Any]:
        """Solve an hCaptcha challenge and return the token.

        This is an async method that navigates to the target site, waits
        for a CAPTCHA challenge, and solves it using the Gemini-powered
        agent.

        Returns:
            Dict[str, Any]: A dictionary with ``success`` (bool) and
                either ``token`` (str) on success or ``error`` (str) on
                failure.
        """
        self._log("Starting solve process...")

        try:
            await self._ensure_initialized()

            target_url = f"https://{self.host}"

            if self.host == "discord.com":
                target_url = "https://discord.com/channels/@me"

            await self._page.goto(target_url, wait_until="domcontentloaded")

            await self._agent.wait_for_challenge()

            token = await self._agent.get_token()

            if token:
                return {"success": True, "token": token}

            return {"success": False, "error": "Token not found"}

        except Exception as e:
            self._log(f"Solve error: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Clean up browser and Playwright resources.

        This is an async method that closes the browser context and stops
        the Playwright instance.
        """
        try:
            if self._page:
                await self._page.context.close()
            if hasattr(self, "_playwright"):
                await self._playwright.stop()
        except Exception as e:
            self._log(f"Close error: {e}")
