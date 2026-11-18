"""Create a Facebook Reel via Meta Business Suite. usage: python data/yt/fb_reel.py <meta.json> [confirm]  (confirm = press the final Schedule button)"""
import sys, json, pathlib, re
from playwright.sync_api import sync_playwright
meta = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); CONFIRM = len(sys.argv) > 2 and sys.argv[2] == "confirm"
DAY = int(sys.argv[3]) if len(sys.argv) > 3 else 19
vid = str(pathlib.Path(meta["video"]).resolve())
def shot(pg, n): pg.screenshot(path=f"data/clipsheets/fb_{n}.png")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled"], viewport={"width": 1400, "height": 900})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        pg.goto("https://business.facebook.com/latest/reels_composer", wait_until="domcontentloaded"); pg.wait_for_timeout(22000)
        with pg.expect_file_chooser(timeout=20000) as fc:
            pg.get_by_text("Add Video", exact=True).first.click()
        fc.value.set_files(vid); pg.wait_for_timeout(15000)
        shot(pg, "d1")
        ed = pg.locator('div[role="textbox"][contenteditable="true"], div[contenteditable="true"]').first
        ed.scroll_into_view_if_needed(); ed.click(force=True); pg.keyboard.type(meta["fb_caption"], delay=8); pg.wait_for_timeout(1500)
        shot(pg, "d2")
        for _ in range(60):
            if not re.search(r"\d{1,2}%", pg.inner_text("body")): break
            pg.wait_for_timeout(3000)
        nxt = pg.get_by_role("button", name="Next").last
        nxt.click(); pg.wait_for_timeout(5000); shot(pg, "d3")
        nxt = pg.get_by_role("button", name="Next").last
        nxt.click(); pg.wait_for_timeout(5000); shot(pg, "d4")
        pg.get_by_text("Schedule", exact=True).first.click(); pg.wait_for_timeout(2500)
        pg.mouse.click(250, 302); pg.wait_for_timeout(1500); shot(pg, "d5a")
        pg.get_by_text(str(DAY), exact=True).locator("visible=true").first.click(); pg.wait_for_timeout(1000)
        pg.mouse.click(498, 302); pg.wait_for_timeout(500); pg.keyboard.type("08"); pg.wait_for_timeout(300)
        pg.mouse.click(525, 302); pg.wait_for_timeout(300); pg.keyboard.type("00"); pg.wait_for_timeout(300)
        pg.mouse.click(548, 302); pg.wait_for_timeout(300); pg.keyboard.type("A"); pg.wait_for_timeout(800)
        shot(pg, "d5")
        if CONFIRM:
            pg.mouse.click(1282, 842); pg.wait_for_timeout(9000); shot(pg, "d6")
            print("scheduled; url:", pg.url)
    finally:
        ctx.close()
