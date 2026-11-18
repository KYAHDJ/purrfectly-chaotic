"""Detailed analytics for the newest video: overview, engagement (retention), reach. Saves text+screenshots to data/raw/<date>/vid_*"""
import sys, re, datetime, pathlib; sys.path.insert(0, "data/yt")
from yt_lib import *
out = pathlib.Path("data/raw") / datetime.date.today().isoformat(); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    ctx, pg = open_studio(p)
    cid = re.search(r"/channel/(UC[\w-]+)", pg.url).group(1)
    pg.goto(f"https://studio.youtube.com/channel/{cid}/videos/short", wait_until="domcontentloaded"); pg.wait_for_timeout(6000)
    href = pg.locator("a[href*='/video/']").first.get_attribute("href"); vid = re.search(r"/video/([\w-]{11})", href).group(1); print("video", vid)
    for tab in ("overview", "engagement", "reach", "audience"):
        pg.goto(f"https://studio.youtube.com/video/{vid}/analytics/tab-{tab}/period-default", wait_until="domcontentloaded"); pg.wait_for_timeout(8000)
        (out / f"vid_{tab}.txt").write_text(pg.inner_text("body"), encoding="utf-8"); pg.screenshot(path=str(out / f"vid_{tab}.png"))
        print("saved", tab)
    ctx.close()
