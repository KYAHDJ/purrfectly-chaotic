"""Study fast, talkative commentary videos: pace (words/min), hook, caption text. Read-only, nothing downloaded."""
import json, re, datetime, pathlib
from urllib.parse import quote
from playwright.sync_api import sync_playwright

QUERIES = ["funny cats shorts commentary", "cat commentary #shorts", "funny animals narration #shorts", "cats voiceover funny #shorts", "cat fails commentary shorts"]
today = datetime.date.today().isoformat()
out = pathlib.Path("data/research"); out.mkdir(parents=True, exist_ok=True)
DETAILS = """() => { const r = window.ytInitialPlayerResponse; if(!r) return null;
  const v = r.videoDetails || {};
  const tr = (((r.captions||{}).playerCaptionsTracklistRenderer||{}).captionTracks)||[];
  return {id:v.videoId,title:v.title,author:v.author,views:+v.viewCount,seconds:+v.lengthSeconds,
          caps: tr.map(t=>({lang:t.languageCode,kind:t.kind||'',url:t.baseUrl}))}; }"""

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False, viewport={"width": 1300, "height": 900},
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled", "--mute-audio"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    ids = []
    for q in QUERIES:
        page.goto(f"https://www.youtube.com/results?search_query={quote(q)}&sp=CAM%253D", wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        for _ in range(3): page.mouse.wheel(0, 3000); page.wait_for_timeout(1100)
        before = len(ids)
        for l in page.eval_on_selector_all("a[href*='/shorts/']", "e => e.map(x => x.getAttribute('href'))"):
            m = re.search(r"/shorts/([\w-]{11})", l)
            if m and m.group(1) not in ids: ids.append(m.group(1))
        print(q, "->", len(ids) - before, flush=True)
    print("candidates:", len(ids))
    res = []
    SAMPLE = """async (maxs) => {
      const v = document.querySelector('video'); v.muted = true; v.currentTime = 0; await v.play().catch(()=>{});
      const btn = document.querySelector('.ytp-subtitles-button');
      if (btn && btn.getAttribute('aria-pressed') !== 'true') btn.click();
      const log = []; const t0 = performance.now();
      while ((performance.now() - t0) / 1000 < Math.min(maxs, 26) + 1) {
        const segs = [...document.querySelectorAll('.ytp-caption-segment')].map(x => x.innerText.trim()).filter(Boolean);
        log.push([+v.currentTime.toFixed(2), segs.join(' ')]);
        await new Promise(r => setTimeout(r, 250));
      }
      return log; }"""
    for vid in ids[:40]:
        if len(res) >= 10: break
        page.goto(f"https://www.youtube.com/watch?v={vid}", wait_until="domcontentloaded"); page.wait_for_timeout(2500)
        d = page.evaluate(DETAILS)
        if not d or not d.get("caps") or d["seconds"] > 60: continue
        d.pop("caps")
        log = page.evaluate(SAMPLE, d["seconds"])
        # count distinct caption words by first time seen
        seen = []; prev = ""
        for t, txt in log:
            if txt and txt != prev:
                new_words = txt.split()
                pw = prev.split()
                k = 0
                while k < len(pw) and k < len(new_words) and pw[len(pw) - 1 - k:] != new_words[:k + 1][-(k + 1):]: k += 1
                seen.append((t, txt)); prev = txt
        words = " ".join(x[1] for x in seen).split()
        spoken_span = max((seen[-1][0] - seen[0][0]), 1) if seen else 1
        if len(words) < 6: continue
        d.update(first_caption_s=seen[0][0], cap_events=len(seen), words_est=len(words), wpm_est=round(len(words) / min(d["seconds"], 26) * 60), sample=[x[1] for x in seen][:14])
        res.append(d); print(f"{d['views']:>12,} {d['seconds']:>3}s ~{d['wpm_est']:>3} wpm first@{d['first_caption_s']}s | {d['title'][:50].encode('ascii','ignore').decode()}", flush=True)
    ctx.close()
res.sort(key=lambda r: -r["views"])
(out / f"voice_{today}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print("saved", len(res))
