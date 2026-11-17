import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1400, "height": 900})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://business.facebook.com/latest/reels_composer", wait_until="domcontentloaded"); pg.wait_for_timeout(25000)
    print(pg.url)
    pg.screenshot(path="data/clipsheets/fb_c.png")
    print(pg.inner_text("body")[:900].encode("ascii","ignore").decode())
    ctx.close()
