import sys; sys.path.insert(0, "data/yt")
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1400, "height": 900})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://business.facebook.com/latest/home", wait_until="domcontentloaded"); pg.wait_for_timeout(9000)
    print(pg.url); print(pg.title())
    pg.screenshot(path="data/clipsheets/fb_a.png")
    print(pg.inner_text("body")[:700].encode("ascii","ignore").decode())
    ctx.close()
