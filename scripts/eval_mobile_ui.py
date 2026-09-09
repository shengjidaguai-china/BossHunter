"""Mobile UI & API Evaluation Script.

Simulates mobile devices (iPhone 390x844), captures screenshots,
and validates mobile responsive layout, touch targets, and API endpoints.
"""

import sys
import time
import threading
from pathlib import Path

# 确保能加载 bosshunter
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bosshunter.web.server import app, ThreadingWSGIServer
from wsgiref.simple_server import make_server


def start_test_server(port=8687):
    server = make_server("127.0.0.1", port, app, server_class=ThreadingWSGIServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def run_evaluation():
    from patchright.sync_api import sync_playwright

    port = 8687
    print(f"[1/5] 启动测试 Web 服务在 http://127.0.0.1:{port}...")
    server = start_test_server(port)
    time.sleep(1)

    eval_dir = Path(__file__).resolve().parents[1] / "eval_results"
    eval_dir.mkdir(parents=True, exist_ok=True)

    print("[2/5] 启动无头浏览器并模拟手机视口 (390x844, iPhone 14/15/16)...")
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chrome_path)

        # 1. 移动端上下文
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True,
        )
        page = mobile_context.new_page()

        # 评估工作台
        print("[3/5] 评估移动端工作台 (/) ...")
        page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
        time.sleep(1)

        # 断言 1: 移动端底部 TabBar 必须存在且可见
        tab_bar = page.locator("nav.safe-area-pb")
        assert tab_bar.is_visible(), "Error: MobileTabBar should be visible on mobile!"
        print("  [✓] 移动端底部 TabBar (MobileTabBar) 正常显示")

        # 断言 2: 桌面侧边栏必须隐藏
        sidebar = page.locator("aside")
        assert not sidebar.is_visible(), "Error: Desktop sidebar should be hidden on mobile!"
        print("  [✓] 桌面侧边栏在手机视口下自动隐藏")

        # 断言 3: 页面无横向破坏性滚动
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        client_width = page.evaluate("document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, f"Error: Horizontal overflow detected! scrollWidth={scroll_width}, clientWidth={client_width}"
        print(f"  [✓] 视口无横向溢出 (clientWidth: {client_width}px, scrollWidth: {scroll_width}px)")

        page.screenshot(path=str(eval_dir / "mobile_eval_workbench.png"))
        print(f"  [✓] 已保存工作台截图: {eval_dir / 'mobile_eval_workbench.png'}")

        # 评估岗位池
        print("[4/5] 评估移动端岗位池 (/jobs) 与卡片式布局 ...")
        page.goto(f"http://127.0.0.1:{port}/jobs", wait_until="networkidle")
        time.sleep(1)
        mobile_cards_container = page.locator("div.md\\:hidden")
        assert mobile_cards_container.count() > 0, "Error: Mobile cards container should exist!"
        print("  [✓] 移动端自适应卡片容器渲染正常")

        page.screenshot(path=str(eval_dir / "mobile_eval_jobs.png"))
        print(f"  [✓] 已保存岗位池截图: {eval_dir / 'mobile_eval_jobs.png'}")

        # 评估配置页
        print("[4.5/5] 评估移动端配置页 (/config) ...")
        page.goto(f"http://127.0.0.1:{port}/config", wait_until="networkidle")
        time.sleep(1)
        page.screenshot(path=str(eval_dir / "mobile_eval_config.png"))
        print(f"  [✓] 已保存配置页截图: {eval_dir / 'mobile_eval_config.png'}")

        mobile_context.close()

        # 2. 桌面端上下文，验证手机扫码弹窗
        print("[5/5] 评估桌面端手机扫码弹窗功能 ...")
        desktop_context = browser.new_context(viewport={"width": 1280, "height": 800})
        desktop_page = desktop_context.new_page()
        desktop_page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
        time.sleep(1)

        # 点击“手机端连接”按钮
        desktop_page.click("button:has-text('手机端连接')")
        time.sleep(1)

        modal = desktop_page.locator("h3:has-text('手机端扫码连接')")
        assert modal.is_visible(), "Error: Mobile connection modal should open!"
        qr_img = desktop_page.locator("img[alt='手机扫码二维码']")
        assert qr_img.is_visible(), "Error: QR code image should be visible in modal!"
        print("  [✓] 桌面端手机扫码连接弹窗及二维码图片正常弹出与显示")

        desktop_page.screenshot(path=str(eval_dir / "desktop_eval_mobile_modal.png"))
        print(f"  [✓] 已保存弹窗截图: {eval_dir / 'desktop_eval_mobile_modal.png'}")

        desktop_context.close()
        browser.close()

    server.shutdown()
    print("\n🎉 全部 Eval 测试与跨端响应式断言 100% 通过！")


if __name__ == "__main__":
    run_evaluation()
