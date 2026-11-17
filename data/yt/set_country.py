import sys; sys.path.insert(0, "data/yt")
from yt_lib import *
with sync_playwright() as p:
    ctx, pg = open_studio(p)
    pg.get_by_text("Settings", exact=True).first.click(); pg.wait_for_timeout(2000)
    pg.get_by_text("Channel", exact=True).first.click(); pg.wait_for_timeout(2000)
    box = pg.get_by_text("Country of residence").first.bounding_box()
    pg.mouse.click(box["x"] + 100, box["y"] + 20); pg.wait_for_timeout(1200)
    opt = pg.get_by_text("United States", exact=True).first
    opt.scroll_into_view_if_needed(); pg.wait_for_timeout(500); opt.click(); pg.wait_for_timeout(800)
    kb = pg.get_by_text("Keywords", exact=True).first.bounding_box()
    pg.mouse.click(kb["x"] + 150, kb["y"] + 30); pg.wait_for_timeout(400)
    pg.keyboard.type("cat shorts, funny cats, cat videos, cat zoomies, cute cats, funny cat shorts", delay=15); pg.wait_for_timeout(600)
    pg.screenshot(path="data/clipsheets/yt_a.png")
    pg.get_by_role("button", name="Save").first.click(); pg.wait_for_timeout(3500)
    pg.screenshot(path="data/clipsheets/yt_b.png")
    ctx.close()
