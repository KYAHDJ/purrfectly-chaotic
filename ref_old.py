import subprocess, json, re, pathlib, asr_util
D = pathlib.Path(r"C:\Users\benit\Downloads\Catcompilationsinpast"); out = pathlib.Path("data/refs/old")
for i, f in enumerate(sorted(D.glob("*.mp4")), 1):
    pr = json.loads(subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,width,height,r_frame_rate:format=duration","-of","json",str(f)],capture_output=True,text=True).stdout)
    dur = float(pr["format"]["duration"]); v=[s for s in pr["streams"] if s["codec_type"]=="video"][0]
    sc = subprocess.run(["ffmpeg","-i",str(f),"-vf","select='gt(scene,0.35)',showinfo","-an","-f","null","-"],capture_output=True,text=True).stderr
    cuts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", sc)]
    vol = subprocess.run(["ffmpeg","-i",str(f),"-af","ebur128=peak=true","-vn","-f","null","-"],capture_output=True,text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", vol)
    try: w = asr_util.words(str(f))
    except Exception as e: w = []; print("asr fail", e)
    txt = " ".join(x[0] for x in w)
    print(f"\n#{i} {f.name}: {dur:.0f}s {v['width']}x{v['height']} cuts={len(cuts)} ({dur/(len(cuts)+1):.1f}s/shot) LUFS={lufs[-1] if lufs else '?'} words={len(w)} ({len(w)/dur:.2f}/s) first@{w[0][1] if w else '-'}")
    print("ASR:", txt[:600], flush=True)
    (out/f"{i}_words.json").write_text(json.dumps(w))
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(f),"-vf",f"fps=12/{dur:.1f},scale=240:-1,tile=6x2",str(out/f"{i}_sheet.jpg"),"-frames:v","1"])
