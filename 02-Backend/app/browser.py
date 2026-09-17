import os
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page


class BrowserAutomation:
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def _ensure_browser(self):
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        if self._browser is None or not self._browser.is_connected():
            self._browser = await self._playwright.chromium.launch(headless=True)
        if self._page is None or self._page.is_closed():
            self._page = await self._browser.new_page()

    async def navigate(self, url: str) -> str:
        await self._ensure_browser()
        await self._page.goto(url, timeout=30000)
        return await self._page.content()

    async def screenshot(self) -> bytes:
        await self._ensure_browser()
        return await self._page.screenshot(full_page=False)

    async def click(self, selector: str) -> bool:
        await self._ensure_browser()
        try:
            await self._page.click(selector, timeout=5000)
            return True
        except Exception:
            return False

    async def type_text(self, selector: str, text: str) -> bool:
        await self._ensure_browser()
        try:
            await self._page.fill(selector, text, timeout=5000)
            return True
        except Exception:
            return False

    async def close(self):
        if self._page and not self._page.is_closed():
            await self._page.close()
        if self._browser and self._browser.is_connected():
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
