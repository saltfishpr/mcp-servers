import logging

from mcp_server_lib import BaseBrowser
from playwright.async_api import Locator, Page, Playwright
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CommentGroup(BaseModel):
    name: str  # 评论组名称
    comments: list["Comment"]  # 评论列表


class Comment(BaseModel):
    username: str  # 用户名
    date_and_location: str  # 评论日期和IP属地
    content: str  # 评论内容
    likes: int  # 点赞数
    reply_count: int  # 回复数
    replies: list["CommentReply"] | None  # 回复列表


class CommentReply(BaseModel):
    username: str  # 回复用户名
    content: str  # 回复内容
    likes: int  # 点赞数


class Song(BaseModel):
    title: str  # 歌名
    about: str | None = None  # 简介
    artists: list[str]  # 歌手
    link: str | None = None  # 歌曲链接
    cover: str | None = None  # 封面
    album: str | None = None  # 专辑
    duration: str | None = None  # 时长
    lyrics: list[str] | None = None  # 歌词
    comments: list[CommentGroup] | None = None  # 评论组列表


class QQMusic(BaseBrowser):
    BASE_URL = "https://y.qq.com"

    def __init__(
        self,
        *,
        playwright: Playwright,
        **kwargs,
    ):
        super().__init__(
            playwright=playwright,
            **kwargs,
        )

    async def __aenter__(self):
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def check_login(self) -> bool:
        """
        检查用户是否已登录。

        Returns:
            bool: 如果用户已登录返回 True，否则返回 False。
        """
        try:
            page = await self.new_page()
            await page.goto(QQMusic.BASE_URL)
            if await self.__is_user_logged_in(page=page):
                return True
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
        finally:
            if page:
                await page.close()
        return False

    async def __is_user_logged_in(self, page: Page) -> bool:
        login_btn = page.locator(".mod_header .top_login__link")
        await login_btn.wait_for()
        try:
            await self.wait_for_stable(page=page, locator=login_btn)
            profile_herf = await login_btn.get_attribute("href")
            return profile_herf is not None
        except Exception as e:
            logger.info(f"[__is_user_logged_in]: {e}")
            return False

    async def login(self, page: Page) -> None:
        await page.goto(self.BASE_URL)

        login_btn = page.locator(".mod_header .top_login__link")
        await login_btn.wait_for()

        if await self.__is_user_logged_in(page=page):
            logger.info("Already logged in")
            return
        await login_btn.click()

        dialog_root = page.locator(".yqq-dialog")
        await dialog_root.wait_for()

        login_iframe = page.frame_locator("iframe#login_frame")
        ptlogin_iframe = login_iframe.frame_locator("iframe#ptlogin_iframe")
        login_list = ptlogin_iframe.locator("#login.login .qlogin_list")
        await login_list.wait_for()
        # 等待登录列表加载
        face_count = await login_list.locator(".face").count()
        if face_count != 0:
            # 已经登陆qq时，点击头像登录
            await login_list.locator(".face").first.click()
        # 等待登录框消失
        await dialog_root.wait_for(state="detached", timeout=60000)
        # 再次检查登录状态
        if not await self.__is_user_logged_in(page=page):
            raise Exception("登录失败")

    async def search_songs(self, page: Page, keyword: str) -> list[Song]:
        await page.goto(f"{self.BASE_URL}/n/ryqq/search?w={keyword}&t=song")

        root = page.locator(".result")
        loading = root.locator(".mod_loading")
        await loading.wait_for()
        await loading.wait_for(state="detached")

        # 等待搜索结果加载
        song_list_items = root.locator(".songlist__list").locator("> li")
        song_list_items_count = await song_list_items.count()

        results = []
        for i in range(song_list_items_count):
            song_item = song_list_items.nth(i)
            name = await song_item.locator(".songlist__songname_txt a").get_attribute(
                "title"
            )
            link = await song_item.locator(".songlist__songname_txt a").get_attribute(
                "href"
            )
            artist_elements = song_item.locator(".songlist__artist a")
            artist_count = await artist_elements.count()
            artists = []
            for j in range(artist_count):
                song_artist = await artist_elements.nth(j).get_attribute("title")
                artists.append(song_artist)
            album = None
            if await has_element(song_item, ".songlist__album a"):
                album = await song_item.locator(".songlist__album a").inner_text()
            duration = await song_item.locator(".songlist__time").inner_text()
            results.append(
                Song(
                    title=name,
                    artists=artists,
                    album=album,
                    duration=duration,
                    link=link,
                )
            )
        return results

    async def get_song(self, page: Page, link: str) -> Song:
        """
        获取歌曲详情

        Args:
            page (Page): Playwright Page 对象
            link (str): 歌曲链接

        Returns:
            GetSongResult: 歌曲详情
        """
        await page.goto(f"{self.BASE_URL}{link}")

        song_info_root = page.locator(".mod_data")
        await song_info_root.wait_for()

        # 提取歌名
        title = await song_info_root.locator(".data__name_txt").get_attribute("title")
        # 提取歌手
        artist_elements = song_info_root.locator(".data__singer_txt")
        artists = [
            await artist_elements.nth(i).get_attribute("title")
            for i in range(await artist_elements.count())
        ]
        # 提取专辑
        album = await song_info_root.locator(".data_info__item_song a").get_attribute(
            "title"
        )
        # 提取封面
        cover = await song_info_root.locator(".data__cover .data__photo").get_attribute(
            "src"
        )
        if cover and cover.startswith("//"):
            cover = f"https:{cover}"

        detail_root = page.locator(".detail_layout")
        loading = detail_root.locator(".mod_loading")
        await loading.wait_for()
        await loading.wait_for(state="detached")

        lyrics = await self.__extract_lyrics(page=page)
        comments = await self.__extract_comment_groups(page=page)
        return Song(
            title=title,
            artists=artists,
            cover=cover,
            album=album,
            lyrics=lyrics,
            comments=comments,
        )

    async def __extract_lyrics(self, page: Page) -> list[str]:
        root = page.locator(".mod_lyric")
        await root.wait_for()
        # TODO 展开歌词
        # 定位歌词内容容器
        lyrics_container = root.locator("#lrc_content")
        await lyrics_container.wait_for()
        # 提取所有歌词行
        lyrics_elements = lyrics_container.locator("p span")
        lyrics_count = await lyrics_elements.count()
        return [await lyrics_elements.nth(i).inner_text() for i in range(lyrics_count)]

    async def __extract_comment_groups(self, page: Page) -> list[CommentGroup]:
        root = page.locator("#comment_box.mod_comment")
        await root.wait_for()

        comment_groups = root.locator(".mod_hot_comment")
        hot_comment_group = await self.__extract_comment_group(comment_groups.first)

        return [hot_comment_group]

    async def __extract_comment_group(self, locator: Locator) -> CommentGroup:
        group_name = await locator.locator(".comment_type__title").inner_text()

        comments = []
        comment_items = locator.locator("> ul.comment__list > li")
        for i in range(await comment_items.count()):
            item = comment_items.nth(i)

            comment_info_element = item.locator("> div").first
            # 提取用户名
            username = await comment_info_element.locator(
                ".comment__title > a"
            ).inner_text()
            # 提取日期和IP属地
            date_and_location = await comment_info_element.locator(
                ".comment__date"
            ).inner_text()
            # 提取评论内容
            content = await comment_info_element.locator(
                ".comment__text span"
            ).inner_text()
            # 提取点赞数
            likes_text = await comment_info_element.locator(
                ".comment__zan"
            ).inner_text()
            likes = int(likes_text) if likes_text.strip().isdigit() else 0

            reply_count = 0
            replies = []
            if await has_element(item, ".comment__reply"):
                comment_reply_element = item.locator(".comment__reply")
                # 查看 x 条回复 btn
                expand_btn = comment_reply_element.locator(".comment__reply_hd a")
                # 提取评论回复数
                expand_btn_text = await expand_btn.inner_text()
                reply_count_text = (
                    expand_btn_text.replace("查看", "").replace("条回复", "").strip()
                    if "查看" in expand_btn_text
                    else "0"
                )
                reply_count = int(reply_count_text) if reply_count_text.isdigit() else 0
                # 提取评论回复列表
                reply_list = comment_reply_element.locator("ul.comment__list")
                # 判断是否展开
                if await reply_list.count() > 1:
                    replies = await self.__extract_expanded_comment_replies(reply_list)
                else:
                    replies = await self.__extract_unexpanded_comment_replies(
                        reply_list
                    )
            comments.append(
                Comment(
                    username=username,
                    date_and_location=date_and_location,
                    content=content,
                    likes=likes,
                    reply_count=reply_count,
                    replies=replies,
                )
            )
        return CommentGroup(
            name=group_name,
            comments=comments,
        )

    async def __extract_unexpanded_comment_replies(
        self, locator: Locator
    ) -> list[CommentReply]:
        """
        提取未展开的评论回复列表

        Args:
            locator (Locator): .comment__reply ul.comment__list

        Returns:
            list[CommentReply]: 评论回复列表
        """

        replies = []
        reply_items = locator.locator("> li")
        for i in range(await reply_items.count()):
            item = reply_items.nth(i)
            # 提取用户名
            username = await item.locator(".comment__text span a").inner_text()
            # 提取评论内容
            content = await item.locator(".comment__text span span").inner_text()
            # 提取点赞数
            likes_text = await item.locator(".comment__zan").inner_text()
            likes = int(likes_text) if likes_text.strip().isdigit() else 0
            # 创建 CommentReply 对象
            reply = CommentReply(
                username=username,
                content=content,
                likes=likes,
            )
            replies.append(reply)
        return replies

    async def __extract_expanded_comment_replies(
        self, locator: Locator
    ) -> list[CommentReply]:
        """
        提取展开的评论回复列表

        Args:
            locator (Locator): .comment__reply ul.comment__list

        Returns:
            list[CommentReply]: 评论回复列表
        """
        replies = []
        reply_items = locator.locator("> li")
        for i in range(await reply_items.count()):
            item = reply_items.nth(i)
            # 提取用户名
            username = await item.locator(".comment__title > a").inner_text()
            # 提取评论内容
            content = await item.locator(".comment__text span").inner_text()
            # 提取点赞数
            likes_text = await item.locator(".comment__zan").inner_text()
            likes = int(likes_text) if likes_text.strip().isdigit() else 0

            # 创建 CommentReply 对象
            reply = CommentReply(
                username=username,
                content=content,
                likes=likes,
            )
            replies.append(reply)
        return replies


async def has_element(locator: Locator, selector: str) -> bool:
    return await locator.locator(selector).count() > 0
