import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastmcp import Context, FastMCP
from mcp_server_lib import browser_manager
from playwright.async_api import async_playwright

from .browser import RedNote
from .settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    rednote: RedNote


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    async with async_playwright() as p:
        async with browser_manager(
            playwright=p, storage_state_path=settings.storage_state_path
        ) as (browser, context):
            yield AppContext(rednote=RedNote(browser, context))


mcp = FastMCP(
    "mcp-server-rednote",
    lifespan=app_lifespan,
)


def get_app_context(ctx: Context) -> AppContext:
    return ctx.request_context.lifespan_context


@mcp.tool()
async def check_login(ctx: Context) -> str:
    """检查登录状态

    Returns:
        str: 登录状态
    """
    if await get_app_context(ctx).rednote.is_user_logged_in():
        return "已登录"
    else:
        return "未登录"


@mcp.tool()
async def login(ctx: Context) -> str:
    """登录小红书

    Returns:
        str: 操作结果
    """
    try:
        page = await get_app_context(ctx).rednote.context.new_page()
        await get_app_context(ctx).rednote.login(page=page)
        return "登录成功"
    except Exception:
        logger.exception("Login failed")
        return "登录失败"
    finally:
        if page:
            await page.close()


@mcp.tool()
async def search_notes(ctx: Context, keyword: str, limit: int = 10) -> str:
    """搜索小红书笔记

    Args:
        keyword (str): 搜索关键词
        limit (int, optional): 返回笔记数量. Defaults to 10.

    Returns:
        str: 笔记列表
    """
    try:
        page = await get_app_context(ctx).rednote.context.new_page()
        notes = await get_app_context(ctx).rednote.search_notes(
            page=page, keyword=keyword, limit=limit
        )
        return "\n".join([note.model_dump_json() for note in notes])
    except Exception:
        logger.exception("Search notes failed")
        return "搜索笔记失败"
    finally:
        if page:
            await page.close()
