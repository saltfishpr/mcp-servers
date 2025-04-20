import logging
import os

from playwright.async_api import Browser, BrowserContext, Locator, Page, Playwright


class BaseBrowser:
    logger: logging.Logger = logging.getLogger(__name__)

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
        self.logger.info(
            f"Args: headless={headless}, storage_state_path={storage_state_path}"
        )
        self._playwright = playwright
        self._headless = headless

        if storage_state_path:
            self._storage_state_path = os.path.expanduser(storage_state_path)
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
            self.logger.info("加载会话成功")
        except Exception as e:
            self.logger.info(f"加载会话失败，创建新的会话: {e}")
            self._context = await self._browser.new_context()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            await self._context.storage_state(path=self._storage_state_path)
            await self._context.close()
        if self._browser:
            await self._browser.close()

    async def wait_for_content_stabilization(
        self,
        page: Page,
        locator: Locator,
        wait_timeout: int = 1000,
        max_attempts: int = 10,
    ) -> bool:
        """
        等待页面内容稳定

        Args:
            page (Page): Playwright 页面对象
            locator (Locator): 要检查的元素的 Locator 对象
            wait_timeout (int): 等待时间，单位为毫秒
            max_attempts (int): 最大尝试次数
        """
        previous_content: str = ""
        stable_count = 0
        for _ in range(max_attempts):
            current_content: str = await locator.evaluate("node => node.outerHTML")

            if current_content == previous_content:
                stable_count += 1
                if stable_count >= 2:  # 连续两次检查数量相同，认为稳定
                    return True
            else:
                stable_count = 0

            previous_content = current_content
            await page.wait_for_timeout(wait_timeout)
        return False
