import asyncio
import base64
import logging
import os
import urllib.parse
from datetime import datetime
from typing import AsyncGenerator

from playwright.async_api import Locator, Page, Playwright
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Note(BaseModel):
    title: str  # 笔记标题
    cover: str  # 笔记封面
    author: str  # 作者
    content: str | None  # 笔记内容
    images: list[str] | None  # 笔记图片
    tags: list[str] | None  # 笔记标签
    date: datetime | None


class SearchNotesParams(BaseModel):
    keyword: str  # 搜索关键词
    limit: int = 10  # 返回的笔记数量限制


class SearchNotesResult(BaseModel):
    data_idx: int  # 笔记索引
    title: str  # 笔记标题
    cover: str  # 笔记封面
    author: str  # 作者
    likes: str  # 点赞数


class RedNoteError(Exception):
    """自定义异常类，用于处理小红书相关的错误"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class RedNoteApiError(Exception):
    """自定义异常类，用于处理小红书 API 相关的错误"""

    def __init__(
        self,
        method: str,
        url: str,
        status_code: int,
        code: int,
        message: str,
        body: str,
    ):
        super().__init__(message)
        self.method = method
        self.url = url
        self.status_code = status_code
        self.code = code
        self.message = message
        self.body = body

    def __str__(self):
        return (
            f"RedNoteApiError: {self.method} {self.url} "
            f"Status Code: {self.status_code}, "
            f"Body: {self.body}"
        )


class RedNote:
    BASE_URL = "https://www.xiaohongshu.com"

    def __init__(
        self,
        playwright: Playwright,
        headless: bool = False,
        storage_state_path: str = "~/.mcp/rednote/state.json",
    ):
        """
        初始化 Rednote 类。

        Args:
            playwright (Playwright): Playwright 库的一个实例，用于浏览器自动化。
            headless (bool, 可选): 决定浏览器是否在无头模式下运行。默认为 False。
            storage_state_path (str, 可选): 用于会话持久性的存储状态文件的路径。
                默认为 "~/.mcp/rednote/state.json"。

        Attributes:
            _playwright (Playwright): Playwright 库的实例。
            _headless (bool): 指示浏览器是否在无头模式下运行。
            _storage_state_path (str): 存储状态文件的展开路径。
            _event_login_success (asyncio.Event): 用于标记成功登录的事件。
        """
        if not playwright:
            raise RedNoteError("Playwright instance is required")
        if headless is None:
            raise RedNoteError("headless is required")
        logger.info(
            f"Args: headless={headless}, storage_state_path={storage_state_path}"
        )
        self._playwright: Playwright = playwright
        self._headless: bool = headless
        self._storage_state_path: str = os.path.expanduser(storage_state_path)
        try:
            directory = os.path.dirname(self._storage_state_path)
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            raise RedNoteError(f"创建目录{directory}失败: {e}")
        self._browser = None
        self._context = None
        self.__event_login_success: asyncio.Event = asyncio.Event()
        logger.info("RedNote initialized")

    async def __aenter__(self):
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        try:
            self._context = await self._browser.new_context(
                storage_state=self._storage_state_path
            )
            logger.info("加载会话成功")
        except Exception as e:
            logger.info(f"加载会话失败，创建新的会话: {e}")
            self._context = await self._browser.new_context()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._context.storage_state(path=self._storage_state_path)
        await self._context.close()
        await self._browser.close()

    async def new_page(self, url: str) -> Page:
        page = await self._context.new_page()
        await page.goto(url)
        return page

    async def is_user_logged_in(self) -> bool:
        """
        检查是否已登录小红书

        Returns:
            bool: 是否已登录
        """
        try:
            resp = await self._context.request.get(
                "https://edith.xiaohongshu.com/api/sns/web/v2/user/me"
            )
            if not resp.ok:
                raise RedNoteApiError(
                    method="get",
                    url=resp.url,
                    status_code=resp.status,
                )
            respBody = await resp.json()
            code = respBody.get("code")
            if code != 0:
                raise RedNoteApiError(
                    method="get",
                    url=resp.url,
                    status_code=resp.status,
                    code=code,
                    message=respBody.get("message", ""),
                    body=respBody,
                )
            if respBody.get("data", {}).get("guest", True):
                return False
            return True
        except Exception as e:
            logger.error(e)
            return False

    async def login(self) -> str:
        """
        导航到 explore 页面、获取二维码并等待登录

        Returns:
            str: 用于登录的 Base64 格式的二维码图片。
        """
        page = await self._context.new_page()
        await page.goto(self.BASE_URL + "/explore")
        qr_code_base64 = await self.__get_qr_code_image(page)
        # 使用异步函数在后台等待登录
        asyncio.create_task(self.__wait_for_login(page))
        # 立即返回二维码图片
        return qr_code_base64

    async def __get_qr_code_image(self, page: Page) -> str:
        # 等待二维码元素加载完成
        qrcode_element = page.locator(".qrcode .qrcode-img")
        await qrcode_element.wait_for(state="visible")
        # 获取二维码图片的src属性（如果是<img>标签）
        qr_code_src = await qrcode_element.get_attribute("src")
        # 如果src是data:image/png;base64形式，直接提取base64部分
        if qr_code_src and "data:image" in qr_code_src:
            return qr_code_src.split("base64,")[1]
        # 如果src是URL，需要下载图片并转换
        elif qr_code_src:
            # 使用Playwright下载图片
            async with page.request.get(qr_code_src) as response:
                image_buffer = await response.body()
                return base64.b64encode(image_buffer).decode("utf-8")
        else:
            # 无法获取src时，尝试截图
            screenshot_buffer = await qrcode_element.screenshot()
            return base64.b64encode(screenshot_buffer).decode("utf-8")

    async def __wait_for_login(self, page: Page) -> None:
        try:
            # 等待扫码
            status_element = page.locator(".qrcode .status .status-text")
            await status_element.wait_for(state="visible", timeout=60000)
            status_text = (await status_element.text_content()).strip()
            if status_text != "扫码成功":
                raise RedNoteError(f"登录失败: {status_text}")
            # 等待登录
            user_element = page.locator(".side-bar .user")
            await user_element.wait_for(state="visible", timeout=60000)
            # TODO 登录次数过多可能需要人机校验
            # 登录成功
            await self._context.storage_state(path=self._storage_state_path)
            self.__event_login_success.set()
        except Exception as e:
            logger.error(f"Login error: {e}")
        finally:
            await page.close()

    async def wait_for_login_success(self, timeout: float) -> None:
        """
        等待登录成功的事件

        Args:
            timeout (float): 超时时间，单位为秒
        """
        try:
            await asyncio.wait_for(self.__event_login_success.wait(), timeout)
        except asyncio.TimeoutError:
            raise RedNoteError("登录超时，请重新扫码登录")

    async def search_notes(
        self,
        page: Page,
        params: SearchNotesParams,
    ) -> list[SearchNotesResult]:
        """
        搜索小红书笔记，获取笔记列表

        Args:
            page (Page): Playwright 页面对象
            params (SearchNotesParams): 搜索参数

        Returns:
            list[SearchNotesResult]: 笔记列表
        """
        encoded_keyword = urllib.parse.quote(params.keyword)
        await page.goto(f"{self.BASE_URL}/search_result?keyword={encoded_keyword}")
        result = []
        async for note in self.__load_notes(page, params.limit):
            result.append(note)
        return result

    async def __load_notes(
        self, page: Page, limit: int
    ) -> AsyncGenerator[SearchNotesResult]:
        data_idx_set = set()

        while True:
            feeds_container = page.locator(".search-layout .feeds-container")
            await feeds_container.wait_for(state="visible", timeout=10000)
            feeds = feeds_container.locator("> section")
            # 等待内容稳定
            await self.wait_for_content_stabilization(
                page=page,
                locator=feeds.first,
                wait_timeout=1,
                max_attempts=10,
            )
            feeds_count = await feeds.count()
            for i in range(feeds_count):
                section = feeds.nth(i)

                # 判断 section 下是否有 a 元素，没有则跳过
                count_a = await section.locator("> div a").count()
                if count_a == 0:
                    logger.info("非笔记 section，跳过")
                    continue

                data_idx = await section.get_attribute("data-index")
                data_idx = int(data_idx)
                if data_idx in data_idx_set:
                    logger.info(f"笔记 {data_idx} 已存在，跳过该笔记")
                    continue
                data_idx_set.add(data_idx)
                if len(data_idx_set) >= limit:
                    break

                title_element = section.locator(".title span")
                title = await title_element.inner_text()
                cover_element = section.locator(".cover img")
                cover = await cover_element.get_attribute("src")
                author_element = section.locator(".author .name")
                author = await author_element.inner_text()
                likes_element = section.locator(".like-wrapper .count")
                likes = await likes_element.inner_text()
                logger.info(f"笔记 {data_idx}：{title}, 作者 {author}，点赞数 {likes}")
                yield SearchNotesResult(
                    data_idx=data_idx,
                    title=title,
                    cover=cover,
                    author=author,
                    likes=likes,
                )
            if len(data_idx_set) >= limit:
                break
            # 滚动页面以加载更多笔记
            await page.evaluate("window.scrollBy(0, 1000);")

    async def wait_for_content_stabilization(
        self,
        page: Page,
        locator: Locator,
        wait_timeout: int = 1,
        max_attempts: int = 10,
    ):
        """
        等待页面内容稳定

        Args:
            page (Page): Playwright 页面对象
            locator (Locator): 要检查的元素的 Locator 对象
            wait_timeout (int): 等待时间，单位为秒
            max_attempts (int): 最大尝试次数
        """
        previous_content: str = ""
        stable_count = 0

        for attempt in range(max_attempts):
            current_content: str = await locator.evaluate("node => node.outerHTML")

            if current_content == previous_content:
                stable_count += 1
                if stable_count >= 2:  # 连续两次检查数量相同，认为稳定
                    break
            else:
                stable_count = 0

            previous_content = current_content
            await page.wait_for_timeout(wait_timeout * 1000)

    async def extract_note_content(self, page: Page, section: Locator) -> Note:
        """
        提取小红书笔记的内容

        Args:
            page (Page): Playwright 页面对象
            feed (Locator): 笔记的 Locator 对象

        Returns:
            Note: 包含笔记信息的 Note 对象
        """
        pass
