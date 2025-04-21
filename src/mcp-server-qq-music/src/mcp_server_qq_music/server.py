import logging
from enum import Enum

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel

from .client import QQMusic


class ServerTools(str, Enum):
    CHECK_LOGIN = "check_login"
    LOGIN = "login"
    SEARCH_SONGS = "search_songs"
    GET_SONG = "get_song"
    DEBUG = "debug"


class CheckLoginRequest(BaseModel):
    pass


class LoginRequest(BaseModel):
    pass


class SearchSongsRequest(BaseModel):
    keyword: str  # 搜索关键词，如 "海阔天空"


class GetSongRequest(BaseModel):
    link: str  # 歌曲链接，如 /n/ryqq/songDetail/002nHTx62ug8MZ


async def serve(qq: QQMusic) -> None:  # noqa: C901
    logger = logging.getLogger(__name__)
    server = Server(
        "mcp-server-qq-music",
        instructions="请在使用工具前校验登录状态",
    )

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name=ServerTools.CHECK_LOGIN,
                description="检查用户登录状态",
                inputSchema=CheckLoginRequest.model_json_schema(),
            ),
            Tool(
                name=ServerTools.LOGIN,
                description="登录QQ音乐",
                inputSchema=LoginRequest.model_json_schema(),
            ),
            Tool(
                name=ServerTools.SEARCH_SONGS,
                description="搜索歌曲，返回歌曲列表，包括歌曲名称、歌手和链接",
                inputSchema=SearchSongsRequest.model_json_schema(),
            ),
            Tool(
                name=ServerTools.GET_SONG,
                description="输入歌曲链接，返回歌曲详情，包括描述、歌词和评论",
                inputSchema=GetSongRequest.model_json_schema(),
            ),
            # Tool(
            #     name=ServerTools.DEBUG,
            #     description="调试工具，保持连接5分钟",
            #     inputSchema=CheckLoginRequest.model_json_schema(),
            # ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        match name:
            case ServerTools.CHECK_LOGIN:
                if await qq.check_login():
                    return [TextContent(type="text", text="已登录")]
                else:
                    return [TextContent(type="text", text="未登录")]
            case ServerTools.LOGIN:
                try:
                    page = await qq.new_page()
                    await qq.login(page=page)
                    return [TextContent(type="text", text="登录成功")]
                except Exception as e:
                    logger.error(f"Login failed: {e}")
                    return [TextContent(type="text", text="登录失败")]
                finally:
                    if page:
                        await page.close()
            case ServerTools.SEARCH_SONGS:
                try:
                    req = SearchSongsRequest(**arguments)
                    page = await qq.new_page()
                    songs = await qq.search_songs(page=page, keyword=req.keyword)
                    return [
                        TextContent(
                            type="text",
                            text="\n".join([song.model_dump_json() for song in songs]),
                        )
                    ]
                except Exception as e:
                    logger.error(f"Search songs failed: {e}")
                    return [TextContent(type="text", text="搜索歌曲失败")]
                finally:
                    if page:
                        await page.close()
            case ServerTools.GET_SONG:
                try:
                    req = GetSongRequest(**arguments)
                    page = await qq.new_page()
                    song = await qq.get_song(page=page, link=req.link)
                    return [
                        TextContent(
                            type="text",
                            text=song.model_dump_json(),
                        )
                    ]
                except Exception as e:
                    logger.error(f"Get song failed: {e}")
                    return [TextContent(type="text", text="获取歌曲失败")]
                finally:
                    if page:
                        await page.close()
            case ServerTools.DEBUG:
                try:
                    page = await qq.new_page()
                    await page.goto(qq.BASE_URL)
                    await page.wait_for_timeout(300 * 1000)  # Wait for 5 minutes
                except Exception as e:
                    logger.error(f"Debug failed: {e}")
                    return [TextContent(type="text", text="Debug failed")]
                finally:
                    if page:
                        await page.close()
            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
