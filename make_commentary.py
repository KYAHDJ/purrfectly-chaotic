"""Commentary Short, copied from the old CapCut videos (measured frame by frame):
ONE clip + fast hype voice (~4 words/sec), ONE-WORD-AT-A-TIME colored captions, slow zoom ramp + big face zoom spikes,
big circle magnifiers, comic burst sticker, RGB glitch + white flash, red posterize moment, whoosh/hit sfx,
subscribe-button animation, loud mastering, fade out.
Reads plan_c.json: {"id","script","focus":[x,y],"flip":false}. Output: output/commentary_<time>.mp4 (+thumb, preview). No uploading."""
import subprocess, pathlib, json, sys, datetime, shutil, re, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).parent.resolve(); sys.path.insert(0, str(ROOT))
OUT = ROOT / "output"; OUT.mkdir(exist_ok=True)
TMP = OUT / "_tmpc"; TMP.mkdir(exist_ok=True)
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
W, H = 1080, 1920
SPEED = float(os.environ.get("VSPEED", "1.3"))  # VoiceStudio speed; ~4 words/sec like the old videos
CTA = "Hit subscribe and click the like button to watch it turn into a meow emoji."
STOP = set("this that with have they their there what when then than from into just like your about would could really every very over only even some more most been being were also while these those and the but for are was his her its him she you can not".split())
CYAN, YELLOW, GREEN = "FFFF00", "00E6FF", "40FF40"  # ASS BGR
CYCLE = [CYAN, YELLOW, GREEN, CYAN, YELLOW]

import voice, asr_util
plan = json.loads((ROOT / "plan_c.json").read_text(encoding="utf-8"))
src = ROOT / "clips" / f"rn_{plan['id']}.mp4"
script = plan["script"].strip()
fx, fy = (plan.get("focus") or [0.5, 0.4])
flip = bool(plan.get("flip", False))

# ---------- voice ----------
if os.environ.get("VOICE_FALLBACK") != "sapi": voice.ensure_backend()
full = script + " " + CTA
vwav = TMP / "voice.wav"
# chunked voice: one TTS call per sentence, silence trimmed, tight gaps, small pitch lift on "!" lines, 0.4s beat before the reboot line
ATEMPO = float(os.environ.get("VATEMPO", "1.85"))  # speed up AFTER generating (stays clear, like the old ElevenLabs workflow)
kw0 = plan.get("climax_word", "boom")
chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+", script) if c.strip()] + [CTA]
VSR = 24000; parts = []
for ci_, ch in enumerate(chunks):
    raw = TMP / f"vc{ci_}.wav"; fin = TMP / f"vc{ci_}f.wav"
    voice.tts(ch, raw, speed=SPEED)
    pitch = 1.06 if ch.endswith("!") else (1.03 if ch.endswith("?") else 1.0)
    trim = "silenceremove=start_periods=1:start_threshold=-45dB:detection=peak,areverse,silenceremove=start_periods=1:start_threshold=-45dB:detection=peak,areverse"
    af = f"asetrate={int(VSR*pitch)},aresample={VSR},atempo={ATEMPO/pitch:.3f},{trim}"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(raw), "-af", af, "-ac", "1", "-ar", str(VSR), str(fin)], check=True)
    with wave.open(str(fin)) as w_: parts.append((ch, np.frombuffer(w_.readframes(w_.getnframes()), "<i2")))
seq = []
for k_, (ch, x) in enumerate(parts):
    if k_:
        first = re.sub(r"[^\w]", "", ch.split()[0]).lower()
        gap = 0.4 if first == kw0 else (0.16 if ch.startswith("Hit subscribe") else 0.2)
        seq.append(np.zeros(int(VSR * gap), "<i2"))
    seq.append(x)
allv = np.concatenate(seq)
with wave.open(str(vwav), "wb") as w_:
    w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(VSR); w_.writeframes(allv.astype("<i2").tobytes())
dv = len(allv) / VSR
asr = asr_util.words(vwav)
T = round(dv + 0.5, 2)
sw = full.split()
if asr and abs(len(sw) - len(asr)) / len(sw) <= 0.25:
    words = []
    for i, w_ in enumerate(sw):
        j = min(int(i * len(asr) / len(sw)), len(asr) - 1)
        words.append([w_, asr[j][1], 0])
    for i in range(len(words)):
        words[i][2] = words[i + 1][1] if i + 1 < len(words) else dv + 0.3
        words[i][2] = max(words[i][2], words[i][1] + 0.12)
else:
    words = [[a[0], a[1], a[2]] for a in asr]
for i in range(1, len(words)): words[i][1] = max(words[i][1], words[i - 1][1] + 0.11)
for i in range(len(words) - 1): words[i][2] = words[i + 1][1]
print(f"voice {dv:.1f}s, {len(words)} words, {len(words)/dv:.2f} words/s")

def clean(w): return re.sub(r"[^\w'%#?!]", "", w).lower()
cta_start = next((w_[1] for w_ in words if clean(w_[0]) == "hit" and w_[1] > dv * 0.6), dv)

# ---------- captions: one word at a time, colors cycle on content words ----------
def ass_t(t):
    t = max(t, 0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Default,Segoe UI Black,104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,8,2,2,60,60,460,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
pop = r"\fscx72\fscy72\t(0,80,\fscx100\fscy100)"
lines = []; ci = 0; kw_times = []
for w_ in words:
    t = clean(w_[0])
    if not t: continue
    st, en = w_[1], w_[2]
    if len(t) >= 4 and t not in STOP and st < cta_start:
        col = CYCLE[ci % len(CYCLE)]; ci += 1
        if len(t) >= 6: kw_times.append(st)
        lines.append(f"Dialogue: 0,{ass_t(st)},{ass_t(en)},Default,,0,0,0,,{{\\bord16\\3c&H{col}&\\blur14\\1a&HFF&{pop}}}{t}")
        lines.append(f"Dialogue: 1,{ass_t(st)},{ass_t(en)},Default,,0,0,0,,{{\\1c&H{col}&{pop}}}{t}")
    else:
        lines.append(f"Dialogue: 1,{ass_t(st)},{ass_t(en)},Default,,0,0,0,,{{{pop}}}{t}")
shutil.copy(r"C:\Windows\Fonts\seguibl.ttf", TMP / "seguibl.ttf")
(TMP / "cap.ass").write_text(head + "\n".join(lines) + "\n", encoding="utf-8")

# ---------- beats ----------
beats = [0.2]
for t in kw_times:
    if t - beats[-1] >= 1.3 and t < cta_start - 0.4: beats.append(round(float(t), 2))
punch = list(beats)
for _ in range(40):  # fill gaps so a zoom punch lands about every 2s
    pts_ = sorted(punch + [cta_start - 0.4]); gaps = [(b - a, a) for a, b in zip(pts_, pts_[1:]) if b - a > 2.3]
    if not gaps: break
    punch.append(round(gaps[0][1] + 1.9, 2))
punch = sorted(punch)
def B(i): return beats[min(i, len(beats) - 1)]
K = len(beats)
spike_t = B(2) if K > 2 else B(1)
circ = [B(1)] + ([B(5) if K > 5 else B(4)] if K > 4 else [])
burst_t = B(3) if K > 3 else spike_t
kw = plan.get("climax_word", "boom")
red_t = next((w_[1] for w_ in words if clean(w_[0]) == kw and w_[1] > dv * 0.3 and w_[1] < cta_start - 0.5), beats[-1] if K > 2 else None)
if red_t is not None:  # keep the magnifier off the reboot moment
    circ = [c for c in circ if abs(c - red_t) > 0.6]
    after = [b for b in beats if b > red_t + 1.0]
    if after and len(circ) < 2: circ.append(after[0])
print("beats", beats, "| spike", spike_t, "| circles", circ, "| burst", burst_t, "| red", red_t)

# ---------- images ----------
def font(sz, f=r"C:\Windows\Fonts\arialbd.ttf"): return ImageFont.truetype(f, sz)
CS = 900
mask = Image.new("L", (CS, CS), 0); ImageDraw.Draw(mask).ellipse([6, 6, CS - 6, CS - 6], fill=255); mask.save(TMP / "mask.png")
ring = Image.new("RGBA", (CS, CS), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([3, 3, CS - 3, CS - 3], outline=(35, 35, 35, 255), width=5); ring.save(TMP / "ring.png")

# comic burst sticker: white spiky star + two red slanted bars
import math
BS = 620; burst = Image.new("RGBA", (BS, BS), (0, 0, 0, 0)); bd = ImageDraw.Draw(burst)
pts = []
for i in range(24):
    r = BS * 0.47 if i % 2 == 0 else BS * 0.24; a = math.pi * 2 * i / 24 - math.pi / 2
    pts.append((BS / 2 + r * math.cos(a), BS / 2 + r * math.sin(a)))
bd.polygon(pts, fill=(255, 255, 255, 255), outline=(30, 30, 30, 255))
bf = font(170); bt = plan.get("burst_text", "WOW!"); bw_ = bd.textlength(bt, font=bf)
bd.text((BS / 2 - bw_ / 2, BS / 2 - 100), bt, font=bf, fill=(225, 30, 40, 255), stroke_width=8, stroke_fill=(20, 20, 20, 255))
burst.save(TMP / "burst.png")

def sub_img(path, done):
    """Like | SUBSCRIBE | bell pills + mouse cursor, drawn small then scaled up big; red + click ring when clicked."""
    cw, ch = 560, 330
    c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    cx, cy = cw // 2, 95; ph = 76; gap = 10
    red = (222, 28, 38, 255); gray = (58, 58, 60, 245)
    lw, sw_, bw = 84, 250, 84; x0 = cx - (lw + sw_ + bw + 2 * gap) // 2; y0 = cy - ph // 2
    d.rounded_rectangle([x0, y0, x0 + lw, y0 + ph], 14, fill=red if done else gray)
    xs = x0 + lw + gap; d.rounded_rectangle([xs, y0, xs + sw_, y0 + ph], 14, fill=red if done else gray)
    xb = xs + sw_ + gap; d.rounded_rectangle([xb, y0, xb + bw, y0 + ph], 14, fill=red if done else gray)
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
    k = 1.8; c = c.resize((int(cw * k), int(ch * k)), Image.LANCZOS)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.paste(c, ((W - c.width) // 2, 700 - int(cy * k)), c)
    im.save(path)
sub_img(TMP / "sub0.png", False); sub_img(TMP / "sub1.png", True)
sub_t = next((w_[1] for w_ in words if clean(w_[0]) == "subscribe" and w_[1] > dv * 0.6), cta_start + 0.2)

# ---------- sfx track ----------
SR = 44100
def rd_wav(n):
    with wave.open(str(ROOT / "assets" / f"sfx_{n}.wav")) as w: return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
if not (ROOT / "assets" / "sfx_whoosh.wav").exists(): subprocess.run([sys.executable, str(ROOT / "sfx.py")], check=True)
track = np.zeros(int((T + 1) * SR), np.float32)
def put(n, t, g=1.0):
    x = rd_wav(n) * g; i = max(int(t * SR), 0); track[i:i + len(x)] += x[:len(track) - i]
for tb in beats: put("whoosh", tb - 0.18, 0.5); put("pop", tb, 0.45)
put("hit", spike_t, 0.7); put("hit", burst_t, 0.7); put("whoosh", spike_t - 0.2, 0.7)
for c in circ: put("whoosh", c - 0.15, 0.6)
put("drop", 0.15, 0.8)
if red_t is not None: put("hit", red_t - 0.05, 1.0)  # jaw slam

for tp in punch:
    if tp not in beats: put("pop", tp, 0.3)
meow_t = next((w_[1] for w_ in words if clean(w_[0]) == "meow"), None)
if meow_t: put("meow", meow_t, 0.9)
put("click", sub_t + 1.15, 0.8); put("pop", sub_t + 1.2, 0.6)
with wave.open(str(TMP / "sfx.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(track, -1, 1) * 32767).astype("<i2").tobytes())

# ---------- video graph ----------
def has_audio(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return bool(r.stdout.strip())
# zoom: slow ramp + small punch at every beat + big face spike
Z = f"1+0.10*t/{T}+" + "+".join(f"0.06*gte(t,{tb})*max(0,1-(t-{tb})/0.35)" for tb in punch) \
    + f"+0.55*between(t,{spike_t},{spike_t+1.0})*sin(PI*(t-{spike_t}))"
music = ROOT / "assets" / "music_loop.wav"
if not music.exists(): subprocess.run([sys.executable, str(ROOT / "music.py")], check=True)
def pingpong(srcp, ss, dur):
    """clip from ss, then the last 2s forward/backward repeatedly, so the end never freezes."""
    d0 = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(srcp)], capture_output=True, text=True).stdout.strip())
    t0 = max(d0 - 2.0, 0)
    base = ["-an", "-vf", "fps=30,scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
    subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", str(ss), "-i", str(srcp), *base, str(TMP / "pp_a.mp4")], check=True)
    subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", str(t0), "-i", str(srcp), *base, str(TMP / "pp_f.mp4")], check=True)
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(TMP / "pp_f.mp4"), "-vf", "reverse", *base, str(TMP / "pp_r.mp4")], check=True)
    n_ = int(dur / 2) + 3
    (TMP / "pp.txt").write_text("file 'pp_a.mp4'" + chr(10) + ("file 'pp_r.mp4'" + chr(10) + "file 'pp_f.mp4'" + chr(10)) * n_, encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(TMP / "pp.txt"), "-c", "copy", str(TMP / "pp_ext.mp4")], check=True)
    return TMP / "pp_ext.mp4"
clip_a = False
bite = plan.get("bite"); off = max(bite - red_t, 0) if (bite and red_t) else 0
pre = max(red_t - bite, 0) if (bite and red_t) else 0  # hold the first frame so the bite lands on the reboot
src_ext = pingpong(src, round(off, 2), T)
cmd = [FFMPEG, "-y", "-v", "error", "-i", str(src_ext), "-i", str(vwav), "-i", str(TMP / "sfx.wav"),
       "-stream_loop", "-1", "-i", str(music)]
for p in ("mask", "ring", "sub0", "sub1", "burst"):
    cmd += ["-framerate", "30", "-loop", "1", "-t", str(T), "-i", str(TMP / f"{p}.png")]
# inputs: 0 clip,1 voice,2 sfx,3 music,4 mask,5 ring,6 sub0,7 sub1,8 burst
if not clip_a:
    cmd += ["-f", "lavfi", "-t", str(T), "-i", "anullsrc=r=44100:cl=stereo"]
ca = "0:a" if clip_a else "9:a"
fl = "hflip," if flip else ""
cx_expr = f"min(max({fx}*iw-{W}/2+9*sin(17*t),0),iw-{W})"; cy_expr = f"min(max({fy}*ih-{H}/2+7*sin(23*t+1),0),ih-{H})"
fc = (f"[0:v]fps=30,tpad=start_mode=clone:start_duration={pre:.2f},trim=duration={T},setpts=PTS-STARTPTS,{fl}split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5[bg];"
      f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v0];"
      f"[v0]scale=w='trunc({W}*({Z})/2)*2':h='trunc({H}*({Z})/2)*2':eval=frame,crop={W}:{H}:x='{cx_expr}':y='{cy_expr}'[vz]")
last = "vz"
REBOOT = False  # red glitch / SYSTEM ERROR screen: OFF (user hates it)
if red_t is not None and REBOOT:  # red posterized moment
    fc += (f";[{last}]split[pa][pb];[pa]lutrgb=r='trunc(val/64)*64':g='trunc(val/64)*64':b='trunc(val/64)*64',colorchannelmixer=rr=1.15:gg=0.35:bb=0.35[prd]"
           f";[pb][prd]overlay=enable='between(t,{red_t},{red_t+1.3})'[pr0]"
           f";[pr0]split[qa][qb];[qa]scale=54:96:flags=neighbor,scale={W}:{H}:flags=neighbor[qp]"
           f";[qb][qp]overlay=enable='between(t,{red_t},{red_t+0.5})+between(t,{red_t+0.8},{red_t+0.95})'[pq]"
           f";[pq]rgbashift=rh=14:bh=-14:gv=6:enable='between(t,{red_t},{red_t+0.55})'[pr]")
    last = "pr"
    lines.append(rf"Dialogue: 2,{ass_t(red_t)},{ass_t(red_t+1.3)},Default,,0,0,0,,{{\an5\pos(540,760)\fs96\1c&H2020FF&\3c&HFFFFFF&\bord8}}SYSTEM ERROR\N{{\fs64}}REBOOTING...")
    (TMP / "cap.ass").write_text(head + chr(10).join(lines) + chr(10), encoding="utf-8")
if circ:  # big circle magnifier(s), 2x zoom on the face
    ccx = int(min(max(fx * W - 225, 0), W - 450)); ccy = int(min(max(fy * H - 225, 0), H - 450))
    n = len(circ)
    fc += (f";[{last}]split[cb0][cm];[cm]crop=450:450:{ccx}:{ccy},scale={CS}:{CS},format=rgba[mc];[mc][4:v]alphamerge[mcirc]"
           f";[mcirc]split={n}[mc0]" + "".join(f"[mc{k}]" for k in range(1, n)) + f";[5:v]split={n}[rg0]" + "".join(f"[rg{k}]" for k in range(1, n)))
    cur = "cb0"
    for k, c in enumerate(circ):
        x = -140 if k % 2 == 0 else 330
        fc += (f";[{cur}][mc{k}]overlay={x}:120:enable='between(t,{c},{c+1.6})'[o{k}a];[o{k}a][rg{k}]overlay={x}:120:enable='between(t,{c},{c+1.6})'[o{k}]")
        cur = f"o{k}"
    last = cur
bx = int(min(max(fx * W - BS - 10, 0), W - BS)); by = int(min(max(fy * H - BS * 0.8, 0), H - BS))
fc += (f";[{last}][8:v]overlay={bx}:{by}:enable='between(t,{burst_t},{burst_t+0.6})'[bu]"
       f";[bu]rgbashift=rh=10:bh=-10:enable='between(t,{burst_t},{burst_t+0.3})'[gl]"
       f";[gl]drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='between(t,{spike_t},{spike_t+0.07})'[fl]"
       f";[fl][6:v]overlay=0:0:enable='between(t,{sub_t},{sub_t+1.15})'[s1];[s1][7:v]overlay=0:0:enable='between(t,{sub_t+1.15},{sub_t+2.6})'[s2]"
       f";[s2]ass=cap.ass:fontsdir=.,fade=t=out:st={T-0.5}:d=0.5,format=yuv420p[vout]")
fc += (f";[1:a]adelay=120|120,aresample=44100,aformat=channel_layouts=stereo,volume=1.0[va]"
       f";[{ca}]volume=0.2,aresample=44100,aformat=channel_layouts=stereo[ka]"
       f";[2:a]aresample=44100,aformat=channel_layouts=stereo,volume=2.0[sa]"
       f";[3:a]aformat=channel_layouts=stereo,volume=0.11[ma]"
       f";[va][ka][sa][ma]amix=inputs=4:duration=longest:dropout_transition=0:normalize=0,loudnorm=I=-11:TP=-1:LRA=9[aout]")
name = f"commentary_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M')}"
final = OUT / f"{name}.mp4"
cmd += ["-filter_complex", fc, "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-t", str(T), str(final)]
subprocess.run(cmd, check=True, cwd=TMP)
print("rendered", final, "| subscribe @", round(sub_t, 1))
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)], capture_output=True, text=True).stdout.strip())
sheet = OUT / f"{name}_preview.jpg"
subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(final), "-vf", f"fps=2,scale=200:-1,tile=8x5", "-frames:v", "1", str(sheet)], check=True)
subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", "1", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(OUT / f"{name}_thumb.jpg")], check=True)
print("preview:", sheet, "| duration", round(dur, 1), "s")
