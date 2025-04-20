from mcp_server_lib import BaseBrowser
from playwright.async_api import Page, Playwright


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

    async def is_user_logged_in(self, page: Page) -> bool:
        login_btn = page.locator(".mod_header .top_login__link")
        await login_btn.wait_for(state="visible")
        login_btn_children_count = await login_btn.locator("*").count()
        return login_btn_children_count > 0

    async def login(self) -> None:
        page = await self._context.new_page()
        await page.goto(self.BASE_URL)

        login_btn = page.locator(".mod_header .top_login__link")
        await login_btn.wait_for(state="visible")
        if await self.is_user_logged_in(page=page):
            return
        await login_btn.click()

        login_container = page.locator("#login.login")
        await login_container.wait_for(state="visible")

        login_list = login_container.locator(".qlogin_list")
        # 等待登录列表加载
        if await self.wait_for_content_stabilization(
            page=page,
            locator=login_list,
            timeout=200,
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

        if not await self.is_user_logged_in(page=page):
            raise Exception("登录失败")
