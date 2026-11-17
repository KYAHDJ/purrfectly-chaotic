import sys; sys.path.insert(0, "data/yt")
from yt_lib import *
with sync_playwright() as p:
    ctx, pg = open_studio(p)
    pg.wait_for_timeout(2000); pg.get_by_text("Content", exact=True).first.click(); pg.wait_for_timeout(5000)
    pg.get_by_text("View all", exact=True).first.click(); pg.wait_for_timeout(5000)
    pg.get_by_text("Private", exact=True).first.click(); pg.wait_for_timeout(2500)
    pg.screenshot(path="data/clipsheets/sch_a.png")
    sch = pg.get_by_text("Schedule", exact=True).first
    sch.scroll_into_view_if_needed(); sch.click(); pg.wait_for_timeout(1500)
    pg.screenshot(path="data/clipsheets/sch_b.png")
    ctx.close()
