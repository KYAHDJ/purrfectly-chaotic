"""Detailed analytics for the newest video: overview, engagement (retention), reach. Saves text+screenshots to data/raw/<date>/vid_*"""
import sys, re, datetime, pathlib; sys.path.insert(0, "data/yt")
from yt_lib import *
out = pathlib.Path("data/raw") / datetime.date.today().isoformat(); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    ctx, pg = open_studio(p)
    cid = re.search(r"/channel/(UC[\w-]+)", pg.url).group(1)
    pg.goto(f"https://studio.youtube.com/channel/{cid}/videos/short", wait_until="domcontentloaded"); pg.wait_for_timeout(6000)
    ids = []
    for a in pg.locator("a[href*='/video/']").all():
        m = re.search(r"/video/([\w-]{11})", a.get_attribute("href") or "")
        if m and m.group(1) not in ids: ids.append(m.group(1))
    print("videos", ids)
    for n, vid in enumerate(ids[:3]):
        pg.goto(f"https://studio.youtube.com/video/{vid}/analytics/tab-engagement/period-default", wait_until="domcontentloaded"); pg.wait_for_timeout(8000)
        (out / f"vid{n}_{vid}.txt").write_text(pg.inner_text("body"), encoding="utf-8"); pg.screenshot(path=str(out / f"vid{n}_{vid}.png"))
        print("saved", n, vid)
    ctx.close()
