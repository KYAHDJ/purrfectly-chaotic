"""Search rednote for cat videos, download the top ones into clips/ (with a manifest).
Usage: python rednote_fetch.py [keyword] [count]"""
import sys, re, json, pathlib, time
from urllib.parse import quote
from playwright.sync_api import sync_playwright

kw = sys.argv[1] if len(sys.argv) > 1 else "funny cat"
want = int(sys.argv[2]) if len(sys.argv) > 2 else 8
out = pathlib.Path("clips"); out.mkdir(exist_ok=True)
manifest_p = out / "manifest.json"
manifest = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.exists() else []
have = {m["id"] for m in manifest}
_sp = pathlib.Path("data/skip_ids.json")
if _sp.exists(): have |= set(json.loads(_sp.read_text(encoding="utf-8")))

def likes(s):
    s = (s or "").strip().lower().replace(",", "")
    try:
        if s.endswith("k"): return float(s[:-1]) * 1e3
        if s.endswith("w") or s.endswith("万"): return float(s[:-1]) * 1e4
        return float(re.sub(r"[^\d.]", "", s) or 0)
    except Exception:
        return 0

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "profile", channel="chrome", headless=False, viewport={"width": 1300, "height": 900},
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled", "--mute-audio"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(f"https://www.rednote.com/search_result?keyword={quote(kw)}&source=web_explore_feed&type=51", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.mouse.wheel(0, 2500); page.wait_for_timeout(1500)
    cards = page.evaluate("""() => [...document.querySelectorAll('section.note-item')].map((c, idx) => {
        const t = c.querySelector('.title, .footer .title');
        const l = c.querySelector('.like-wrapper .count, .count');
        const a = c.querySelector('a[href*="/search_result/"]');
        return {idx, href: a ? a.href : '', title: t ? t.innerText : '', likes: l ? l.innerText : ''};
    })""")
    print("cards found:", len(cards))
    cards.sort(key=lambda c: likes(c["likes"]), reverse=True)
    search_url = page.url
    got = 0
    for c in cards:
        if got >= want: break
        m = re.search(r"([0-9a-f]{24})", c["href"])
        if not m or m.group(1) in have: continue
        nid = m.group(1)
        try:
            page.click(f"section.note-item >> nth={c['idx']}"); page.wait_for_timeout(5000)
            html = page.content()
            urls = re.findall(r"https?://[^\"'\s\\]+?\.mp4[^\"'\s\\]*", html)
            dur = page.evaluate("() => { const v = document.querySelector('video'); return v ? v.duration : null; }")
            if not urls:
                print("no video in", nid, "(image post?)"); page.keyboard.press("Escape"); page.wait_for_timeout(800); continue
            if dur and (dur < 4 or dur > 60):
                print("skip", nid, "duration", round(dur)); page.keyboard.press("Escape"); page.wait_for_timeout(800); continue
            resp = ctx.request.get(urls[0], headers={"Referer": "https://www.rednote.com/"})
            body = resp.body()
            if resp.status != 200 or len(body) < 50_000:
                print("download failed", nid, resp.status); page.keyboard.press("Escape"); page.wait_for_timeout(800); continue
            f = out / f"rn_{nid}.mp4"; f.write_bytes(body)
            manifest.append({"id": nid, "file": f.name, "title": c["title"], "likes": c["likes"], "duration": dur, "page": c["href"]})
            got += 1; print(f"saved {f.name}  {dur and round(dur)}s  likes={c['likes']}  {len(body)//1024}KB")
        except Exception as e:
            print("error", nid, str(e)[:150])
        page.keyboard.press("Escape"); page.wait_for_timeout(800)
        if "search_result?" not in page.url:
            page.goto(search_url, wait_until="domcontentloaded"); page.wait_for_timeout(3000)
            for _ in range(3): page.mouse.wheel(0, 2500); page.wait_for_timeout(800)
    manifest_p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    ctx.close()
print("clips saved:", got)
