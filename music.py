"""Generate an original, license-free upbeat loop (no downloads). -> assets/music_loop.wav"""
import numpy as np, wave, pathlib

SR = 44100; BPM = 140; BEAT = 60 / BPM; BARS = 28  # ~48s
out = pathlib.Path(__file__).parent / "assets"; out.mkdir(exist_ok=True)
rng = np.random.default_rng(7)
n = int(SR * BEAT * 4 * BARS)
mix = np.zeros(n)

def add(sig, t0):
    i = int(t0 * SR); j = min(n, i + len(sig))
    if i < n: mix[i:j] += sig[: j - i]

def env(L, a=0.005, d=8.0):
    t = np.arange(L) / SR
    return np.minimum(t / a, 1) * np.exp(-d * t)

def tone(freq, dur, kind="tri", amp=0.3, d=6.0):
    L = int(SR * dur); t = np.arange(L) / SR
    ph = 2 * np.pi * freq * t
    w = {"tri": 2 / np.pi * np.arcsin(np.sin(ph)), "sq": np.sign(np.sin(ph)) * 0.6, "sin": np.sin(ph)}[kind]
    return w * env(L, d=d) * amp

def kick():
    L = int(SR * 0.25); t = np.arange(L) / SR
    f = 120 * np.exp(-t * 22) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * 0.9

def hat():
    L = int(SR * 0.05)
    return rng.standard_normal(L) * np.exp(-np.arange(L) / SR * 90) * 0.12

def clap():
    L = int(SR * 0.12)
    return rng.standard_normal(L) * np.exp(-np.arange(L) / SR * 28) * 0.25

mid = lambda m: 440 * 2 ** ((m - 69) / 12)
prog = [(48, [60, 64, 67]), (45, [57, 60, 64]), (41, [57, 60, 65]), (43, [59, 62, 67])]  # C Am F G
pent = [0, 2, 4, 7, 9]
for bar in range(BARS):
    root, chord = prog[bar % 4]
    t0 = bar * BEAT * 4
    for b in range(4):
        add(kick(), t0 + b * BEAT)
        if b in (1, 3): add(clap(), t0 + b * BEAT)
    for e in range(8):
        add(hat(), t0 + e * BEAT / 2 + BEAT / 4 * (e % 2 == 1) * 0)
        add(tone(mid(root - 12 + (12 if e % 4 == 3 else 0)), BEAT / 2 * 0.9, "sq", 0.16, 7), t0 + e * BEAT / 2)
    base = chord[0]
    for s in range(16):  # sixteenth-note pluck arpeggio, varies per bar
        if rng.random() < 0.72:
            note = base + 12 + pent[int(rng.integers(0, 5))] + (12 if rng.random() < 0.25 else 0)
            add(tone(mid(note), BEAT / 4 * 1.6, "tri", 0.14, 9), t0 + s * BEAT / 4)

mix = np.tanh(mix * 1.1)
mix /= np.max(np.abs(mix)) / 0.9
pcm = (mix * 32767).astype(np.int16)
with wave.open(str(out / "music_loop.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("music ->", out / "music_loop.wav", round(n / SR), "s")
