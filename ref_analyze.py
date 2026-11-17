import subprocess, json, re, pathlib, sys
import asr_util
D = pathlib.Path(r"C:\Users\benit\Downloads")
names = {"help":"Help.mp4","sounds":"What's your favorite cat sounds.mp4","rank":"Ranking Funniest Cat Moments.mp4","grumpy":"GRUMPY CAT!.mp4"}
out = pathlib.Path("data/refs")
for k, fn in names.items():
    f = str(D/fn)
    pr = json.loads(subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,width,height,r_frame_rate:format=duration","-of","json",f],capture_output=True,text=True).stdout)
    dur = float(pr["format"]["duration"]); v=[s for s in pr["streams"] if s["codec_type"]=="video"][0]
    sc = subprocess.run(["ffmpeg","-i",f,"-vf","select='gt(scene,0.3)',showinfo","-an","-f","null","-"],capture_output=True,text=True).stderr
    cuts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", sc)]
    vol = subprocess.run(["ffmpeg","-i",f,"-af","ebur128=peak=true","-vn","-f","null","-"],capture_output=True,text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", vol)
    try:
        w = asr_util.words(f)
    except Exception as e:
        w = []; print("asr fail", e)
    txt = " ".join(x[0] for x in w)
    print(f"\n== {k}: {dur:.1f}s {v['width']}x{v['height']} cuts={len(cuts)} (avg {dur/(len(cuts)+1):.1f}s/shot) LUFS={lufs[-1] if lufs else '?'} words={len(w)} ({len(w)/dur:.2f}/s) first_word@{w[0][1] if w else '-'}")
    print("cuts:", [round(c,1) for c in cuts][:30]); print("ASR:", txt[:500])
    pathlib.Path(out/f"{k}_words.json").write_text(json.dumps(w))
    subprocess.run(["ffmpeg","-y","-v","error","-i",f,"-vf",f"fps=1/{max(dur/12,1):.2f},scale=270:-1,tile=6x2",str(out/f"{k}_sheet.jpg"),"-frames:v","1"])
