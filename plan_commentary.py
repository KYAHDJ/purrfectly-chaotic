"""Pick a fresh clip, have Claude write the commentary script (old-videos style) + find the face and the big moment,
write plan_c.json for make_commentary.py. Never uploads."""
import json, os, pathlib, re, shutil, subprocess, sys
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).parent.resolve()
subprocess.run([sys.executable, str(ROOT / "dedupe.py")], cwd=ROOT)
clips = ROOT / "clips"
man = json.loads((clips / "manifest.json").read_text(encoding="utf-8"))
used_p = ROOT / "data" / "used_clips.json"
used = set(json.loads(used_p.read_text(encoding="utf-8"))) if used_p.exists() else set()
W, H = 1080, 1920

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
    d, w, h = probe(f)
    if 6 <= d <= 45: cands.append({**m, "dur": d, "w": w, "h": h, "l": likes(m.get("likes")), "used": m["id"] in used})
cands.sort(key=lambda c: (c["used"], -c["l"]))  # fresh clips first, reuse only when none are left
if cands and cands[0]["used"]: print("No fresh clips left, reusing an older one. Run the clip search for new ones.", flush=True)
if not cands:
    sys.exit("No fresh clips of 6-45 seconds. Run the clip search again.")

# ---- old-video scripts as style examples ----
def old_scripts(n=3):
    out = []
    for p in sorted((ROOT / "data" / "refs" / "old").glob("*_words.json")):
        try:
            w = json.loads(p.read_text(encoding="utf-8"))
            w = w if isinstance(w, list) else w.get("words", [])
            t = " ".join(x[0] if isinstance(x, list) else x.get("word", "") for x in w)
            t = re.split(r"\b[Hh]it (the )?subscribe|\bsubscribe\b", t)[0].strip()
            if 150 < len(t) < 900: out.append(t)
        except Exception:
            pass
    return out[:n]
examples = "\n".join(f'EXAMPLE {i}: "{t}"' for i, t in enumerate(old_scripts(), 1))

def sheet_for(c):
    n = 8; dur = c["dur"]; fr = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        out = ROOT / "data" / "clipsheets" / f"cm_{c['id']}_{k}.jpg"; out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(clips / c["file"]), "-frames:v", "1", "-vf", "scale=240:-1", str(out)], check=True)
        im = Image.open(out); ImageDraw.Draw(im).text((4, 2), f"{t:.1f}s", fill="yellow"); fr.append(im)
    cw, ch = fr[0].size; sh = Image.new("RGB", (cw * 4, ch * 2), "black")
    for k, im in enumerate(fr): sh.paste(im, ((k % 4) * cw, (k // 4) * ch))
    p = ROOT / "data" / "clipsheets" / f"cm_{c['id']}.jpg"; sh.save(p, quality=80); return p

def claude_cmd():
    """Find the Claude CLI: on PATH, or the npm shim (cmd or ps1)."""
    w = shutil.which("claude") or shutil.which("claude.cmd")
    if w: return [w]
    npm = pathlib.Path(os.environ.get("APPDATA", "")) / "npm"
    if (npm / "claude.cmd").exists(): return ["cmd", "/c", str(npm / "claude.cmd")]
    if (npm / "claude.ps1").exists(): return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(npm / "claude.ps1")]
    # python sometimes cannot see the npm shim that PowerShell can: let PowerShell run it
    return ["PS"]

def ask_claude(c, sheet):
    claude = claude_cmd()
    nw = max(48, min(66, int(c["dur"] * 4.3 * 1.5)))
    prompt = f"""Read the image {sheet} . It shows 8 frames of ONE cat video clip, each labeled with its time in seconds (the clip is {c['dur']:.1f}s long).
You write voiceover scripts for a viral cat 'Commentary Short' channel. Study the style of these real scripts:
{examples}

The formula: (1) a shocking hook in the first sentence that starts mid-action, never a normal intro (like 'What you are looking at is not a cat.'); (2) deadpan fake-serious framing (tiny lawyer, 12 hour shift at the biscuit factory, scientists believe...) that matches what really happens in the frames; (3) escalate; (4) at the single biggest moment, a short sentence that starts with exactly 'Boom.' (or 'Wait.' if nothing big happens) followed by a quick reaction line; (5) a revenge-plot or funny ending line. Short punchy sentences, some ending with '!'. Plain words, no emojis, no hashtags, no quotes inside. HARD LIMIT: at most {nw + 6} words total, count them. Everything you say must match what is truly visible in the frames. Do NOT write the subscribe line, it is added later.

Also answer:
- text: true if the frames show burned-in subtitles, captions, a big watermark or channel text over the video, else false.
- focus: [x, y] center of the cat's face at the most important moment, as fractions of the frame (0..1, x from left, y from top).
- bite: the time in seconds of the single biggest moment (the strike, the fall, the scream, the jump), judged from the labels; null if unsure.
- burst: a 1-2 word comic sticker like "WOW!", "NOPE!", "OOF!", "BRUH!" that fits.

Reply with ONLY one JSON object: {{"text":false,"script":"...","focus":[0.5,0.4],"bite":4.2,"burst":"WOW!"}}"""
    (ROOT / "data" / "last_prompt.txt").write_text(prompt, encoding="utf-8")
    if os.environ.get("CLAUDE_REPLY_FILE"):  # testing hook: use a saved reply instead of calling Claude
        reply = pathlib.Path(os.environ["CLAUDE_REPLY_FILE"]).read_text(encoding="utf-8")
        m = re.search(r"\{.*\}", reply, re.S); return json.loads(m.group(0))
    args = ["-p", "--allowedTools", "Read", "--add-dir", str(ROOT), "--output-format", "text"]
    npm = pathlib.Path(os.environ.get("APPDATA", "")) / "npm"
    tries = []
    w = shutil.which("claude") or shutil.which("claude.cmd")
    if w: tries.append([w] + args)
    for nm in ("claude.cmd", "claude.exe"):
        if (npm / nm).exists(): tries.append(["cmd", "/c", str(npm / nm)] + args)
    if (npm / "claude.ps1").exists(): tries.append(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(npm / "claude.ps1")] + args)
    tries.append(["powershell", "-NoProfile", "-Command", "$input | claude " + " ".join(f"'{a_}'" for a_ in args)])
    errs = []; r = None
    for full in tries:
        try:
            r = subprocess.run(full, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=400, cwd=ROOT)
            if re.search(r"\{.*\}", r.stdout, re.S): break
            errs.append(f"{full[0]}: {(r.stdout + r.stderr).strip()[:160]}")
        except Exception as e:
            errs.append(f"{full[0]}: {e}")
        r = None
    if r is None: raise RuntimeError("CLAUDE NOT REACHABLE | " + " || ".join(errs))
    m = re.search(r"\{.*\}", r.stdout, re.S)
    if not m: raise RuntimeError("no JSON: " + r.stdout[:200])
    j = json.loads(m.group(0))
    if not isinstance(j.get("script"), str) or len(j["script"].split()) < 25: raise RuntimeError("script too short")
    return j

pick = None; info = None
for c in cands[:5]:
    print("trying clip", c["id"][:8], f"{c['dur']:.1f}s", flush=True)
    try:
        info = ask_claude(c, sheet_for(c))
    except Exception as e:
        print("Claude step failed:", e, flush=True); info = None
        if "NOT REACHABLE" in str(e) or "no JSON" in str(e) or isinstance(e, (FileNotFoundError, OSError)): break
        continue
    if info.get("text"):
        print("skipped: burned-in text", flush=True); used.add(c["id"]); info = None; continue
    pick = c; break

if pick is None:
    print("STOPPED: no video made. Claude could not write a script for this clip, and I will not make a generic one.", flush=True)
    sys.exit(1)

# focus: fractions of the frame -> fractions of the 1080x1920 canvas (clip is fit inside, letterboxed if not 9:16)
fx, fy = (info.get("focus") or [0.5, 0.4])[:2]
fx = min(max(float(fx), 0.05), 0.95); fy = min(max(float(fy), 0.05), 0.95)
s = min(W / pick["w"], H / pick["h"]); ox = (W - pick["w"] * s) / 2; oy = (H - pick["h"] * s) / 2
cfx = (ox + fx * pick["w"] * s) / W; cfy = (oy + fy * pick["h"] * s) / H
bite = info.get("bite")
try: bite = float(bite) if bite is not None else None
except Exception: bite = None
if bite is not None: bite = round(min(max(bite, 0.5), pick["dur"] - 0.3), 2)
script = re.sub(r"\s+", " ", info["script"]).strip().replace('"', "")
limit = max(48, min(66, int(pick["dur"] * 4.3 * 1.5))) + 10
sents = re.split(r"(?<=[.!?])\s+", script)
si = next((i for i, x in enumerate(sents) if x.lower().startswith("system")), None)
while len(" ".join(sents).split()) > limit and si is not None and si > 3:  # too long: drop a middle sentence, keep hook + reboot + ending
    del sents[si - 1]; si -= 1
script = " ".join(sents)
burst = re.sub(r"[^A-Za-z!?]", "", str(info.get("burst") or "WOW!"))[:7].upper() or "WOW!"
plan = {"id": pick["id"], "script": script, "focus": [round(cfx, 3), round(cfy, 3)], "flip": False,
        "climax_word": "boom", "bite": bite, "burst_text": burst}
(ROOT / "plan_c.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
used_p.parent.mkdir(exist_ok=True); used_p.write_text(json.dumps(sorted(used | {pick["id"]})), encoding="utf-8")
print("plan_c.json written:", pick["id"][:8], "| words:", len(script.split()), "| bite:", bite, "| burst:", burst)
print(script)
