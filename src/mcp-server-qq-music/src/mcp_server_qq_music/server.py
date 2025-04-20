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


class CheckLoginRequest(BaseModel):
    pass


class LoginRequest(BaseModel):
    pass


async def serve(qq: QQMusic) -> None:
    logger = logging.getLogger(__name__)
    server = Server("mcp-server-qq-music")

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
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        match name:
            case ServerTools.CHECK_LOGIN:
                try:
                    page = await qq._context.new_page()
                    await page.goto(QQMusic.BASE_URL)
                    if await qq.is_user_logged_in(page=page):
                        return [TextContent(type="text", text="已登录")]
                    else:
                        return [TextContent(type="text", text="未登录")]
                except Exception as e:
                    logger.error(f"Check login failed: {e}")
                    return [TextContent(type="text", text="检查登录状态失败")]
                finally:
                    if page:
                        await page.close()
            case ServerTools.LOGIN:
                try:
                    await qq.login()
                    return [TextContent(type="text", text="登录成功")]
                except Exception as e:
                    logger.error(f"Login failed: {e}")
                    return [TextContent(type="text", text="登录失败")]
            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
