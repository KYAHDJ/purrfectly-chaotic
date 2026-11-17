"""Step 1: open Studio with the saved login, grab channel stats, save to data/."""
import json, re, datetime, pathlib
from playwright.sync_api import sync_playwright

today = datetime.date.today().isoformat()
out = pathlib.Path("data") / "raw" / today
out.mkdir(parents=True, exist_ok=True)

def grab(page, name, url):
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(7000)  # Studio is slow to render
    (out / f"{name}.txt").write_text(page.inner_text("body"), encoding="utf-8")
    page.screenshot(path=str(out / f"{name}.png"), full_page=False)
    print("saved", name)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1500, "height": 950},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://studio.youtube.com", wait_until="domcontentloaded")
    try:
        page.wait_for_url(re.compile(r"/channel/UC"), timeout=30000)
    except Exception:
        pass
    m = re.search(r"/channel/(UC[\w-]+)", page.url)
    if not m:
        print("Not logged in / channel not found. Run login.py first.")
        ctx.close(); raise SystemExit(1)
    cid = m.group(1)
    base = f"https://studio.youtube.com/channel/{cid}"
    grab(page, "dashboard", base)
    grab(page, "videos", base + "/videos/upload")
    grab(page, "analytics_overview", base + "/analytics/tab-overview/period-default")
    grab(page, "analytics_content", base + "/analytics/tab-content/period-default")
    txt = (out / "dashboard.txt").read_text(encoding="utf-8")
    def f(pat):
        mm = re.search(pat, txt)
        return mm.group(1) if mm else ""
    row = [today, f(r"Current subscribers\s+([\d.,KM]+)"), f(r"Views	([\d.,KM]+)"), f(r"Watch time \(hours\)	([\d.,KM]+)")]
    log = pathlib.Path("data") / "stats_log.csv"
    if log.exists():  # one row per day: drop today's earlier row if re-run
        keep = [l for l in log.read_text(encoding="utf-8").splitlines() if not l.startswith(today)]
        log.write_text("\n".join(keep) + "\n", encoding="utf-8")
    new = not log.exists()
    with log.open("a", encoding="utf-8", newline="") as fh:
        if new:
            fh.write("date,subscribers,views_28d,watch_hours_28d\n")
        fh.write(",".join(row) + "\n")
    print("logged:", row)
    (out / "meta.json").write_text(json.dumps({"channel_id": cid, "date": today}), encoding="utf-8")
    ctx.close()
print("done ->", out)
