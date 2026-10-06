import json
import wave
import numpy as np
from faster_whisper import WhisperModel


def load_wav(path):
    with wave.open(path, "rb") as w:
        frames = w.readframes(w.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


model = WhisperModel("medium", device="cpu", compute_type="int8")
for name in ["IMG_9141", "IMG_9145", "IMG_9148", "IMG_9150", "IMG_9151", "IMG_9153"]:
    audio = load_wav(f"{name}.wav")
    segs, info = model.transcribe(
        audio,
        language="pt",
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
        beam_size=5,
    )
    out = []
    for s in segs:
        out.append({
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text.strip(),
            "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in (s.words or [])],
        })
    with open(f"{name}_v2.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(name, len(out), "segments", flush=True)

