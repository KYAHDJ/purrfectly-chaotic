"""Helpers: load audio via ffmpeg (avoids faster-whisper/PyAV mismatch) and transcribe with word timestamps."""
import subprocess, numpy as np
from faster_whisper import WhisperModel

_model = None
def load_audio(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

def words(path, model="base.en"):
    global _model
    if _model is None:
        _model = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = _model.transcribe(load_audio(path), word_timestamps=True)
    return [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
