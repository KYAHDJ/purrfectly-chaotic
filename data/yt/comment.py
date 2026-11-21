"""Post a top-level comment as the channel on a video and pin it. usage: python data/yt/comment.py <videoId> "<comment text>" [confirm]"""
import sys, re
from playwright.sync_api import sync_playwright
vid, text = sys.argv[1], sys.argv[2]; CONFIRM = len(sys.argv) > 3 and sys.argv[3] == "confirm"
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled"], viewport={"width": 1300, "height": 900})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        pg.goto(f"https://www.youtube.com/watch?v={vid}", wait_until="domcontentloaded"); pg.wait_for_timeout(6000)
        pg.mouse.wheel(0, 700); pg.wait_for_timeout(3500)
        box = pg.locator("#placeholder-area, #simplebox-placeholder").first
        box.scroll_into_view_if_needed(); box.click(); pg.wait_for_timeout(1500)
        pg.keyboard.type(text, delay=15); pg.wait_for_timeout(1000)
        pg.screenshot(path="data/clipsheets/cm_1.png")
        if CONFIRM:
            pg.locator("#submit-button button, ytd-button-renderer#submit-button button").first.click(); pg.wait_for_timeout(4000)
            pg.screenshot(path="data/clipsheets/cm_2.png")
            print("posted")
            if len(sys.argv) < 5 or sys.argv[4] != "pin": return_ = True
            else: return_ = False
            if return_: raise SystemExit(0)
            th = pg.locator("ytd-comment-thread-renderer").first
            th.scroll_into_view_if_needed(); th.hover(); pg.wait_for_timeout(800)
            th.locator("#action-menu button, ytd-menu-renderer button").first.click(); pg.wait_for_timeout(1200)
            pg.get_by_text("Pin", exact=True).first.click(); pg.wait_for_timeout(1500)
            pg.screenshot(path="data/clipsheets/cm_3.png")
            pg.locator("tp-yt-paper-dialog button:has-text('Pin'), yt-confirm-dialog-renderer button:has-text('Pin'), #confirm-button button").last.click(); pg.wait_for_timeout(3000)
            pg.screenshot(path="data/clipsheets/cm_4.png")
            print("pinned attempt done")
    finally:
        ctx.close()
