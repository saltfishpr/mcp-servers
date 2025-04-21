import logging
import os

from playwright.async_api import Browser, BrowserContext, Locator, Page, Playwright

logger = logging.getLogger(__name__).addHandler(logging.NullHandler())


class BaseBrowser:
    _playwright: Playwright
    _headless: bool
    _storage_state_path: str | None
    _browser: Browser | None
    _context: BrowserContext | None

    def __init__(
        self,
        *,
        playwright: Playwright,
        storage_state_path: str | None,
        headless: bool = False,
    ):
        self._playwright = playwright
        self._headless = headless

        if storage_state_path:
            self._storage_state_path = os.path.expanduser(storage_state_path)
            logger.info(f"Storage state path: {self._storage_state_path}")
            directory = os.path.dirname(self._storage_state_path)
            os.makedirs(directory, exist_ok=True)
        self._browser = None
        self._context = None

    async def __aenter__(self):
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        try:
            self._context = await self._browser.new_context(
                storage_state=self._storage_state_path
            )
            logger.info("Session loaded successfully")
        except Exception as e:
            logger.info(f"Failed to load session, creating a new one: {e}")
            self._context = await self._browser.new_context()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            logger.info("Saving session...")
            await self._context.storage_state(path=self._storage_state_path)
            await self._context.close()
        if self._browser:
            await self._browser.close()

    async def new_page(self) -> Page:
        if not self._context:
            raise Exception("Browser context is not initialized.")
        return await self._context.new_page()

    async def wait_for_stable(
        self,
        page: Page,
        locator: Locator,
        check_interval_ms: int = 1000,
        retry_count: int = 10,
        threshold: int = 2,
    ) -> bool:
        """
        等待 locator.outerHTML 稳定

        Args:
            page (Page): Playwright 页面对象
            locator (Locator): 要检查的元素的 Locator 对象
            wait_timeout (int): 单词检查时间间隔，单位为毫秒
            max_attempts (int): 尝试次数
            threshold (int): 稳定的阈值，表示连续相同的次数
        """
        previous_content = ""
        stable_count = 0
        for _ in range(retry_count):
            current_content = await locator.evaluate("e => e.outerHTML")

            if current_content == previous_content:
                stable_count += 1
                logger.debug("[wait_for_stable] Stable count: %d", stable_count)
                if stable_count >= threshold:
                    return True
            else:
                logger.debug(
                    "[wait_for_stable] Content changed, resetting stable count"
                )
                stable_count = stable_count = 0

            previous_content = current_content
            await page.wait_for_timeout(check_interval_ms)
        return False
