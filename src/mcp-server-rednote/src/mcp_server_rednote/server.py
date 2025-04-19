import logging
from enum import Enum

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel

from .rednote import RedNote, SearchNotesParams


class RedNoteTools(str, Enum):
    CHECK_LOGIN = "check_login"
    LOGIN = "login"
    SEARCH_NOTES = "search_notes"


class CheckLoginRequest(BaseModel):
    pass


class LoginRequest(BaseModel):
    pass


class SearchNotesRequest(BaseModel):
    keyword: str
    limit: int = 10


async def serve(rednote: RedNote) -> None:
    logger = logging.getLogger(__name__)
    server = Server("mcp-server-rednote")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name=RedNoteTools.CHECK_LOGIN,
                description="检查用户登录状态",
                inputSchema=CheckLoginRequest.model_json_schema(),
            ),
            Tool(
                name=RedNoteTools.LOGIN,
                description="登录小红书",
                inputSchema=LoginRequest.model_json_schema(),
            ),
            Tool(
                name=RedNoteTools.SEARCH_NOTES,
                description="搜索小红书笔记，返回笔记列表",
                inputSchema=SearchNotesRequest.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        match name:
            case RedNoteTools.CHECK_LOGIN:
                try:
                    if await rednote.is_user_logged_in():
                        return [TextContent(type="text", text="用户已登录")]
                    else:
                        return [TextContent(type="text", text="用户未登录")]
                except Exception as e:
                    logger.error(f"Check login failed: {e}")
                    return [TextContent(type="text", text="检查登录状态失败")]
            case RedNoteTools.LOGIN:
                try:
                    await rednote.login()
                    await rednote.wait_for_login_success(timeout=60)
                    return [TextContent(type="text", text="登录成功")]
                except Exception as e:
                    logger.error(f"Login failed: {e}")
                    return [TextContent(type="text", text="登录失败")]
            case RedNoteTools.SEARCH_NOTES:
                try:
                    page = await rednote.new_page("https://www.xiaohongshu.com/explore")
                    notes = await rednote.search_notes(
                        page=page, params=SearchNotesParams(**arguments)
                    )
                    return [TextContent(type="text", text=f"Notes:\n{notes}")]
                except Exception as e:
                    logger.error(f"Search notes failed: {e}")
                    return [TextContent(type="text", text="搜索笔记失败")]
            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
