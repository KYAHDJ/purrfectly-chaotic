"""Make 6 different short swoosh sounds -> assets/swoosh_1..6.wav (44.1k mono)."""
import numpy as np, wave, pathlib
SR = 44100; ROOT = pathlib.Path(__file__).parent; rng = np.random.default_rng(7)
def sweep(dur, f0, f1, peak=0.5, q=0.5, tone=0.0, gain=0.8):
    n = int(SR * dur); t = np.arange(n) / SR; x = rng.standard_normal(n)
    fc = f0 * (f1 / f0) ** (t / dur); a = 1 - np.exp(-2 * np.pi * fc / SR); y = np.zeros(n); lo = 0.0; lo2 = 0.0
    for i in range(n):
        lo += a[i] * (x[i] - lo); lo2 += a[i] * 0.35 * (lo - lo2); y[i] = lo - lo2
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 if peak == 0.5 else np.where(t < dur * peak, (t / (dur * peak)) ** 2, ((dur - t) / (dur * (1 - peak))) ** 1.5)
    y = y * env
    if tone: y += tone * np.sin(2 * np.pi * np.cumsum(fc * 0.5) / SR) * env
    return y / (np.abs(y).max() + 1e-9) * gain
specs = [(0.50, 300, 5200, 0.7), (0.55, 4800, 260, 0.35), (0.30, 1500, 7000, 0.6), (0.60, 150, 1800, 0.5), (0.45, 900, 3200, 0.5), (0.35, 600, 9000, 0.8)]
for i, (d, a, b, p) in enumerate(specs, 1):
    y = sweep(d, a, b, p, tone=0.12 if i == 6 else 0)
    with wave.open(str(ROOT / "assets" / f"swoosh_{i}.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
print("ok")
