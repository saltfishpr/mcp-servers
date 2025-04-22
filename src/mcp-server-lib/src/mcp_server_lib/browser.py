import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Locator, Page, Playwright

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@asynccontextmanager
async def browser_manager(
    *,
    playwright: Playwright,
    headless: bool = False,
    storage_state_path: str,
) -> AsyncIterator[tuple[Browser, BrowserContext]]:
    async def new_context(browser: Browser, storage_state_path: str) -> BrowserContext:
        storage_state = os.path.expanduser(storage_state_path)
        logger.info(f"Storage state path: {storage_state}")
        try:
            directory = os.path.dirname(storage_state)
            if not os.path.exists(directory):
                os.makedirs(directory)
            return await browser.new_context(storage_state=storage_state)
        except Exception as e:
            logger.info(f"Failed to load context, creating a new one: {e}")
            return await browser.new_context()

    browser = await playwright.chromium.launch(headless=headless)
    context = await new_context(browser, storage_state_path)
    try:
        yield browser, context
    finally:
        await context.storage_state(path=storage_state_path)
        await context.close()
        await browser.close()


async def wait_for_stable(
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
        check_interval_ms (int): 单词检查时间间隔，单位为毫秒
        retry_count (int): 尝试次数
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
            logger.debug("[wait_for_stable] Content changed, resetting stable count")
            stable_count = stable_count = 0

        previous_content = current_content
        await page.wait_for_timeout(check_interval_ms)
    return False
