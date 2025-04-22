import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastmcp import Context, FastMCP
from mcp_server_lib import browser_manager
from playwright.async_api import async_playwright

from .browser import QQMusic
from .settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    qq: QQMusic


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    async with async_playwright() as p:
        async with browser_manager(
            playwright=p, storage_state_path=settings.storage_state_path
        ) as (browser, context):
            yield AppContext(qq=QQMusic(browser, context))


mcp = FastMCP(
    "mcp-server-qq-music",
    instructions="tips: 请在使用工具前校验登录状态",
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
    if await get_app_context(ctx).qq.check_login():
        return "已登录"
    else:
        return "未登录"


@mcp.tool()
async def login(ctx: Context) -> str:
    """登录QQ音乐

    Returns:
        str: 操作结果
    """
    app_context = get_app_context(ctx)
    try:
        page = await app_context.qq.context.new_page()
        await app_context.qq.login(page=page)
        return "登录成功"
    except Exception:
        logger.exception("Login failed")
        return "登录失败"
    finally:
        if page:
            await page.close()


@mcp.tool()
async def search_songs(ctx: Context, keyword: str) -> str:
    """搜索歌曲，返回歌曲列表

    Args:
        keyword (str): 搜索关键词，如 "海阔天空"

    Returns:
        str: 歌曲列表，包括歌曲名称、歌手和链接
    """
    app_context = get_app_context(ctx)
    try:
        page = await app_context.qq.context.new_page()
        songs = await app_context.qq.search_songs(page=page, keyword=keyword)
        return "\n".join([song.model_dump_json() for song in songs])
    except Exception:
        logger.exception("Search songs failed")
        return "搜索歌曲失败"
    finally:
        if page:
            await page.close()


@mcp.tool()
async def get_song(ctx: Context, link: str) -> str:
    """输入歌曲链接，返回歌曲详情

    Args:
        link (str): 歌曲链接，如 "/n/ryqq/songDetail/002nHTx62ug8MZ"

    Returns:
        str: 歌曲详情，包括歌曲名称、歌手、歌曲描述、歌词和评论
    """
    app_context = get_app_context(ctx)
    try:
        page = await app_context.qq.context.new_page()
        song = await app_context.qq.get_song(page=page, link=link)
        return song.model_dump_json()
    except Exception:
        logger.exception("Get song failed")
        return "获取歌曲失败"
    finally:
        if page:
            await page.close()
