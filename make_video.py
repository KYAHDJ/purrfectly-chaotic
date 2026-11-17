"""Build the ranking Short (reference style: clip's own sound, rank list with reactions, fast 3-4s shots, no narrator).
Output: output/<name>.mp4 + thumbnail + preview sheet. No uploading."""
import subprocess, pathlib, json, sys, datetime, shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).parent.resolve()
CLIPS = ROOT / "clips"
OUT = ROOT / "output"; OUT.mkdir(exist_ok=True)
TMP = OUT / "_tmp"; TMP.mkdir(exist_ok=True)
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
W, H = 1080, 1920
PLAN = json.loads((ROOT / "plan.json").read_text(encoding="utf-8"))  # countdown order: highest rank number first
N = len(PLAN)
END = "WHICH IS YOUR #1?"

def font(size):
    for f in (r"C:\Windows\Fonts\impact.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
        if pathlib.Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()

def outlined(d, xy, text, f, fill, sw=5):
    d.text(xy, text, font=f, fill=fill, stroke_width=sw, stroke_fill=(0, 0, 0, 255))

COLS = {1: (255, 214, 0), 2: (255, 255, 255), 3: (255, 120, 40)}

def overlay(done_ranks, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    # title, centered, two lines + hook (like the reference)
    tf = font(84); hf = font(40)
    for y, parts in ((70, [("Ranking ", (255, 255, 255)), ("Funniest", (255, 214, 0))]), (165, [("Cat ", (255, 120, 40)), ("Moments", (255, 255, 255))])):
        tw = sum(d.textlength(t, font=tf) for t, _ in parts); x = (W - tw) / 2
        for t, c in parts:
            outlined(d, (x, y), t, tf, c + (255,), 6); x += d.textlength(t, font=tf)
    hk = "(Last one is insane)"
    outlined(d, ((W - d.textlength(hk, font=hf)) / 2, 268), hk, hf, (255, 255, 255, 255), 4)
    # rank list on the left
    lf = font(58); sf = font(48)
    step = 92; y0 = 380
    for i in range(N):
        rank = i + 1; y = y0 + i * step
        outlined(d, (36, y), f"{rank}.", lf, COLS.get(rank, (255, 255, 255)) + (255,), 5)
        item = next((p for p in PLAN if p["rank"] == rank), None)
        if item and rank in done_ranks:
            outlined(d, (36 + 96, y + 6), item["label"], sf, (255, 255, 255, 255), 5)
    im.save(path)

def end_overlay(path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = font(110)
    tw = d.textlength(END, font=f)
    outlined(d, ((W - tw) / 2, 1500), END, f, (255, 214, 0, 255), 8)
    im.save(path)

def has_audio(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())

segs = []
shown = set()
for n_, item in enumerate(PLAN):
    shown.add(item["rank"])
    src = CLIPS / f"rn_{item['id']}.mp4"
    ov = TMP / f"ov_{item['rank']}.png"; overlay(set(shown), ov)
    seg = TMP / f"seg_{item['rank']}.mp4"
    L = item["len"]
    cmd = [FFMPEG, "-y", "-v", "error", "-ss", str(item["start"]), "-t", str(L), "-i", str(src), "-i", str(ov)]
    idx = 2; extras = []
    if n_ == N - 1:
        ep = TMP / "end.png"; end_overlay(ep)
        cmd += ["-i", str(ep)]; extras.append((idx, f"gte(t,{max(L-2.0,0)})")); idx += 1
    fc = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5[bg];"
          f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v0];"
          f"[v0][1:v]overlay=0:0[v1]")
    last = "v1"
    for k, (i_, en) in enumerate(extras):
        fc += f";[{last}][{i_}:v]overlay=0:0:enable='{en}'[x{k}]"; last = f"x{k}"
    fc += f";[{last}]setsar=1,fps=30[v]"
    clip_a = has_audio(src)
    if not clip_a:
        cmd += ["-f", "lavfi", "-t", str(L), "-i", "anullsrc=r=44100:cl=stereo"]; nidx = idx; idx += 1
    ca = "0:a" if clip_a else f"{nidx}:a"
    fc += f";[{ca}]afade=t=in:st=0:d=0.04,afade=t=out:st={max(L-0.12,0)}:d=0.12,aresample=44100,aformat=channel_layouts=stereo[a]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", str(L), str(seg.resolve())]
    subprocess.run(cmd, check=True, cwd=TMP)
    segs.append(seg); print("segment", item["rank"], item["label"], f"{L}s")

lst = TMP / "list.txt"
lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), encoding="utf-8")
name = f"top{N}_cats_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M')}"
final = OUT / f"{name}.mp4"
music = ROOT / "assets" / "music_loop.wav"
if not music.exists():
    subprocess.run([sys.executable, str(ROOT / "music.py")], check=True)
# clip sounds are the star; music only a faint bed
subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-stream_loop", "-1", "-i", str(music),
                "-filter_complex", "[0:a]aresample=44100[c];[1:a]aformat=channel_layouts=stereo,volume=0.05[m];[c][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(final)], check=True)
print("rendered", final)

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)],
                           capture_output=True, text=True).stdout.strip())
sheet = OUT / f"{name}_preview.jpg"
subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(final), "-vf", f"fps=8/{dur},scale=270:-1,tile=8x1", "-frames:v", "1", str(sheet)], check=True)
subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", "1", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(OUT / f"{name}_thumb.jpg")], check=True)
print("preview:", sheet, "| duration", round(dur, 1), "s")
