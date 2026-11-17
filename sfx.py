"""Synthesized sound effects (original, no samples): whoosh, pop, hit, click. Writes assets/sfx_*.wav (44.1k mono)."""
import numpy as np, pathlib, wave

SR = 44100
OUT = pathlib.Path(__file__).parent / "assets"; OUT.mkdir(exist_ok=True)

def save(name, x):
    x = np.clip(x / max(np.abs(x).max(), 1e-6) * 0.9, -1, 1)
    with wave.open(str(OUT / f"sfx_{name}.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

def whoosh(d=0.45):
    n = int(SR * d); t = np.linspace(0, 1, n); rng = np.random.default_rng(1)
    noise = rng.standard_normal(n)
    # sweep a band-pass up then down using a moving average of varying width
    k = np.cumsum(noise); out = np.zeros(n)
    for w in (8, 24, 60):
        out += (k - np.concatenate([np.zeros(w), k[:-w]])) / w
    env = np.sin(np.pi * t) ** 2
    return (noise * 0.35 + out * 1.4) * env

def pop(d=0.14):
    n = int(SR * d); t = np.arange(n) / SR
    f = 900 - 5000 * t
    return np.sin(2 * np.pi * np.cumsum(np.maximum(f, 200)) / SR) * np.exp(-t * 28)

def hit(d=0.5):
    n = int(SR * d); t = np.arange(n) / SR; rng = np.random.default_rng(2)
    f = 110 * np.exp(-t * 6) + 40
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + rng.standard_normal(n) * 0.15 * np.exp(-t * 30))

def click(d=0.08):
    n = int(SR * d); t = np.arange(n) / SR; rng = np.random.default_rng(3)
    return (rng.standard_normal(n) * np.exp(-t * 90) + np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 60))

def scratch(d=0.45):
    n = int(SR * d); t = np.arange(n) / SR; rng = np.random.default_rng(5)
    f = 900 * np.exp(-t * 5) + 120
    saw = ((np.cumsum(f) / SR) % 1.0) * 2 - 1
    return (saw * 0.6 + rng.standard_normal(n) * 0.5) * np.exp(-t * 3) * (1 - np.exp(-t * 400))

def beep(d=0.5):
    n = int(SR * d); t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * 1000 * t)) * ((t % 0.25) < 0.14)
    return sq * 0.6

def drop(d=1.1):
    n = int(SR * d); t = np.arange(n) / SR
    f = 180 * np.exp(-t * 3.2) + 28
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)

def meow(d=0.7):
    n = int(SR * d); t = np.arange(n) / SR; u = t / d
    f0 = 420 + 480 * np.sin(np.pi * np.clip(u * 1.1, 0, 1)) ** 0.8 - 120 * u
    ph = 2 * np.pi * np.cumsum(f0) / SR
    out = np.zeros(n)
    for k in range(1, 40):
        fk = k * f0
        a = np.exp(-((fk - 900) / 450) ** 2) + 0.6 * np.exp(-((fk - 2500) / 700) ** 2)
        out += a * np.sin(k * ph) / k ** 0.3
    env = np.minimum(u / 0.08, 1) * np.exp(-((u - 0.45) / 0.45) ** 4)
    return out * env * (1 + 0.08 * np.sin(2 * np.pi * 7 * t))

if __name__ == "__main__":
    for nm, fn in (("whoosh", whoosh), ("pop", pop), ("hit", hit), ("click", click), ("scratch", scratch), ("beep", beep), ("drop", drop), ("meow", meow)):
        save(nm, fn())
    print("sfx written to", OUT)
