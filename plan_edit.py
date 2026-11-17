"""Edit planner: pick a fresh clip, let Claude WATCH its frames + motion peaks and write a custom edit plan:
 - lines of commentary, each anchored to a moment (source time) of the clip  -> the video is time-warped (cut / speed up / slow down) to fit
 - effect events (punch-in, magnifier, sticker, shake, flash, glitch) tied to real moments, only when they fit
Writes plan_e.json for make_edit.py. Never uploads."""
import json, os, pathlib, re, shutil, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).parent.resolve()
subprocess.run([sys.executable, str(ROOT / "dedupe.py")], cwd=ROOT)
clips = ROOT / "clips"
man = json.loads((clips / "manifest.json").read_text(encoding="utf-8"))
used_p = ROOT / "data" / "used_clips.json"
used = set(json.loads(used_p.read_text(encoding="utf-8"))) if used_p.exists() else set()
(ROOT / "data" / "clipsheets").mkdir(parents=True, exist_ok=True)
ONLY = os.environ.get("EDIT_CLIP")  # force one clip id (testing)

def likes(s):
    s = str(s or "").strip().lower().replace(",", "")
    try:
        if s.endswith("k"): return float(s[:-1]) * 1e3
        if s.endswith(("w", "万")): return float(s[:-1]) * 1e4
        return float(re.sub(r"[^\d.]", "", s) or 0)
    except Exception:
        return 0

def probe(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", str(f)], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout); s = j["streams"][0]
        return float(j["format"]["duration"]), int(s["width"]), int(s["height"])
    except Exception:
        return 0, 0, 0

cands = []
for m in man:
    f = clips / m["file"]
    if not f.exists(): continue
    if ONLY and m["id"] != ONLY: continue
    d, w, h = probe(f)
    if 5 <= d <= 45: cands.append({**m, "dur": d, "w": w, "h": h, "l": likes(m.get("likes")), "used": m["id"] in used})
cands.sort(key=lambda c: (c["used"], -c["l"]))
if not cands: sys.exit("No usable clips (5-45 seconds). Run the clip search again.")
if cands[0]["used"] and not ONLY: print("No fresh clips left, reusing an older one. Run the clip search for new ones.", flush=True)

# ---------- what Claude sees: frame sheet + motion peaks ----------
def motion(c):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clips / c["file"]), "-vf", "fps=10,scale=48:84,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8).reshape(-1, 84, 48).astype(np.float32)
    d = np.abs(np.diff(a, axis=0))
    e = np.convolve(d.mean(axis=(1, 2)), np.ones(3) / 3, "same")
    ys, xs = np.mgrid[0:84, 0:48]
    cen = [((di * xs).sum() / max(di.sum(), 1e-6) / 48, (di * ys).sum() / max(di.sum(), 1e-6) / 84) for di in d]
    return e, cen  # one value per 0.1s

def peaks(e, n=7):
    idx = list(np.argsort(-e)); out = []
    for i in idx:
        if all(abs(i - j) >= 8 for j in out): out.append(int(i))
        if len(out) >= n: break
    return sorted(out)

def sheet_for(c):
    n = 20; frs = []
    for k in range(n):
        t = min(c["dur"] * (k + 0.5) / n, c["dur"] - 0.05)
        out = ROOT / "data" / "clipsheets" / f"pe_{c['id']}_{k}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(clips / c["file"]), "-frames:v", "1", "-vf", "scale=216:-1", str(out)], check=True)
        im = Image.open(out); ImageDraw.Draw(im).rectangle([0, 0, 52, 14], fill="black"); ImageDraw.Draw(im).text((3, 1), f"{t:.1f}s", fill="yellow"); frs.append(im)
    cw, ch = frs[0].size; sh = Image.new("RGB", (cw * 5, ch * 4), "black")
    for k, im in enumerate(frs): sh.paste(im, ((k % 5) * cw, (k // 5) * ch))
    p = ROOT / "data" / "clipsheets" / f"pe_{c['id']}.jpg"; sh.save(p, quality=82); return p

def old_scripts(n=3):
    out = []
    for p in sorted((ROOT / "data" / "refs" / "old").glob("*_words.json")):
        try:
            w = json.loads(p.read_text(encoding="utf-8")); w = w if isinstance(w, list) else w.get("words", [])
            t = " ".join(x[0] if isinstance(x, list) else x.get("word", "") for x in w)
            t = re.split(r"\b[Hh]it (the )?subscribe|\bsubscribe\b", t)[0].strip()
            if 150 < len(t) < 900: out.append(t)
        except Exception:
            pass
    return out[:n]
examples = "\n".join(f'EXAMPLE {i}: "{t}"' for i, t in enumerate(old_scripts(), 1))

BANNED = ["not a cat", "scientists believe", "system error", "rebooting", "plotting his revenge", "plotting revenge", "tiny professional", "tiny lawyer", "what you are looking at"]

def claude_run(prompt):
    args = ["-p", "--allowedTools", "Read", "--add-dir", str(ROOT), "--output-format", "text"]
    npm = pathlib.Path(os.environ.get("APPDATA", "")) / "npm"
    tries = []
    w = shutil.which("claude") or shutil.which("claude.cmd")
    if w: tries.append([w] + args)
    for nm in ("claude.cmd", "claude.exe"):
        if (npm / nm).exists(): tries.append(["cmd", "/c", str(npm / nm)] + args)
    if (npm / "claude.ps1").exists(): tries.append(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(npm / "claude.ps1")] + args)
    tries.append(["powershell", "-NoProfile", "-Command", "$input | claude " + " ".join(f"'{a_}'" for a_ in args)])
    errs = []
    for full in tries:
        try:
            r = subprocess.run(full, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=500, cwd=ROOT)
            if re.search(r"\{.*\}", r.stdout, re.S): return r.stdout
            errs.append(f"{full[0]}: {(r.stdout + r.stderr).strip()[:160]}")
        except Exception as e:
            errs.append(f"{full[0]}: {e}")
    raise RuntimeError("CLAUDE NOT REACHABLE | " + " || ".join(errs))

def build_prompt(c, sheet, pk, cen, extra=""):
    dur = c["dur"]
    total = max(13.0, min(32.0, dur * 1.4 + 2.0))            # target video length
    words = int((total - 4.5) * 4.2)                    # commentary words, CTA not included
    pks = ", ".join(f"{p/10:.1f}s (movement around x={cen[min(p, len(cen)-1)][0]:.2f}, y={cen[min(p, len(cen)-1)][1]:.2f})" for p in pk)
    return f"""Read the image {sheet} . It shows 20 frames of ONE cat video clip, each labeled with its time in seconds (clip length {dur:.1f}s). Biggest motion happens near: {pks}. (x,y are where the movement is, a hint for focus; the cat's FACE is usually near it, check the frames.)
You are the editor of a viral cat 'Commentary Short' channel. You write the voiceover AND the edit for THIS clip only. Style of the channel's real scripts (learn the energy, never copy the lines):
{examples}

HOW THE EDIT WORKS (important):
- You split the commentary into 5-9 LINES (one sentence each). Every line has "at": the moment of the clip (seconds) that line is about. The video is time-warped to follow your lines: boring stretches between two anchors get cut or sped up, and if two anchors are close together that moment plays in slow motion. So put anchors on the real beats of the action, and skip dead time.
- Lines go in clip order (at must ascend). The first line starts the video, so open with a hook that hits the first interesting thing right away. Never a normal intro.
- The WHOLE script must be about {words} words, absolute maximum {words + 8} (the video is only {total:.0f}s long, so COUNT your words; each line at most 14 words). Write LONG, connected, flowing sentences with colorful vocabulary and specific comic detail, like a fast breathless commentator (for example: 'traded their shins for pure unadulterated rage', 'plotting a murder it physically cannot execute'). It is read as one continuous stream with almost no pauses, so NO choppy 2-3 word fragments (at most one short punchline fragment in the whole script). Describe and exaggerate EXACTLY what is visible at that moment (the wiggle, the crouch, the fall, the look). Be specific to this clip, jokes must come from what happens. No emojis, no hashtags, no quotes. Do NOT write the subscribe line.
- NEVER use these stock phrases: {', '.join(repr(b) for b in BANNED)}. Find a fresh comedic angle for this clip (pick ONE: sports commentator, nature documentary, courtroom, heist movie, tech support, angry boss, therapist, conspiracy, dramatic soap, hype man, etc.) and write the lines in that voice. Vary it, do not default to the same angle.
- EVENTS are visual effects tied to real moments (t = clip seconds). Use only the ones that fit, 5-8 total, never two within 0.8s of each other. Make the video ENTERTAINING: use a mix of punch, circle, shake, flash on the real beats (the renderer also adds automatic rhythm zooms):
  punch: hard zoom-in on a detail at its exact moment ("zoom": 1.4-2.0, "focus": [x,y] the thing to zoom on, "dur": 0.5-1.2)
  circle: live round magnifier, 1.6x zoom, centered on the cat's FACE or eyes, OR on the key action detail (the paw entering the mouth, the object it touches); never empty floor ("focus": [x,y] of the face, "dur": 1.2-2)
  shake: screen shake on an impact, jump or landing
  flash: white flash on a sudden change
  glitch: short RGB glitch, only if the cat freezes or stares blankly
  focus x,y are fractions of the frame (0..1, x from left, y from top).
{extra}
Also: "text": true if the frames show burned-in subtitles, captions, big watermark or channel text over the video, else false. "angle": your chosen comedic angle in 3-6 words.

Reply with ONLY one JSON object, like:
{{"text":false,"angle":"sports commentator","lines":[{{"say":"Folks, the cat is lining up the shot.","at":0.8}},{{"say":"Wiggle wiggle wiggle!","at":2.1,"pause":0.3}}],"events":[{{"type":"punch","t":2.1,"zoom":1.6,"focus":[0.5,0.7],"dur":0.8}},{{"type":"burst","t":6.5,"text":"OOF!"}}]}}"""

def norm(j, c, e):
    dur = c["dur"]
    lines = []
    for L in j.get("lines", []):
        say = re.sub(r"\s+", " ", str(L.get("say", ""))).strip().replace('"', "")
        try: at = float(L.get("at", 0))
        except Exception: at = 0.0
        if len(say.split()) >= 1: lines.append({"say": say, "at": round(min(max(at, 0), dur - 0.2), 2), "pause": round(min(max(float(L.get("pause", 0) or 0), 0), 0.6), 2)})
    lines.sort(key=lambda x: x["at"])
    total = max(13.0, min(32.0, dur * 1.4 + 2.0)); limit = int((total - 4.5) * 4.2) + 14
    nw_ = len(" ".join(l["say"] for l in lines).split())
    if nw_ > limit: raise RuntimeError(f"too long: {nw_} words, the maximum is {limit - 12}. Rewrite SHORTER (about {limit - 18} words, each line at most 14 words)")
    if len(lines) < 3: raise RuntimeError("too few lines")
    text = " ".join(l["say"] for l in lines).lower()
    bad = [b for b in BANNED if b in text]
    if bad: raise RuntimeError("banned stock phrase: " + bad[0])
    pks = [p / 10 for p in peaks(e)]
    ev = []
    for E in j.get("events", []):
        ty = str(E.get("type", "")).lower()
        if ty not in ("punch", "circle", "shake", "flash", "glitch", "burst"): continue
        try: t = float(E.get("t"))
        except Exception: continue
        near = min(pks, key=lambda p: abs(p - t)) if pks else t
        if abs(near - t) <= 0.4: t = near            # snap to the real motion peak
        t = round(min(max(t, 0), dur - 0.1), 2)
        o = {"type": ty, "t": t}
        fx, fy = (E.get("focus") or [0.5, 0.4])[:2]
        o["focus"] = [min(max(float(fx), 0.05), 0.95), min(max(float(fy), 0.05), 0.95)]
        o["zoom"] = min(max(float(E.get("zoom", 1.6) or 1.6), 1.3), 2.2)
        o["dur"] = min(max(float(E.get("dur", 0.9) or 0.9), 0.4), 2.0)
        o["text"] = re.sub(r"[^A-Za-z!?]", "", str(E.get("text") or "WOW!"))[:7].upper() or "WOW!"
        ev.append(o)
    ev.sort(key=lambda x: x["t"]); keep = []
    for o in ev:
        if not keep or o["t"] - keep[-1]["t"] >= 0.8: keep.append(o)
    return {"lines": lines, "events": keep[:8], "angle": str(j.get("angle", ""))[:40]}

pick = None; plan = None
for c in cands[:5]:
    print("trying clip", c["id"][:8], f"{c['dur']:.1f}s", flush=True)
    try:
        e, cen = motion(c); sheet = sheet_for(c); pk = peaks(e)
        err = ""
        for attempt in range(3):
            prompt = build_prompt(c, sheet, pk, cen, extra=err)
            (ROOT / "data" / "last_prompt.txt").write_text(prompt, encoding="utf-8")
            if os.environ.get("CLAUDE_REPLY_FILE"): out = pathlib.Path(os.environ["CLAUDE_REPLY_FILE"]).read_text(encoding="utf-8")
            else: out = claude_run(prompt)
            j = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
            if j.get("text"): break
            try:
                plan = norm(j, c, e); break
            except RuntimeError as ex:
                print("rejected:", ex, "- asking again", flush=True); err = f"\nYour previous answer was rejected: {ex}. Fix that."; plan = None
        if j.get("text"):
            print("skipped: burned-in text", flush=True); used.add(c["id"]); plan = None; continue
        if plan is None: continue
        pick = c; break
    except RuntimeError as ex:
        print("Claude step failed:", ex, flush=True)
        if "NOT REACHABLE" in str(ex): break
    except Exception as ex:
        print("planner error:", repr(ex), flush=True)

if pick is None:
    print("STOPPED: no video made. Claude could not plan an edit for these clips, and I will not make a generic one.", flush=True)
    used_p.write_text(json.dumps(sorted(used)), encoding="utf-8"); sys.exit(1)

plan.update({"id": pick["id"], "file": pick["file"], "dur": round(pick["dur"], 2), "w": pick["w"], "h": pick["h"], "peaks": [p / 10 for p in peaks(motion(pick)[0])], "cen": [[round(i / 10, 1), round(float(x), 3), round(float(y), 3)] for i, (x, y) in enumerate(motion(pick)[1]) if i % 5 == 0]})
(ROOT / "plan_e.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
used_p.write_text(json.dumps(sorted(used | {pick["id"]})), encoding="utf-8")
print("plan_e.json written:", pick["id"][:8], "| angle:", plan["angle"], "| lines:", len(plan["lines"]), "| events:", [(x["type"], x["t"]) for x in plan["events"]])
for l in plan["lines"]: print(f'  @{l["at"]:>5}s  {l["say"]}')
