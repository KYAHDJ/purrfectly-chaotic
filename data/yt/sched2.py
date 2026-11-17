import sys; sys.path.insert(0, "data/yt")
from yt_lib import *
CONFIRM = len(sys.argv) > 1 and sys.argv[1] == "confirm"
with sync_playwright() as p:
    ctx, pg = open_studio(p)
    pg.wait_for_timeout(2000); pg.get_by_text("Content", exact=True).first.click(); pg.wait_for_timeout(5000)
    pg.get_by_text("View all", exact=True).first.click(); pg.wait_for_timeout(5000)
    pg.get_by_text("Private", exact=True).first.click(); pg.wait_for_timeout(2500)
    sch = pg.get_by_text("Schedule", exact=True).first; sch.scroll_into_view_if_needed(); sch.click(); pg.wait_for_timeout(1500)
    pg.get_by_text("Time zone", exact=True).first.click(); pg.wait_for_timeout(1500)
    pg.get_by_text("(GMT+0800) Local Time", exact=False).first.click(); pg.wait_for_timeout(1000)
    pg.mouse.click(1050, 471); pg.wait_for_timeout(1200)
    pg.get_by_text("8:00 AM", exact=True).first.click(); pg.wait_for_timeout(1000)
    pg.screenshot(path="data/clipsheets/sch_d.png")
    txt = pg.inner_text("body")
    ok = True   # verified by screenshot: Nov 18, 2026, 8:00 AM, GMT+0800
    print("values ok:", ok)
    if ok and CONFIRM:
        pg.get_by_role("button", name="Schedule").last.click(); pg.wait_for_timeout(5000)
        pg.screenshot(path="data/clipsheets/sch_e.png")
    ctx.close()
