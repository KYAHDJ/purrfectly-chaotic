"""Pick the best 8 unused clips, name them (via Claude, with a fallback), write plan.json for make_video.py."""
import json, pathlib, re, shutil, subprocess, sys
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).parent.resolve()
subprocess.run([sys.executable, str(ROOT / "dedupe.py")], cwd=ROOT)  # never use the same video twice
clips = ROOT / "clips"
man = json.loads((clips / "manifest.json").read_text(encoding="utf-8"))
used_p = ROOT / "data" / "used_clips.json"
used = set(json.loads(used_p.read_text(encoding="utf-8"))) if used_p.exists() else set()

def likes(s):
    s = str(s or "").strip().lower().replace(",", "")
    try:
        if s.endswith("k"): return float(s[:-1]) * 1e3
        if s.endswith(("w", "万")): return float(s[:-1]) * 1e4
        return float(re.sub(r"[^\d.]", "", s) or 0)
    except Exception:
        return 0

def dur(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except Exception: return 0

items = []
for m in man:
    f = clips / m["file"]
    if f.exists():
        d = dur(f)
        if d >= 3.5: items.append({**m, "dur": d, "l": likes(m.get("likes")), "used": m["id"] in used})
fresh = sorted([i for i in items if not i["used"]], key=lambda i: -i["l"])
old = sorted([i for i in items if i["used"]], key=lambda i: -i["l"])
NR = 8  # ranks in the video
cands = (fresh + old)[:12]
if len(cands) < NR:
    sys.exit(f"Only {len(cands)} usable clips, need {NR}. Run the clip search again.")

# frame strips -> one sheet for judging + naming
sheets = ROOT / "data" / "clipsheets"; sheets.mkdir(parents=True, exist_ok=True)
strips = []
for p in cands:
    out = sheets / f"{p['id']}.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(clips / p["file"]), "-vf", f"fps=4/{p['dur']:.2f},scale=200:-1,tile=4x1", "-frames:v", "1", str(out)], check=True)
    strips.append(Image.open(out))
W = max(s.width for s in strips); H = sum(s.height + 16 for s in strips)
sheet = Image.new("RGB", (W, H), "black"); d = ImageDraw.Draw(sheet); y = 0
for n, s_ in enumerate(strips, 1):
    d.text((4, y + 2), f"CLIP {n}", fill="white"); sheet.paste(s_, (0, y + 16)); y += s_.height + 16
naming = sheets / "naming_sheet.jpg"; sheet.save(naming, quality=75)

N = len(cands)
(sheets / "cands.json").write_text(json.dumps([c["id"] for c in cands]), encoding="utf-8")
labels = [f"Cat Moment {n}" for n in range(1, N + 1)]
has_text = [False] * N
lines = [""] * N
import os
npm_ = pathlib.Path(os.environ.get("APPDATA", "")) / "npm"
claude = [shutil.which("claude") or shutil.which("claude.cmd")] if (shutil.which("claude") or shutil.which("claude.cmd")) else (["cmd", "/c", str(npm_ / "claude.cmd")] if (npm_ / "claude.cmd").exists() else ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(npm_ / "claude.ps1")])  # python can't see npm shims on this PC; cmd can
if claude:
    prompt = (f"Read the image {naming} . It shows {N} cat video clips (CLIP 1..{N}), each as 4 frames. For EACH clip give: "
              "label = a short funny reaction caption for the ranking list, 2-4 words, max 20 characters, in the style of 'Bro's hungry', 'Flashlight', 'That was personal', 'Tried his best', 'Eww' (plain letters and apostrophes only, no emojis); "
              "text = true if the frames show burned-in subtitles, captions, a big watermark or channel text overlaid on the video, else false. "
              f"Reply with ONLY a JSON array of {N} objects like [{{\"label\":\"Bro's hungry\",\"text\":false}}, ...] in clip order, nothing else.")
    try:
        r = subprocess.run(claude + ["-p", "--allowedTools", "Read", "--add-dir", str(ROOT), "--output-format", "text"],
                           input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=300, cwd=ROOT)
        m = re.search(r"\[.*\]", r.stdout, re.S)
        got = json.loads(m.group(0)) if m else []
        if len(got) == N and all(isinstance(x, dict) and "label" in x for x in got):
            labels = [str(x["label"]).strip()[:28] for x in got]
            has_text = [bool(x.get("text")) for x in got]
            lines = [str(x.get("line") or "").strip()[:220] for x in got]
        else:
            print("naming fallback (unexpected reply):", r.stdout[:150])
    except Exception as e:
        print("naming fallback:", e)

for c, l, t, ln in zip(cands, labels, has_text, lines):
    c["label"], c["text"], c["line"] = l, t, ln
clean = [c for c in cands if not c["text"]]
skipped = [c["id"][:8] for c in cands if c["text"]]
if skipped: print("skipped (burned-in text):", skipped)
pool = clean if len(clean) >= NR else cands
pick = sorted(pool, key=lambda c: (c["text"], c["used"], -c["l"]))[:NR]
print("picked:", [p["id"][:8] for p in pick], "fresh:", sum(1 for p in pick if not p["used"]))

# countdown: lowest likes = #5 ... highest likes = #1
order = sorted(range(NR), key=lambda i: pick[i]["l"])
plan = []
for rank, i in zip(range(NR, 0, -1), order):
    p = pick[i]
    plan.append({"rank": rank, "id": p["id"], "label": p["label"], "start": 0, "len": round(min(4.5 if rank == 1 else 3.6, p["dur"] - 0.1), 1)})
(ROOT / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
used_p.parent.mkdir(exist_ok=True)
used_p.write_text(json.dumps(sorted(used | {p["id"] for p in pick})), encoding="utf-8")
print("plan:", [(x["rank"], x["label"]) for x in plan])
