from mcp_server_lib import BaseBrowser
from playwright.async_api import Locator, Page, Playwright
from pydantic import BaseModel


class SearchSongsResult(BaseModel):
    title: str  # 歌曲
    artists: list[str]  # 歌手
    album: str | None  # 专辑
    duration: str  # 时长
    link: str  # 链接


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
        try:
            page = await self.new_page()
            await page.goto(QQMusic.BASE_URL)
            if await self.__is_user_logged_in(page=page):
                return True
        except Exception as e:
            self.logger.error(f"Error checking login status: {e}")
        finally:
            if page:
                await page.close()
        return False

    async def __is_user_logged_in(self, page: Page) -> bool:
        login_btn = page.locator(".mod_header .top_login__link")
        await login_btn.wait_for(state="visible")
        await self.wait_for_stabilization(
            page=page,
            locator=login_btn,
            check_interval_ms=500,
            threshold=2,
        )
        profile_herf = await login_btn.get_attribute("href")
        return profile_herf is not None

    async def login(self, page: Page) -> None:
        await page.goto(self.BASE_URL)

        login_btn = page.locator(".mod_header .top_login__link")
        await login_btn.wait_for(state="visible")
        if await self.__is_user_logged_in(page=page):
            self.logger.info("Already logged in")
            return
        await login_btn.click()

        login_container = page.locator("#login.login")
        await login_container.wait_for(state="visible")

        login_list = login_container.locator(".qlogin_list")
        # 等待登录列表加载
        if await self.wait_for_stabilization(
            page=page,
            locator=login_list,
            check_interval_ms=200,
        ):
            face_count = await login_list.locator(".face").count()
            if face_count == 0:
                await page.wait_for_timeout(60000)  # 等待用户扫码
            else:
                await login_list.locator(".face").first.click()  # 点击头像登录
        else:
            raise Exception("登录页面加载失败")

        # 等待登录框消失
        await login_container.wait_for(state="visible")

        if not await self.__is_user_logged_in(page=page):
            raise Exception("登录失败")

    async def search_songs(self, page: Page, keyword: str) -> list[SearchSongsResult]:
        await page.goto(
            f"{self.BASE_URL}/n/ryqq/search?w={keyword}&t=song&remoteplace=txt.yqq.top"
        )

        # 等待搜索结果加载
        song_list = page.locator(".result .songlist__list")
        await song_list.wait_for(state="visible")

        await self.wait_for_stabilization(page=page, locator=song_list)

        song_list_items = song_list.locator("> li")
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
            result = SearchSongsResult(
                title=name,
                artists=artists,
                album=album,
                duration=duration,
                link=link,
            )
            results.append(result)
        return results


async def has_element(locator: Locator, selector: str) -> bool:
    return await locator.locator(selector).count() > 0
