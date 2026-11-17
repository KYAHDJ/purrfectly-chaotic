"""Clip-driven Commentary Short renderer.
Reads plan_e.json (from plan_edit.py): lines of commentary anchored to moments of the clip + effect events.
1) voice per line (VoiceStudio, sped up after) 2) time-warp the clip so every line lands on its moment (cut dead time, speed up, slow-mo)
3) effects only where the plan says, at the real moments 4) one-word captions, sfx, music, subscribe cursor gag, mastering. Never uploads."""
import subprocess, pathlib, json, sys, datetime, shutil, re, wave, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).parent.resolve(); sys.path.insert(0, str(ROOT))
OUT = ROOT / "output"; OUT.mkdir(exist_ok=True)
TMP = OUT / "_tmpe"
if TMP.exists(): shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir(exist_ok=True)
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
W, H = 1080, 1920
VSPEED = float(os.environ.get("VSPEED", "1.3")); _DAV = os.environ.get("VOICE_ENGINE", "edge") in ("edge", "david")
ATEMPO = float(os.environ.get("VATEMPO", "1.0" if _DAV else "1.75"))
VPITCH = float(os.environ.get("VPITCH", "1.0"))  # no pitch shift: it made the voice ugly
import random
CTA_MEOW = "Hit subscribe and click the like button to watch it turn into a meow emoji."
CTA_RATE = "Rate this absolute genius from one to ten in the comments."
CTA_MODE = os.environ.get("CTA") or random.Random(plan_id := json.loads((ROOT / "plan_e.json").read_text(encoding="utf-8"))["id"]).choice(["none", "none", "none", "rate", "meow"])
CTA = {"meow": CTA_MEOW, "rate": CTA_RATE, "none": None}[CTA_MODE]
print("ending:", CTA_MODE, flush=True)
STOP = set("this that with have they their there what when then than from into just like your about would could really every very over only even some more most been being were also while these those and the but for are was his her its him she you can not".split())
CYAN, YELLOW, GREEN = "FFFF00", "00E6FF", "40FF40"  # ASS BGR
WHITE = "FFFFFF"
CYCLE = [WHITE, CYAN, YELLOW, WHITE, GREEN, YELLOW, CYAN]

import voice, asr_util
plan = json.loads((ROOT / "plan_e.json").read_text(encoding="utf-8"))
src = ROOT / "clips" / plan["file"]
cw_, ch_ = plan["w"], plan["h"]; sdur = plan["dur"]
lines = plan["lines"]; events = plan.get("events", [])
def run(cmd): subprocess.run(cmd, check=True)

# ---------- 1. voice: one TTS call per line, tight gaps ----------
voice.ensure_backend() if os.environ.get("VOICE_ENGINE", "edge") not in ("edge", "david") and os.environ.get("VOICE_FALLBACK") != "sapi" else None
VSR = 24000
texts = [l["say"] for l in lines] + ([CTA] if CTA else [])
pauses = [l.get("pause", 0) for l in lines] + ([0.1] if CTA else [])
parts = []
for i, tx in enumerate(texts):
    raw = TMP / f"v{i}.wav"; fin = TMP / f"v{i}f.wav"
    voice.tts(tx, raw, speed=VSPEED)
    pitch = VPITCH * (1.04 if tx.endswith("!") else (1.02 if tx.endswith("?") else 1.0))
    trim = "silenceremove=start_periods=1:start_threshold=-45dB:detection=peak,areverse,silenceremove=start_periods=1:start_threshold=-45dB:detection=peak,areverse"
    run([FFMPEG, "-y", "-v", "error", "-i", str(raw), "-af", f"asetrate={int(VSR*pitch)},aresample={VSR},atempo={ATEMPO/pitch:.3f},{trim}", "-ac", "1", "-ar", str(VSR), str(fin)])
    with wave.open(str(fin)) as w_: parts.append(np.frombuffer(w_.readframes(w_.getnframes()), "<i2"))
seq = []; Ls = []; Ld = []; pos = 0.0   # line start/dur on the voice timeline; each video segment covers [gap + line]
for i, x in enumerate(parts):
    gap = 0.1 if i == 0 else (0.04 + pauses[i] if i < len(parts) - 1 else 0.14)
    seq.append(np.zeros(int(VSR * gap), "<i2")); seq.append(x)
    Ls.append(pos); pos += gap + len(x) / VSR; Ld.append(pos - Ls[-1])   # Ld includes the gap before the line
allv = np.concatenate(seq); dv = len(allv) / VSR
vwav = TMP / "voice.wav"
with wave.open(str(vwav), "wb") as w_:
    w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(VSR); w_.writeframes(allv.astype("<i2").tobytes())
TAIL = 0.8; T = round(dv + TAIL, 2)
Ld[-1] += TAIL
print(f"voice {dv:.1f}s | lines {len(lines)} | video {T}s", flush=True)

# ---------- 2. time-warp the clip so each line lands on its moment ----------
s_fit = min(W / cw_, H / ch_); ox = (W - cw_ * s_fit) / 2; oy = (H - ch_ * s_fit) / 2
def canvas(fx, fy): return (ox + fx * cw_ * s_fit) / W, (oy + fy * ch_ * s_fit) / H
COMP = (f"fps=30,split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5[bg];"
        f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
VMIN, VMAX = 0.55, 2.4
segs = []   # (out_start, src_start, window, speed)
for i in range(len(lines)):
    a = lines[i]["at"]; D = Ld[i]; nxt = lines[i + 1]["at"] if i + 1 < len(lines) else sdur
    S = max(nxt - a, 0.3)
    v = min(max(S / D, VMIN), VMAX); win = min(S, D * v, sdur - a)
    segs.append((Ls[i], a, win, v))
files = []
for i, (os_, a, win, v) in enumerate(segs):
    D = Ld[i]; f = TMP / f"seg{i}.mp4"; last_seg = i == len(segs) - 1
    vf = f"setpts=(PTS-STARTPTS)/{v:.4f},{COMP}" + ("" if last_seg else f",tpad=stop_mode=clone:stop_duration={D:.2f}")
    run([FFMPEG, "-y", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{win:.3f}", "-i", str(src), "-an", "-filter_complex", f"[0:v]{vf}"] + ([] if last_seg else ["-t", f"{D:.3f}"]) +
        ["-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30", str(f)])
    if last_seg and win / v < D - 0.05:   # never freeze: play it forward and backward until the segment is long enough
        fr = TMP / "last_r.mp4"
        run([FFMPEG, "-y", "-v", "error", "-i", str(f), "-vf", "reverse", "-an", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30", str(fr)])
        (TMP / "lastpp.txt").write_text(chr(10).join([f"file '{f.name}'", "file 'last_r.mp4'"] * (int(D / max(win / v, 0.3)) + 3)) + chr(10), encoding="utf-8")
        f2 = TMP / "last_pp.mp4"
        run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(TMP / "lastpp.txt"), "-t", f"{D:.3f}", "-c", "copy", str(f2)]); f = f2
    files.append(f)
if CTA:
    # CTA segment: the clip's last 2s, forward/backward, so the ending never freezes
    t0 = max(sdur - 2.0, 0); base = ["-an", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30"]
    run([FFMPEG, "-y", "-v", "error", "-ss", f"{t0:.2f}", "-i", str(src), "-filter_complex", f"[0:v]{COMP}", *base, str(TMP / "tf.mp4")])
    run([FFMPEG, "-y", "-v", "error", "-i", str(TMP / "tf.mp4"), "-vf", "reverse", *base, str(TMP / "tr.mp4")])
    nrep = int(Ld[-1] / 1.8) + 3
    (TMP / "pp.txt").write_text(chr(10).join(["file 'tf.mp4'", "file 'tr.mp4'"] * nrep) + chr(10), encoding="utf-8")
    run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(TMP / "pp.txt"), "-t", f"{Ld[-1]:.3f}", "-c", "copy", str(TMP / "cta.mp4")])
    files.append(TMP / "cta.mp4")
(TMP / "list.txt").write_text(chr(10).join(f"file '{f.name}'" for f in files) + chr(10), encoding="utf-8")
run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(TMP / "list.txt"), "-c", "copy", str(TMP / "timeline.mp4")])

def to_out(t):
    """clip time -> output time (None if that moment was cut out)."""
    for (os_, a, win, v) in segs:
        if a - 0.05 <= t <= a + win + 0.5: return os_ + (min(t, a + win) - a) / v
    return None

# ---------- 3. events -> output time ----------
ev = []
for E in events:
    if E["type"] == "burst": E = {**E, "type": "shake"}
    to = to_out(E["t"])
    if to is None or to > dv - 0.5: continue
    ev.append({**E, "to": round(to, 2)})
print("effects:", [(e["type"], e["to"]) for e in ev], flush=True)
for i, (os_, a, win, v) in enumerate(segs): print(f"  line {i}: clip {a:.1f}-{a+win:.1f}s at {v:.2f}x  -> out {os_:.1f}s", flush=True)

def to_src(t):
    for (os_, a, win, v) in segs:
        if os_ <= t < os_ + win / v + 0.01: return a + (t - os_) * v
    return None
cen = plan.get("cen", [])
def focus_at(ts):
    if not cen or ts is None: return 0.5, 0.45
    c = min(cen, key=lambda r: abs(r[0] - ts)); return c[1], c[2]

# ---------- 4. captions: one word at a time ----------
# exact timing: we know where each line's speech starts/ends (silence trimmed), so spread its words over that span by letter count.
# (speech-recognition word starts run late and drifted, which made the captions lag.)
words = []
for i, tx in enumerate(texts):
    dur_i = len(parts[i]) / VSR; sp0 = Ls[i] + Ld[i] - dur_i
    if i == len(texts) - 1: sp0 -= TAIL   # Ld of the last part includes the tail
    ws = tx.split()
    if not ws: continue
    wt = [len(re.sub(r"\W", "", w_)) + 2 + (3 if w_[-1:] in ",.!?" else 0) for w_ in ws]
    tot = sum(wt); acc = 0.0
    for w_, k in zip(ws, wt):
        words.append([w_, max(sp0 + dur_i * acc / tot - 0.04, 0), 0]); acc += k
for i in range(len(words)):
    words[i][2] = words[i + 1][1] if i + 1 < len(words) else dv + 0.3
    words[i][2] = max(words[i][2], words[i][1] + 0.12)
def clean(w): return re.sub(r"[^\w'%#?!]", "", w).lower()
cta_start = next((w_[1] for w_ in words if clean(w_[0]) in ("hit", "rate") and w_[1] > dv * 0.6), dv) if CTA else dv
# rhythm: a hard punch-in on a key word about every 2s (alternating 1.25x / 1.4x), aimed at where the action is
last_t = -9; flip_ = 0
for w_ in words:
    t_ = clean(w_[0]); st_ = w_[1]
    if plan.get("rhythm") is False or len(t_) < 5 or t_ in STOP or st_ < 0.5 or st_ > cta_start - 0.6: continue
    if st_ - last_t < 1.7 or any(abs(st_ - e_["to"]) < 0.9 for e_ in ev): continue
    fx_, fy_ = focus_at(to_src(st_))
    ev.append({"type": "punch", "t": 0, "to": round(st_, 2), "focus": [fx_, fy_], "zoom": 1.25 if flip_ % 2 == 0 else 1.4, "dur": 0.85, "rhythm": True})
    last_t = st_; flip_ += 1
ev.sort(key=lambda e_: e_["to"])
print("effects (with rhythm punches):", [(e_["type"], e_["to"]) for e_ in ev], flush=True)
def ass_t(t):
    t = max(t, 0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Default,Impact,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,5,2,2,60,60,380,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
pop = r"\fscx86\fscy86\t(0,70,\fscx100\fscy100)"
BS = chr(92); chunks = []; cur = []
for w_ in words:
    if not clean(w_[0]): continue
    cur.append(w_)
    if len(cur) >= 3 or w_[0][-1:] in ",.!?:;" or sum(len(x[0]) for x in cur) >= 14: chunks.append(cur); cur = []
if cur: chunks.append(cur)
asl = []; ci = 0; ACC = plan.get("acc") or [CYAN, YELLOW, GREEN, YELLOW]
for ck, ch in enumerate(chunks):
    st = ch[0][1]; en = chunks[ck + 1][0][1] if ck + 1 < len(chunks) else ch[-1][2]
    en = max(en, st + 0.25)
    big = max(range(len(ch)), key=lambda q_: len(clean(ch[q_][0])) - (4 if clean(ch[q_][0]) in STOP else 0) - (3 if clean(ch[q_][0]) in ("is","a","he","it","in","to","of","at","an","be","and","the","then","that","has","his") else 0)); acc = ACC[ci % len(ACC)]; ci += 1
    txt = " ".join(("{"+BS+"1c&H"+(acc if q_ == big else WHITE)+"&}") + clean(w2[0]).upper() for q_, w2 in enumerate(ch))
    asl.append(f"Dialogue: 1,{ass_t(st)},{ass_t(en)},Default,,0,0,0,,{{{pop}}}{txt}")
shutil.copy(r"C:\Windows\Fonts\impact.ttf", TMP / "impact.ttf")
(TMP / "cap.ass").write_text(head + chr(10).join(asl) + chr(10), encoding="utf-8")

# ---------- 5. images ----------
def font(sz, f=r"C:\Windows\Fonts\arialbd.ttf"): return ImageFont.truetype(f, sz)
CS = 900
Image.new("L", (CS, CS), 0); m_ = Image.new("L", (CS, CS), 0); ImageDraw.Draw(m_).ellipse([6, 6, CS - 6, CS - 6], fill=255); m_.save(TMP / "mask.png")
r_ = Image.new("RGBA", (CS, CS), (0, 0, 0, 0)); ImageDraw.Draw(r_).ellipse([3, 3, CS - 3, CS - 3], outline=(35, 35, 35, 255), width=5); r_.save(TMP / "ring.png")
BS = 600
_yy, _xx = np.mgrid[0:H // 4, 0:W // 4]; _d = np.sqrt(((_xx - W / 8) / (W / 8)) ** 2 + ((_yy - H / 8) / (H / 8)) ** 2)
_a = np.clip((_d - 0.75) / 0.7, 0, 1) ** 1.5 * 175
_v = np.zeros((H // 4, W // 4, 4), np.uint8); _v[..., 0] = 235; _v[..., 1] = 10; _v[..., 2] = 20; _v[..., 3] = _a.astype(np.uint8)
Image.fromarray(_v, "RGBA").resize((W, H), Image.BILINEAR).save(TMP / "vig.png")
def make_burst(text, path):
    im = Image.new("RGBA", (BS, BS), (0, 0, 0, 0)); d = ImageDraw.Draw(im); pts = []
    for i in range(24):
        r = BS * 0.47 if i % 2 == 0 else BS * 0.24; a = math.pi * 2 * i / 24 - math.pi / 2
        pts.append((BS / 2 + r * math.cos(a), BS / 2 + r * math.sin(a)))
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(30, 30, 30, 255))
    sz = 170 if len(text) <= 4 else (140 if len(text) <= 5 else 110); bf = font(sz); bw_ = d.textlength(text, font=bf)
    d.text((BS / 2 - bw_ / 2, BS / 2 - sz * 0.58), text, font=bf, fill=(225, 30, 40, 255), stroke_width=8, stroke_fill=(20, 20, 20, 255)); im.save(path)

def make_text(text, path, size=120, fill=(255, 255, 255), rot=0):
    f_ = font(size, r"C:\Windows\Fonts\impact.ttf"); tmp = Image.new("RGBA", (10, 10)); dd = ImageDraw.Draw(tmp)
    lines_ = text.split("|"); wmax = max(int(dd.textlength(l_, font=f_)) for l_ in lines_) + 40; hh = int(size * 1.25) * len(lines_) + 30
    im = Image.new("RGBA", (wmax, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k_, l_ in enumerate(lines_):
        tw = d.textlength(l_, font=f_); d.text(((wmax - tw) / 2, 10 + k_ * size * 1.25), l_, font=f_, fill=fill + (255,), stroke_width=max(6, size // 14), stroke_fill=(0, 0, 0, 255))
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    im.save(path)

def sub_img(path, done):
    cw, chh = 560, 330
    c = Image.new("RGBA", (cw, chh), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    cx, cy = cw // 2, 95; ph = 76; gap = 10
    red = (222, 28, 38, 255); gray = (58, 58, 60, 245)
    lw, sw_, bw = 84, 250, 84; x0 = cx - (lw + sw_ + bw + 2 * gap) // 2; y0 = cy - ph // 2
    for xa, wa in ((x0, lw), (x0 + lw + gap, sw_), (x0 + lw + gap + sw_ + gap, bw)): d.rounded_rectangle([xa, y0, xa + wa, y0 + ph], 14, fill=red if done else gray)
    xs = x0 + lw + gap; xb = xs + sw_ + gap
    tx, ty = x0 + 24, y0 + 18
    d.rounded_rectangle([tx, ty + 16, tx + 9, ty + 38], 2, fill="white")
    d.rounded_rectangle([tx + 12, ty + 14, tx + 38, ty + 38], 6, fill="white"); d.polygon([(tx + 18, ty + 15), (tx + 25, ty), (tx + 31, ty + 3), (tx + 29, ty + 15)], fill="white")
    t = "SUBSCRIBED" if done else "SUBSCRIBE"; f = font(30); tw = d.textlength(t, font=f)
    d.text((xs + (sw_ - tw) / 2, y0 + 20), t, font=f, fill="white")
    bx, by = xb + bw // 2, cy
    d.pieslice([bx - 14, by - 18, bx + 14, by + 8], 180, 360, fill="white"); d.rectangle([bx - 14, by - 5, bx + 14, by + 8], fill="white"); d.ellipse([bx - 5, by + 8, bx + 5, by + 17], fill="white")
    px, py = (xs + sw_ // 2 + 6, cy + 14) if done else (xs + sw_ + 40, cy + 85)
    if done: d.ellipse([px - 26, py - 26, px + 26, py + 26], outline=(255, 255, 255, 220), width=4)
    S = 2.4; arrow = [(0, 0), (0, 34), (8, 26), (14, 40), (20, 37), (14, 24), (25, 24)]
    d.polygon([(px + 3 + x * S, py + 3 + y * S) for x, y in arrow], fill=(0, 0, 0, 110))
    d.polygon([(px + x * S, py + y * S) for x, y in arrow], fill="white", outline="black", width=3)
    k = 1.8; c = c.resize((int(cw * k), int(chh * k)), Image.LANCZOS)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.paste(c, ((W - c.width) // 2, 700 - int(cy * k)), c); im.save(path)
sub_img(TMP / "sub0.png", False); sub_img(TMP / "sub1.png", True)
sub_t = next((w_[1] for w_ in words if clean(w_[0]) == "subscribe" and w_[1] > dv * 0.6), cta_start + 0.2) if CTA_MODE == "meow" else None

# ---------- 6. sfx ----------
SR = 44100
def rd_wav(n):
    mp = next((q_ for q_ in (ROOT / "assets" / "memes" / f"{n}.wav", ROOT / "assets" / f"{n}.wav") if q_.exists()), ROOT / "assets" / f"sfx_{n}.wav")
    with wave.open(str(mp)) as w: return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
if not (ROOT / "assets" / "sfx_meow.wav").exists(): run([sys.executable, str(ROOT / "sfx.py")])
track = np.zeros(int((T + 1) * SR), np.float32)
def put(n, t, g=1.0):
    x = rd_wav(n) * g; i = max(int(t * SR), 0); track[i:i + len(x)] += x[:len(track) - i]
put("drop", 0.1, 0.5)
TRD = 0.2; TR_TYPES = plan.get("trs") or ["WhipPan", "ZoomInOut", "TangentMotionBlur", "WhipSpin", "StretchSlide", "LensPush", "DirectionalWarp"]; SW = plan.get("sw") or [11, 12, 10, 6, 1, 5, 7, 4]; TR_D = {"WhipPan": 0.2, "ZoomInOut": 0.22, "TangentMotionBlur": 0.2, "WhipSpin": 0.22, "StretchSlide": 0.2, "LensPush": 0.2, "DirectionalWarp": 0.2}
trs = []; _tp = -9.0
for (os_, a, win, v) in segs:
    if os_ - _tp >= 3.0 and os_ < dv - 1.0 and not any(abs(os_ - e_["to"]) < 0.5 and e_["type"] in ("flash", "text") for e_ in ev):
        trs.append((round(os_, 2), TR_TYPES[len(trs) % len(TR_TYPES)])); _tp = os_
for i_, (t0_, ty_) in enumerate(trs): put(f"swish_{SW[i_ % len(SW)]}", max(t0_ - 0.12, 0), 0.8)
print("transitions:", trs, flush=True)
import gl_trans
gl_trans.apply(TMP / "timeline.mp4", TMP / "timeline_tr.mp4", [(t_, n_, TR_D[n_]) for t_, n_ in trs])
for e in ev:
    to = e["to"]
    if e["type"] == "punch": put("whoosh", to - 0.15, 0.6); put("pop", to, 0.5)
    elif e["type"] == "circle": put("whoosh", to - 0.15, 0.6); put("pop", to, 0.4)
    elif e["type"] == "burst": put("pop", to, 0.6); put("hit", to, 0.6)
    elif e["type"] == "shake": put("hit", to, 0.9)
    elif e["type"] == "freeze": put("scratch", to, 0.6)
    elif e["type"] == "damage": put("hit", to, 0.9); put("drop", to, 0.35)
    elif e["type"] == "flash": put("hit", to, 0.6)
    elif e["type"] == "sfx": put(e.get("name", "hit"), to, e.get("g", 0.9))
    elif e["type"] == "glitch": put("click", to, 0.8); put("whoosh", to, 0.3)
meow_t = next((w_[1] for w_ in words if clean(w_[0]) == "meow"), None) if CTA_MODE == "meow" else None
if meow_t: put("meow", meow_t, 0.9)
if sub_t is not None: put("click", sub_t + 1.15, 0.8); put("pop", sub_t + 1.2, 0.6)
with wave.open(str(TMP / "sfx.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(track, -1, 1) * 32767).astype("<i2").tobytes())

# ---------- 7. video graph ----------
music = ROOT / "assets" / "music_loop.wav"
if not music.exists(): run([sys.executable, str(ROOT / "music.py")])
cmd = [FFMPEG, "-y", "-v", "error", "-i", str(TMP / "timeline_tr.mp4"), "-i", str(vwav), "-i", str(TMP / "sfx.wav"), "-stream_loop", "-1", "-i", str(music)]
nin = 4
def add_img(p):
    global nin
    cmd.extend(["-framerate", "30", "-loop", "1", "-t", str(T), "-i", str(TMP / p)]); nin += 1; return nin - 1
sub0, sub1 = (add_img("sub0.png"), add_img("sub1.png")) if sub_t is not None else (None, None)
# base: slow push-in + handheld sway + shake on impacts
shk = []   # screen shake removed (made viewers dizzy); shake events keep only their hit sound
sx = "+".join(f"26*sin(70*t)*between(t,{e['to']},{e['to']+0.45})*(1-(t-{e['to']})/0.45)" for e in shk) or "0"
sy = "+".join(f"20*sin(83*t+1)*between(t,{e['to']},{e['to']+0.45})*(1-(t-{e['to']})/0.45)" for e in shk) or "0"
Z = f"1.07+0.12*t/{T}+0.12*max(0,t-{T-3.5})/3.5"
fc = ("[0:v]eq=saturation=1.12:gamma_r=1.04:gamma_b=0.95[v0]" if plan.get("grade") == "warm" else ("[0:v]eq=saturation=0.9:gamma_r=0.95:gamma_b=1.06[v0]" if plan.get("grade") == "cold" else "[0:v]null[v0]"))   # flat, still picture: no sway, no zoom creep
last = "v0"; k = 0
def nxt():
    global k; k += 1; return f"s{k}"
circ_n = sum(1 for e in ev if e["type"] == "circle")
if circ_n:
    mi = add_img("mask.png"); ri = add_img("ring.png")
    fc += f";[{mi}:v]split={circ_n}" + "".join(f"[mk{j}]" for j in range(circ_n)) + f";[{ri}:v]split={circ_n}" + "".join(f"[rg{j}]" for j in range(circ_n))
cj = 0
for e in sorted(ev, key=lambda e_: e_["type"] == "text"):   # text goes on last so punch-ins never cover it
    to, ty = e["to"], e["type"]
    if ty == "circle" and cen and not e.get("exact"):
        mx, my = focus_at(e["t"]); e["focus"] = [0.5 * e["focus"][0] + 0.5 * mx, 0.5 * e["focus"][1] + 0.5 * my]
    cfx, cfy = canvas(*e.get("focus", [0.5, 0.4]))
    if ty == "punch":
        z = e["zoom"]; cwid = int(W / z) // 2 * 2; chei = int(H / z) // 2 * 2
        px_ = int(min(max(cfx * W - cwid / 2, 0), W - cwid)); py_ = int(min(max(cfy * H - chei / 2, 0), H - chei))
        a, b = nxt(), nxt()
        fc += (f";[{last}]split[{a}p][{a}q];[{a}q]crop={cwid}:{chei}:{px_}:{py_},scale={W}:{H}[{a}z];[{a}p][{a}z]overlay=enable='between(t,{to-0.03},{to+e['dur']})'[{b}]")
        last = b
    elif ty == "circle":
        src_ = int(e.get("src", 540)) // 2 * 2; r = src_ // 2; dd = int(e.get("d", CS)) // 2 * 2
        ccx = int(min(max(cfx * W - r, 0), W - 2 * r)); ccy = int(min(max(cfy * H - r, 0), H - 2 * r))
        x = 330 if cfx < 0.5 else -140; y = 120 if cfy > 0.3 else 760
        if e.get("pos"): x, y = int(e["pos"][0]), int(e["pos"][1])
        if e.get("inplace"): x, y = int(cfx * W - dd / 2), int(cfy * H - dd / 2)
        a, b = nxt(), nxt()
        fc += (f";[{last}]split[{a}p][{a}q];[{a}q]crop={src_}:{src_}:{ccx}:{ccy},scale={CS}:{CS},format=rgba[{a}m];[{a}m][mk{cj}]alphamerge[{a}c0];[{a}c0]scale={dd}:{dd}[{a}c];[rg{cj}]scale={dd}:{dd}[{a}r]"
               f";[{a}p][{a}c]overlay={x}:{y}:enable='between(t,{to},{to+e['dur']})'[{a}o];[{a}o][{a}r]overlay={x}:{y}:enable='between(t,{to},{to+e['dur']})'[{b}]")
        last = b; cj += 1
    elif ty == "burst":
        make_burst(e["text"], TMP / f"b{len(str(fc))}.png"); bi = add_img(f"b{len(str(fc))}.png")
        bx = 40 if cfx > 0.5 else W - BS - 40; by = 200
        b = nxt(); fc += f";[{last}][{bi}:v]overlay={bx}:{by}:enable='between(t,{to},{to+0.7})'[{b}]"; last = b
    elif ty == "text":
        tn = f"tx{k}_{nin}.png"; make_text(e["text"], TMP / tn, int(e.get("size", 120)), tuple(e.get("fill", [255, 255, 255])), e.get("rot", 0))
        ti = add_img(tn); bx, by = e.get("pos", ["c", 1560]); bx = "(W-w)/2" if bx == "c" else bx; d_ = e.get("dur", 1.2)
        b = nxt(); fc += f";[{last}][{ti}:v]overlay=x={bx}:y='{by}+90*pow(max(0,1-(t-{to})/0.18),2)':enable='between(t,{to},{to+d_})'[{b}]"; last = b
    elif ty == "push":
        nc_ = next((o_ for (o_, *_r) in segs if o_ > to + 0.4), to + 2.0); dur_ = e.get("dur") or (nc_ - to); z1 = e.get("zoom", 1.25); a, b = nxt(), nxt()
        zf = f"(1+{z1 - 1}*min(max((t-{to})/{dur_},0),1))"
        fc += (f";[{last}]split[{a}p][{a}q];[{a}q]scale=w='trunc({W}*{zf}/2)*2':h='trunc({H}*{zf}/2)*2':eval=frame,crop={W}:{H}:x='min(max({cfx}*iw-{W}/2,0),iw-{W})':y='min(max({cfy}*ih-{H}/2,0),ih-{H})'[{a}z]"
               f";[{a}p][{a}z]overlay=enable='between(t,{to},{to + dur_})'[{b}]")
        last = b
    elif ty == "spot":
        nc_ = next((o_ for (o_, *_r) in segs if o_ > to + 0.4), to + 2.0); dur_ = e.get("dur") or (nc_ - to); b = nxt(); si = add_img(f"spot{k}.png")
        r1 = e.get("r", 260); yy, xx = np.mgrid[0:H // 4, 0:W // 4]; dd_ = np.sqrt((xx * 4 - cfx * W) ** 2 + (yy * 4 - cfy * H) ** 2)
        al = (np.clip((dd_ - r1) / 320, 0, 1) * 185).astype(np.uint8); im_ = np.zeros((H // 4, W // 4, 4), np.uint8); im_[..., 3] = al
        Image.fromarray(im_, "RGBA").resize((W, H), Image.BILINEAR).save(TMP / f"spot{k}.png")
        fc += f";[{last}][{si}:v]overlay=0:0:enable='between(t,{to},{to + dur_})'[{b}]"; last = b
    elif ty == "freeze":
        a, b = nxt(), nxt(); dur_ = e.get("dur", 0.8)
        fc += (f";[{last}]split[{a}p][{a}q];[{a}q]trim=start={to}:end={to + 0.034},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={dur_},hue=s=0,eq=contrast=1.25,setpts=PTS+{to}/TB[{a}f]"
               f";[{a}p][{a}f]overlay=enable='between(t,{to},{to + dur_})':eof_action=pass[{b}]")
        last = b
    elif ty == "damage":
        dur_ = e.get("dur", 0.4); a, b = nxt(), nxt(); vg = add_img("vig.png")
        sxx = f"34*sin(95*t)*(1-(t-{to})/{dur_})"; syy = f"26*sin(113*t+1)*(1-(t-{to})/{dur_})"
        fc += (f";[{last}]split[{a}p][{a}q];[{a}q]scale=1166:2074,crop={W}:{H}:x='43+{sxx}':y='77+{syy}',rgbashift=rh=16:bh=-16:gv=6[{a}s]"
               f";[{a}p][{a}s]overlay=enable='between(t,{to},{to+dur_})'[{a}o];[{a}o][{vg}:v]overlay=0:0:enable='between(t,{to},{to+dur_ + 0.15})'[{b}]")
        last = b
    elif ty == "flash":
        b = nxt(); fc += f";[{last}]drawbox=x=0:y=0:w=iw:h=ih:color=white@0.6:t=fill:enable='between(t,{to},{to+0.08})'[{b}]"; last = b
    elif ty == "glitch":
        b = nxt(); fc += f";[{last}]rgbashift=rh=12:bh=-12:gv=5:enable='between(t,{to},{to+0.35})'[{b}]"; last = b
if sub_t is not None:
    fc += (f";[{last}][{sub0}:v]overlay=0:0:enable='between(t,{sub_t},{sub_t+1.15})'[u1];[u1][{sub1}:v]overlay=0:0:enable='between(t,{sub_t+1.15},{sub_t+2.6})'[u2]")
    last = "u2"
for i_, (t0_, ty_) in enumerate([]):   # old ffmpeg transitions replaced by gl_trans
    d_ = TRD; o_ = f"tr{i_}"; w_ = f"between(t,{t0_},{t0_ + d_})"; pr = f"((t-{t0_})/{d_})"; bgf = "boxblur=30:3,eq=brightness=-0.35"
    if ty_ in ("slide_r", "slide_l"):
        sg = "" if ty_ == "slide_r" else "-"
        fc += f";[{last}]split[{o_}a][{o_}b];[{o_}b]{bgf}[{o_}g];[{o_}g][{o_}a]overlay=x='if({w_},{sg}W*pow(1-{pr},3),0)':y=0:eval=frame[{o_}]"
    elif ty_ == "zoom":
        zf = f"(1+0.5*{w_}*pow(1-{pr},2))"
        fc += f";[{last}]scale=w='trunc({W}*{zf}/2)*2':h='trunc({H}*{zf}/2)*2':eval=frame,crop={W}:{H},gblur=sigma=10:enable='between(t,{t0_},{t0_ + d_ * 0.7})'[{o_}]"
    elif ty_ == "flip":
        fc += (f";[{last}]split[{o_}a][{o_}b];[{o_}b]{bgf}[{o_}g];[{o_}a]scale=w='if({w_},max(2,trunc({W}*pow({pr},0.7)/2)*2),{W})':h={H}:eval=frame[{o_}f]"
               f";[{o_}g][{o_}f]overlay=x='(W-w)/2':y=0:eval=frame[{o_}]")
    elif ty_ == "spin":
        fc += f";[{last}]rotate=a='{w_}*0.5*pow(1-{pr},2)':ow=iw:oh=ih:fillcolor=black[{o_}]"
    else:
        fc += f";[{last}]rgbashift=rh=28:bh=-28:gv=10:enable='between(t,{t0_},{t0_ + 0.3})',noise=alls=45:allf=t:enable='between(t,{t0_},{t0_ + 0.3})'[{o_}]"
    last = o_
fc += f";[{last}]ass=cap.ass:fontsdir=.,fade=t=out:st={T-0.5}:d=0.5,format=yuv420p[vout]"
fc += (f";[1:a]aresample=44100,aformat=channel_layouts=stereo,highpass=f=90,equalizer=f=3000:t=q:w=1.2:g=3,acompressor=threshold=0.1:ratio=3:attack=5:release=80,volume=1.15,asplit[va][vs]"
       f";[2:a]aresample=44100,aformat=channel_layouts=stereo,volume=1.2[sa]"
       f";[3:a]aformat=channel_layouts=stereo,volume={plan.get("music", 0.15)}[ma0];[ma0][vs]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=250[ma]"
       f";[va][sa][ma]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,loudnorm=I=-11:TP=-1:LRA=9[aout]")
name = f"commentary_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M')}"
final = OUT / f"{name}.mp4"
cmd += ["-filter_complex", fc, "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-t", str(T), str(final)]
subprocess.run(cmd, check=True, cwd=TMP)
print("rendered", final)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)], capture_output=True, text=True).stdout.strip())
sheet = OUT / f"{name}_preview.jpg"
subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(final), "-vf", "fps=2,scale=200:-1,tile=8x5", "-frames:v", "1", str(sheet)], check=True)
subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", "1", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(OUT / f"{name}_thumb.jpg")], check=True)
print("preview:", sheet, "| duration", round(dur, 1), "s")
