import json
import os
import re
import subprocess

# (arquivo, início, fim) em segundos, na ordem do vídeo final
CLIPS = [
    ("IMG_9145", [(0.5, 23.8)]),   # título + itens 1 e 2
    # item 3 + comunidade; pausas longas da parte das planilhas encurtadas (0,2 s de respiro)
    ("IMG_9148", [(0.6, 2.22), (2.40, 3.36), (3.71, 4.92), (5.11, 7.78), (8.21, 11.53), (11.90, 29.4)]),
    ("IMG_9150", [(0.4, 18.2)]),   # item 4
    ("IMG_9151", [(0.0, 3.9)]),    # chamada para comentar
]

# correções de ortografia / marca (palavra sem pontuação -> correta)
FIX = {
    "Cloud": "Claude",
    "Cláudio": "Claude",
    "Claudio": "Claude",
    "garrões": "garranchos",
    "bananava": "embananava",
    "ferida": "querida",
}

WIDTH, HEIGHT = 1080, 1920
os.makedirs("parts", exist_ok=True)


def fix_word(w):
    m = re.match(r"^(\W*)(\w+)(\W*)$", w)
    if not m:
        return w
    pre, core, post = m.groups()
    return pre + FIX.get(core, core) + post


def load(name):
    return json.load(open(f"{name}_v2.json", encoding="utf-8"))


def words_in(name, start, end):
    ws = []
    for seg in load(name):
        for w in seg["words"]:
            if w["s"] >= start and w["e"] <= end + 0.05 and w["w"]:
                ws.append(w)
    return ws


# cada trecho vira um arquivo: (arquivo, início, fim) na ordem do vídeo final
SEGMENTS = [(name, s, e) for name, ranges in CLIPS for s, e in ranges]

# 1) cortes verticais 1080x1920
parts = []
for i, (name, s, e) in enumerate(SEGMENTS):
    out = f"parts/p{i}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", rf"C:\Users\layla\Downloads\{name}.MOV",
        "-ss", str(s), "-to", str(e),
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        out,
    ], check=True)
    parts.append(out)

with open("parts/list.txt", "w", encoding="utf-8") as f:
    for p in parts:
        f.write(f"file '{os.path.basename(p)}'\n")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", "parts/list.txt", "-c", "copy", "base.mp4"], check=True)

# 2) legendas: grupos de até 4 palavras, tempo relativo ao vídeo final
def ts(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


events = []
offset = 0.0
for name, s, e in SEGMENTS:
    ws = words_in(name, s, e)
    group = []
    for w in ws:
        if group and (len(group) >= 4 or w["s"] - group[-1]["e"] > 0.6):
            events.append((offset + group[0]["s"] - s, offset + group[-1]["e"] - s, " ".join(fix_word(x["w"]) for x in group)))
            group = []
        group.append(w)
    if group:
        events.append((offset + group[0]["s"] - s, offset + group[-1]["e"] - s, " ".join(fix_word(x["w"]) for x in group)))
    offset += e - s

header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Legenda,Arial,58,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,80,80,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
with open("subs.ass", "w", encoding="utf-8") as f:
    f.write(header)
    for a, b, t in events:
        t = t.replace("me querida", "minha querida")
        f.write(f"Dialogue: 0,{ts(a)},{ts(b)},Legenda,,0,0,0,,{t}\n")

# 3) motion graphics (overlay com alfa) + legendas queimadas no vídeo
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "base.mp4",
                "-i", "../motion/out/overlay.mov",
                "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1[v];[v]ass=subs.ass[vout]",
                "-map", "[vout]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "copy", "final_reels.mp4"], check=True)

print("eventos de legenda:", len(events))
for a, b, t in events:
    print(f"{a:6.2f}-{b:6.2f} {t}")
print("duração total:", round(offset, 2), "s")
