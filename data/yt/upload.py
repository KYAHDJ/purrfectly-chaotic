"""Upload a video to YouTube Studio as PRIVATE (never publishes). usage: python data/yt/upload.py <meta.json>"""
import sys, json, pathlib, re; sys.path.insert(0, "data/yt")
from yt_lib import *
meta = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
vid = str(pathlib.Path(meta["video"]).resolve())
def shot(pg, n): pg.screenshot(path=f"data/clipsheets/up_{n}.png")
with sync_playwright() as p:
    ctx, pg = open_studio(p)
    try:
        pg.wait_for_timeout(3000)
        pg.get_by_role("button", name="Upload videos").first.click(); pg.wait_for_timeout(2500)
        with pg.expect_file_chooser(timeout=20000) as fc:
            pg.get_by_role("button", name="Select files").first.click()
        fc.value.set_files(vid); pg.wait_for_timeout(9000)
        tb = pg.locator("#title-textarea #textbox").first
        tb.click(); pg.keyboard.press("Control+A"); pg.keyboard.type(meta["title"], delay=8); pg.wait_for_timeout(800)
        pg.mouse.click(700, 140); pg.wait_for_timeout(300)      # close hashtag suggestions
        ds = pg.locator("#description-textarea #textbox").first
        ds.click(); pg.keyboard.press("Control+A"); pg.keyboard.type(meta["description"], delay=5); pg.wait_for_timeout(800)
        pg.get_by_text("Thumbnail", exact=True).first.click(); pg.wait_for_timeout(500)
        shot(pg, 2)
        kids = pg.get_by_role("radio", name=re.compile("not made for kids", re.I)).first
        kids.scroll_into_view_if_needed(); kids.click(); pg.wait_for_timeout(600)
        sm = pg.locator("#toggle-button, ytcp-button:has-text('Show more'), button:has-text('Show more')").first
        sm.scroll_into_view_if_needed(); sm.click(); pg.wait_for_timeout(1500)
        shot(pg, 3)
        tg = pg.locator("ytcp-form-input-container#tags-container input, #tags-container input").first
        tg.scroll_into_view_if_needed(); tg.click(); pg.keyboard.type(",".join(meta["tags"]) + ",", delay=4); pg.wait_for_timeout(800)
        shot(pg, 4)
        _l = pg.get_by_text("Video language", exact=True).first; _l.scroll_into_view_if_needed(); pg.wait_for_timeout(600); lang = _l.bounding_box()
        pg.mouse.click(lang["x"] + 100, lang["y"] + 20); pg.wait_for_timeout(1200)
        shot(pg, 10)
        print([t for t in pg.locator("tp-yt-paper-item, [role=option]").all_inner_texts()][:8])
        opt = pg.locator("tp-yt-paper-item:has-text('English (United States)')").first
        opt.scroll_into_view_if_needed(); pg.wait_for_timeout(400); opt.click(force=True); pg.wait_for_timeout(1000)
        vl = pg.get_by_text("Video location", exact=True).first; vl.scroll_into_view_if_needed(); pg.wait_for_timeout(500)
        bb = vl.bounding_box(); pg.mouse.click(bb["x"] + 100, bb["y"] + 22); pg.keyboard.type("United States", delay=40); pg.wait_for_timeout(2500)
        shot(pg, 5)
        pg.mouse.click(655, 335); pg.wait_for_timeout(1200)
        shot(pg, 6)
        pg.get_by_text("Language and captions certification", exact=True).first.click(); pg.wait_for_timeout(800)
        for _ in range(80):
            if not pg.get_by_text("Uploading", exact=False).first.is_visible(): break
            pg.wait_for_timeout(3000)
        for i in range(3):
            pg.locator("#next-button").first.click(force=True); pg.wait_for_timeout(4000)
        shot(pg, 7)
        pg.get_by_role("radio", name=re.compile("^Private", re.I)).first.click(); pg.wait_for_timeout(800)
        for _ in range(60):
            if not pg.get_by_text("Uploading", exact=False).first.is_visible(): break
            pg.wait_for_timeout(3000)
        shot(pg, 8)
        pg.get_by_role("button", name="Save").first.click(); pg.wait_for_timeout(4000)
        shot(pg, 9)
        print("saved as private")
    finally:
        pg.wait_for_timeout(1500)
        ctx.close()
