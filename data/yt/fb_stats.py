import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1400, "height": 900})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://business.facebook.com/latest/content_posts", wait_until="domcontentloaded"); pg.wait_for_timeout(10000)
    pg.screenshot(path="data/clipsheets/fb_stats.png")
    print(pg.inner_text("body")[:2500].encode("ascii","ignore").decode())
    ctx.close()
