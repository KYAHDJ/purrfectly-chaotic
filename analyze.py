"""Watch top videos in the browser (no downloading): sample frames of the player, build one contact sheet per video.
Usage: python analyze.py   -> data/analysis/<date>/<id>/{sheet.jpg,meta.json}"""
import json, re, io, datetime, pathlib
from urllib.parse import quote
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

today = datetime.date.today().isoformat()
base = pathlib.Path("data/analysis") / today
base.mkdir(parents=True, exist_ok=True)
shorts = json.loads(pathlib.Path(f"data/research/{today}.json").read_text(encoding="utf-8"))
N_SHORTS, N_LONG_FRAMES, N_COMP = 8, 12, 4
DETAILS = """() => { const r = window.ytInitialPlayerResponse; if(!r) return null;
  const v = r.videoDetails || {}; const m = (r.microformat||{}).playerMicroformatRenderer || {};
  return {id:v.videoId,title:v.title,author:v.author,views:+v.viewCount,seconds:+v.lengthSeconds,
          tags:v.keywords||[],description:v.shortDescription,published:m.publishDate}; }"""

def wait_ads(page):
    for _ in range(40):
        if not page.evaluate("() => !!document.querySelector('.html5-video-player.ad-showing')"):
            return
        sk = page.query_selector(".ytp-skip-ad-button, .ytp-ad-skip-button-modern")
        if sk:
            try: sk.click()
            except Exception: pass
        page.wait_for_timeout(1000)

def sample(page, d, times, out):
    page.goto(f"https://www.youtube.com/watch?v={d['id']}", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    page.evaluate("() => { const v=document.querySelector('video'); if(v){v.muted=true; v.play();} }")
    wait_ads(page)
    player = page.query_selector("#movie_player") or page.query_selector("video")
    frames = []
    for t in times:
        page.evaluate("t => { const v=document.querySelector('video'); v.currentTime=t; v.play(); }", t)
        page.wait_for_timeout(1400)
        wait_ads(page)
        img = Image.open(io.BytesIO(player.screenshot(type="jpeg", quality=70))).convert("RGB")
        frames.append((t, img))
    # contact sheet
    cols = 4 if len(frames) > 6 else 3
    tw = 360
    th = int(frames[0][1].height * tw / frames[0][1].width)
    rows = -(-len(frames) // cols)
    sheet = Image.new("RGB", (cols * tw, rows * th), "black")
    dr = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(frames):
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(im.resize((tw, th)), (x, y)); dr.rectangle([x, y, x + 52, y + 16], fill="black")
        dr.text((x + 4, y + 2), f"{t:.0f}s", fill="white")
    out.mkdir(parents=True, exist_ok=True)
    sheet.save(out / "sheet.jpg", quality=80)
    (out / "meta.json").write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    print("analyzed", d["id"], d["title"][:50])

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled", "--mute-audio"],
        viewport={"width": 1280, "height": 800})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # 1) long compilations (priority): find top by views, 3+ minutes
    comps = []
    for q in ["funny cat compilation", "funniest cats compilation try not to laugh"]:
        page.goto(f"https://www.youtube.com/results?search_query={quote(q)}&sp=CAM%253D", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for _ in range(3): page.mouse.wheel(0, 3000); page.wait_for_timeout(1200)
        ids = page.eval_on_selector_all("a[href^='/watch?v=']", "e => e.map(x=>x.getAttribute('href'))")
        ids = list(dict.fromkeys(re.search(r"v=([\w-]{11})", i).group(1) for i in ids if re.search(r"v=([\w-]{11})", i)))
        for vid in ids[:12]:
            if len(comps) >= N_COMP: break
            if any(c["id"] == vid for c in comps): continue
            page.goto(f"https://www.youtube.com/watch?v={vid}", wait_until="domcontentloaded"); page.wait_for_timeout(2000)
            d = page.evaluate(DETAILS)
            if d and d.get("seconds", 0) >= 180:
                comps.append(d); print("compilation found:", f"{d['views']:,}", d["title"][:60])
        if len(comps) >= N_COMP: break
    for d in comps:
        n = N_LONG_FRAMES; step = d["seconds"] / (n + 1)
        sample(page, d, [step * (i + 1) for i in range(n)], base / ("comp_" + d["id"]))

    # 2) top shorts
    for r in shorts[:N_SHORTS]:
        d = {k: r[k] for k in ("id", "title", "author", "views", "seconds", "tags", "description", "published")}
        n = 8; step = max(d["seconds"], 1) / n
        sample(page, d, [min(step * i + 0.3, d["seconds"] - 0.3) for i in range(n)], base / ("short_" + d["id"]))
    ctx.close()
print("done ->", base)
