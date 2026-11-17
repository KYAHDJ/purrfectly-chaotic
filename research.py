"""Research: find top cat Shorts/compilations on YouTube using the logged-in profile.
Collects title, views, channel, length, description, tags. No downloading."""
import json, re, sys, datetime, pathlib
from urllib.parse import quote
from playwright.sync_api import sync_playwright

QUERIES = ["cat compilation shorts", "funny cats shorts", "cats being chaotic shorts", "cat fails shorts"]
WANT = 12
today = datetime.date.today().isoformat()
out = pathlib.Path("data/research"); out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1400, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    ids = []
    for q in QUERIES:
        if len(ids) >= WANT: break
        # sp=CAM%3D -> sort by view count
        page.goto(f"https://www.youtube.com/results?search_query={quote(q)}&sp=CAM%253D", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for _ in range(4):
            page.mouse.wheel(0, 3000); page.wait_for_timeout(1500)
        links = page.eval_on_selector_all("a[href*='/shorts/']", "els => els.map(e => e.getAttribute('href'))")
        for l in links:
            m = re.search(r"/shorts/([\w-]{11})", l)
            if m and m.group(1) not in ids:
                ids.append(m.group(1))
        print(q, "->", len(ids), "shorts so far")
    results = []
    for vid in ids[:WANT + 4]:
        if len(results) >= WANT: break
        page.goto(f"https://www.youtube.com/watch?v={vid}", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        d = page.evaluate("""() => { const r = window.ytInitialPlayerResponse; if(!r) return null;
            const v = r.videoDetails || {}; const m = (r.microformat||{}).playerMicroformatRenderer || {};
            return {id:v.videoId,title:v.title,author:v.author,views:+v.viewCount,seconds:+v.lengthSeconds,
                    tags:v.keywords||[],description:v.shortDescription,published:m.publishDate}; }""")
        if d and d.get("title"):
            d["url"] = f"https://www.youtube.com/shorts/{vid}"
            results.append(d); print(f"{d['views']:>12,}  {d['title'][:70]}")
    ctx.close()

results.sort(key=lambda r: r["views"], reverse=True)
(out / f"{today}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("saved", len(results), "->", out / f"{today}.json")
