import sys; sys.path.insert(0, "data/yt")
from yt_lib import *
DELETE = len(sys.argv) > 1 and sys.argv[1] == "delete"
with sync_playwright() as p:
    ctx, pg = open_studio(p)
    pg.wait_for_timeout(2000); pg.get_by_text("Content", exact=True).first.click(); pg.wait_for_timeout(5000)
    pg.get_by_text("View all", exact=True).first.click(); pg.wait_for_timeout(6000)
    rows = pg.locator("ytcp-video-row")
    n = rows.count(); picked = 0
    for i in range(n):
        r = rows.nth(i); t = r.inner_text()
        if "Draft" in t and "Private" not in t:
            r.locator("ytcp-checkbox-lit, #checkbox-container").first.click(); picked += 1
    print("rows", n, "drafts selected", picked)
    pg.wait_for_timeout(1000); pg.screenshot(path="data/clipsheets/drafts_b.png")
    if DELETE and picked == 7 and n == 8:
        pg.get_by_text("More actions", exact=True).first.click(); pg.wait_for_timeout(1000)
        pg.get_by_text("Delete forever", exact=True).first.click(); pg.wait_for_timeout(1500)
        pg.screenshot(path="data/clipsheets/drafts_c.png")
        print(pg.locator("ytcp-confirmation-dialog").first.inner_text())
        pg.locator("ytcp-confirmation-dialog ytcp-checkbox-lit, ytcp-confirmation-dialog #checkbox-container").first.click(); pg.wait_for_timeout(600)
        pg.locator("ytcp-confirmation-dialog #confirm-button").first.click(); pg.wait_for_timeout(4000)
        pg.screenshot(path="data/clipsheets/drafts_d.png")
    ctx.close()
