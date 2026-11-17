"""Commentator voice: text -> wav via the local VoiceStudio API, plus word timings for subtitles."""
import json, os, pathlib, subprocess, time, urllib.request, urllib.error, wave

API = "http://127.0.0.1:3900"
CLI = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Programs" / "VoiceStudio" / "resources" / "cli" / "voicestudio.exe"
ENGINE = "kittentts"
VOICE = "Jasper"
SPEED = 1.5  # fast, nonstop delivery like top commentary Shorts (~3.4 words/sec)  # Kitten presets: Bella Jasper Luna Bruno Rosie Hugo Kiki Leo

def _up():
    try:
        urllib.request.urlopen(API + "/v1/models", timeout=5).read(); return True
    except Exception:
        return False

def ensure_backend(timeout=240):
    """Start VoiceStudio's backend in the background if needed (no window) and wait until it answers."""
    if _up(): return
    subprocess.run([str(CLI), "engines", "select", "--type", "tts", ENGINE], capture_output=True, timeout=300)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if _up(): return
        time.sleep(3)
    raise RuntimeError("VoiceStudio backend did not start")

def _sapi(text, out_wav, speed, voice_name=None, rate=None):
    """Stand-in Windows voice, only for testing the video pipeline when VoiceStudio is not ready."""
    raw = str(out_wav) + ".raw.wav"
    sel = f"$s.SelectVoice('{voice_name}'); " if voice_name else ""
    rt = f"$s.Rate={rate}; " if rate is not None else ""
    ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; " + sel + rt +
          f"$s.SetOutputToWaveFile('{raw}'); $s.Speak([Console]::In.ReadToEnd()); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=text, text=True, check=True)
    af = "anull" if voice_name else f"atempo={min(max(speed / 1.3, 0.5), 2.0)}"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", af, "-ar", "24000", str(out_wav)], check=True)
    with wave.open(str(out_wav)) as w:
        return w.getnframes() / w.getframerate()

def tts(text, out_wav, voice=VOICE, speed=None):
    speed = speed or SPEED
    if os.environ.get("VOICE_ENGINE", "edge") == "edge":  # natural neural voice (online, free); falls back to David if offline
        try:
            import subprocess, sys, tempfile
            mp3 = str(out_wav) + ".mp3"
            for _try in range(6):
                if _try: __import__("time").sleep(1.2 * _try)
                r_ = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", os.environ.get("EDGE_VOICE", "en-US-AndrewNeural"), "--rate=" + os.environ.get("EDGE_RATE", "+40%"), "--pitch=" + os.environ.get("EDGE_PITCH", "+2Hz"), "--text=" + text, "--write-media", mp3], capture_output=True, text=True, timeout=60)
                if r_.returncode == 0: break
            else: raise RuntimeError(r_.stderr[-200:])
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3, "-ac", "1", "-ar", "24000", str(out_wav)], check=True)
            with wave.open(str(out_wav)) as w: return w.getnframes() / w.getframerate()
        except Exception as e:
            print("edge voice failed, using David:", str(e)[:80], flush=True)
    if os.environ.get("VOICE_ENGINE", "edge") in ("edge", "david"):  # default: real male Windows voice; set VOICE_ENGINE=voicestudio to use VoiceStudio  # real male Windows voice, already fast: use with VATEMPO=1 VPITCH=1
        return _sapi(text, out_wav, speed, voice_name="Microsoft David Desktop", rate=int(os.environ.get("DAVID_RATE", "3")))
    if os.environ.get("VOICE_FALLBACK") == "sapi" and not _up():
        return _sapi(text, out_wav, speed)
    body = json.dumps({"model": ENGINE, "input": text, "voice": voice, "response_format": "wav", "speed": speed}).encode()
    req = urllib.request.Request(API + "/v1/audio/speech", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        pathlib.Path(out_wav).write_bytes(r.read())
    with wave.open(str(out_wav)) as w:
        return w.getnframes() / w.getframerate()
