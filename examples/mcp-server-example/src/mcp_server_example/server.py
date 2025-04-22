import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastmcp import Context, FastMCP
from mcp_server_lib import browser_manager
from playwright.async_api import Browser, BrowserContext, async_playwright

from .settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)

logger = logging.getLogger(__name__)


class MyBrowser:
    browser: Browser
    context: BrowserContext

    def __init__(self, browser: Browser, context: BrowserContext):
        self.browser = browser
        self.context = context

    async def login(self):
        logger.info("Logging in...")


@dataclass
class AppContext:
    b: MyBrowser


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    async with async_playwright() as p:
        async with browser_manager(
            playwright=p, storage_state_path=settings.storage_state_path
        ) as (browser, context):
            yield AppContext(b=MyBrowser(browser, context))


mcp = FastMCP(
    "mcp-server-example",
    lifespan=app_lifespan,
)


def get_app_context(ctx: Context) -> AppContext:
    return ctx.request_context.lifespan_context


@mcp.tool()
async def login(ctx: Context) -> str:
    """
    Login to the application.
    """
    app_context = get_app_context(ctx)
    await app_context.b.login()
    return "Logged in"
