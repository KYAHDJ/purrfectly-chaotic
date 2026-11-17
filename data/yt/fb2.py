import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1400, "height": 900})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://business.facebook.com/latest/home", wait_until="domcontentloaded"); pg.wait_for_timeout(8000)
    try: pg.get_by_text("Done", exact=True).first.click(timeout=3000)
    except Exception: pass
    pg.get_by_text("Create reel", exact=True).first.click(); pg.wait_for_timeout(6000)
    pg.wait_for_timeout(5000)
    pgs = ctx.pages; print([x.url for x in pgs])
    last = pgs[-1]; last.screenshot(path="data/clipsheets/fb_b.png")
    print(last.inner_text("body")[:900].encode("ascii","ignore").decode())
    ctx.close()
