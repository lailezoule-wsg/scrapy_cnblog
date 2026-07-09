"""
基于 Playwright 的登录与 Cookie 生成器（同步版本）
专门适配博客园（https://account.cnblogs.com/signin）
适用于 Scrapy 2.16 生产环境
"""
import logging
from typing import Dict, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class LoginGenerator:
    """
    使用 Playwright 模拟浏览器登录博客园，获取 Cookie
    选择器基于稳定的 formcontrolname、类名和文本，避免动态 ID
    """

    def __init__(
        self,
        login_url: str = "https://account.cnblogs.com/signin",
        username: str = "",
        password: str = "",
        username_selector: str = 'input[formcontrolname="username"]',  # 稳定
        password_selector: str = 'input[formcontrolname="password"]',  # 稳定
        remember_selector: str = 'mat-checkbox[formcontrolname="isRemember"]',  # 稳定
        login_button_selector: str = 'button.action-button:has-text("登录")',   # 类名+文本
        headless: bool = True,
        timeout: int = 30000,          # 毫秒
        wait_after_click: int = 3000,   # 登录后等待
        success_selector: Optional[str] = None,  # 登录成功后的元素，可设为 None 依赖 URL
        browser_type: str = "chromium",
    ):
        self.login_url = login_url
        self.username = username
        self.password = password
        self.username_selector = username_selector
        self.password_selector = password_selector
        self.remember_selector = remember_selector
        self.login_button_selector = login_button_selector
        self.headless = headless
        self.timeout = timeout
        self.wait_after_click = wait_after_click
        self.success_selector = success_selector
        self.browser_type = browser_type

    def get_cookie(self) -> Optional[Dict[str, str]]:
        """执行登录并返回 Cookie 字典"""
        browser = None
        page = None
        try:
            with sync_playwright() as p:
                browser_launcher = getattr(p, self.browser_type)
                browser = browser_launcher.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',  # 移除 webdriver 标识
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials',
                        '--disable-web-security',
                        '--disable-features=BlockInsecurePrivateNetworkRequests',
                        '--disable-features=OutOfBlinkCors',
                    ]
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    permissions=["geolocation"],
                    device_scale_factor=1,
                    has_touch=False,
                    is_mobile=False,
                    # 关键：隐藏自动化特征
                    extra_http_headers={
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
                    }
                )

                
                page = context.new_page()

                # 注入 JavaScript 覆盖 webdriver 属性（可选，Playwright 新版本已自动处理）
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                # 访问登录页
                logger.info(f"Navigating to {self.login_url}")
                page.goto(self.login_url, timeout=self.timeout)

                # ----- 检测是否存在 reCAPTCHA（仅提示，暂不处理） -----
                if page.locator('.grecaptcha-badge').count() > 0:
                    logger.warning("检测到 reCAPTCHA，可能需要手动处理或集成打码服务。继续尝试登录...")

                # ----- 填写用户名 -----
                username_input = page.locator(self.username_selector)
                username_input.wait_for(state="visible", timeout=self.timeout)
                username_input.click()
                username_input.fill(self.username)

                # ----- 填写密码 -----
                password_input = page.locator(self.password_selector)
                password_input.wait_for(state="visible", timeout=self.timeout)
                password_input.click()
                password_input.fill(self.password)

                # ----- 勾选“记住我”（如果未勾选） -----
                remember_checkbox = page.locator(self.remember_selector)
                if remember_checkbox.count():
                    # 检查是否已勾选（通过 class 是否包含 mat-checkbox-checked）
                    class_list = remember_checkbox.get_attribute('class') or ''
                    if 'mat-checkbox-checked' in class_list:
                        logger.debug("'记住我' 已勾选，无需操作")
                    else:
                        remember_checkbox.click()
                        logger.debug("已勾选 '记住我'")
                else:
                    logger.warning("未找到 '记住我' 复选框，跳过")

                # ----- 点击登录按钮 -----
                login_button = page.locator(self.login_button_selector)
                login_button.wait_for(state="visible", timeout=self.timeout)
                login_button.click()

                # ----- 等待登录成功 -----
                if self.success_selector:
                    page.locator(self.success_selector).wait_for(state="visible", timeout=self.timeout)
                else:
                    # 等待 URL 从 /signin 变为其他（如 /dashboard 或 /）
                    page.wait_for_url(lambda url: "signin" not in url.lower(), timeout=self.timeout)

                # 额外等待确保 Cookie 完全写入
                page.wait_for_timeout(self.wait_after_click)

                # ----- 获取 Cookies -----
                cookies = context.cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                logger.info(f"Successfully logged in as {self.username}, got {len(cookie_dict)} cookies")
                return cookie_dict

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during login for {self.username}: {e}")
            # 保存截图便于调试
            if page and 'page' in locals():
                page.screenshot(path=f"error_{self.username}.png")
            return None
        except Exception as e:
            logger.error(f"Login failed for {self.username}: {e}", exc_info=True)
            return None
 

    def get_cookies_with_retry(self, max_retries: int = 3) -> Optional[Dict[str, str]]:
        """带重试的登录"""
        for attempt in range(1, max_retries + 1):
            logger.info(f"Login attempt {attempt}/{max_retries} for {self.username}")
            cookie = self.get_cookie()
            if cookie:
                return cookie
            logger.warning(f"Attempt {attempt} failed, retrying...")
        logger.error(f"All {max_retries} login attempts failed for {self.username}")
        return None


# ============ 使用示例 ============
if __name__ == "__main__":
    import sys
    import os
    import json
    import time
    import random

    logging.basicConfig(level=logging.INFO)
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


    user_path = os.path.dirname(os.path.abspath(__file__)) + '/user_info.js'

    userInfoStr = None
    with open(user_path,'r',encoding="utf-8") as f:
        userInfoStr = f.read()

    user_info_list = json.loads(userInfoStr)

    delay_time = [2,3,4,2,3]

    for user_info in user_info_list:
        # print(user_info["username"],user_info["password"])
        # 实例化登录生成器（替换为真实账号）
        generator = LoginGenerator(
            username=user_info["username"],
            password=user_info["password"],
            headless=False,          # 调试时关闭 headless 以便观察
            success_selector="#user_icon"
        )

        cookie = generator.get_cookies_with_retry(max_retries=2)

        from cnblog.scripts.cookie_manager import CookieManager
        cookieManager = CookieManager()
        if cookie:
            cookieManager.add_cookie('cnblog',"lailezoule",cookie)
            print("Got cookie:", cookie)
        else:
            print("Login failed")
        
        time.sleep(random.choice(delay_time))