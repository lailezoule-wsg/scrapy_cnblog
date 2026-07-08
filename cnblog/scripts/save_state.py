import asyncio
import os
from playwright.async_api import async_playwright

# 创建或指定一个目录用于存储用户数据（持久化）
USER_DATA_DIR = os.path.expanduser("~/playwright_chrome_user_data")  # 可自定义路径

async def save_state():
    async with async_playwright() as p:
        # 使用用户数据目录启动浏览器，这将保持登录状态和浏览器配置
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        # 注意：launch_persistent_context 直接返回 context 对象
        context = browser
        page = context.pages[0] if context.pages else await context.new_page()

        # 打开博客园登录页
        await page.goto("https://account.cnblogs.com/signin")
        print("🌐 浏览器已打开，请手动完成登录（包括验证码）...")
        input("✅ 登录成功后，按 Enter 键继续保存状态...")

        # 保存状态到文件（仍然可以使用 storage_state）
        await context.storage_state(path="state.json")
        await context.close()
        print("🎉 登录状态已保存到 state.json")

if __name__ == "__main__":
    asyncio.run(save_state())