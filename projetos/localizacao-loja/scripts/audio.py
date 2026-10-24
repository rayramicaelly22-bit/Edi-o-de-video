"""Trilha, efeitos sonoros e mixagem final — tudo sintetizado aqui (sem samples nem músicas de terceiros).

Lê src/timeline.json, public/scene/scene.json e public/audio/narration.json e grava em public/audio/:
  music.wav  — trilha (house/pop alegre em Mi maior, 124,7 BPM: os compassos caem no início da rota,
               na virada e na chegada)
  sfx.wav    — whooshes, pops, seta de carro, impacto e brilhos sincronizados com o motion graphics
  mix.wav    — narração + trilha (com ducking sob a voz) + efeitos, pronta para normalizar e juntar ao vídeo
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public/audio"
SR = 44100
RNG = np.random.default_rng(42)

TL = json.loads((ROOT / "src/timeline.json").read_text())
SCENE = json.loads((ROOT / "public/scene/scene.json").read_text())
NARR = json.loads((OUT / "narration.json").read_text())
DUR = TL["end"]
N = int(DUR * SR) + SR

# grade musical ancorada no voo: 8 compassos entre o início da rota e a chegada
BAR = (TL["arrive"] - TL["routeStart"]) / 8
BEAT = BAR / 4
GRID0 = TL["routeStart"] - 4 * BAR
BPM = 60 / BEAT


def bar_t(k, beat=0.0):
    return GRID0 + (k + beat / 4) * BAR


# ------------------------------------------------------------------ utilitários de síntese
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a=0.005, d=0.1, s=0.7, r=0.1, hold=None):
    t = np.arange(n) / SR
    hold = (n / SR - r) if hold is None else hold
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = np.clip((t - hold) / max(r, 1e-6), 0, 1)
    return e * (1 - rel)


def saw(freq, n, max_hz=9000.0, phase=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    k = 1
    while k * freq < max_hz and k < 80:
        out += np.sin(2 * np.pi * k * freq * t + phase * k) / k
        k += 1
    return out * (2 / np.pi)


def sine(freq, n, phase=0.0):
    return np.sin(2 * np.pi * freq * np.arange(n) / SR + phase)


def lp(x, hz, order=2):
    return sosfilt(butter(order, min(hz, SR * 0.45), "low", fs=SR, output="sos"), x)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x)


def place(track, sig, t0, gain=1.0, pan=0.0):
    """Soma um sinal (mono ou estéreo) na faixa estéreo, no instante t0 (s)."""
    s = int(round(t0 * SR))
    if s >= len(track):
        return
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], 1)
    if s < 0:
        sig = sig[-s:]
        s = 0
    e = min(len(track), s + len(sig))
    track[s:e] += sig[: e - s] * gain


def reverb(x, seconds=1.6, wet=0.25, predelay=0.015, damp=6000):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.stack([RNG.standard_normal(n), RNG.standard_normal(n)], 1) * np.exp(-t * 6.9 / seconds)[:, None]
    ir = np.stack([lp(ir[:, 0], damp), lp(ir[:, 1], damp)], 1)
    ir[: int(predelay * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet) + y * wet * 1.6


# ------------------------------------------------------------------ instrumentos
def kick():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 46 + 84 * np.exp(-t * 30)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.0)
    click = hp(RNG.standard_normal(n), 2500) * np.exp(-t * 500) * 0.35
    return np.tanh(1.6 * (body + click)) * 0.9


def clap():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    noise = bp(RNG.standard_normal(n), 900, 6000)
    e = np.zeros(n)
    for k, d in enumerate([0.0, 0.011, 0.022]):
        e += (t >= d) * np.exp(-(t - d) * (180 if k < 2 else 22)) * (t >= d)
    return noise * e * 0.55


def hat(open_=False):
    n = int((0.22 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    noise = hp(RNG.standard_normal(n), 7500, 4)
    return noise * np.exp(-t * (14 if open_ else 70)) * (0.32 if open_ else 0.26)


def crash():
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    noise = hp(RNG.standard_normal(n), 4500, 2) + 0.3 * hp(RNG.standard_normal(n), 9000, 2)
    return noise * np.exp(-t * 1.9) * 0.22


def bass_note(midi, dur):
    n = int(dur * SR)
    f = mtof(midi)
    x = 0.65 * saw(f, n, 3500) + 0.35 * np.sign(sine(f, n)) * 0.6 + 0.5 * sine(f, n)
    x = lp(x, 900) * env_adsr(n, 0.004, 0.14, 0.55, 0.05)
    return np.tanh(1.4 * x) * 0.75


def pad_chord(midis, dur, cutoff):
    n = int(dur * SR)
    L = np.zeros(n)
    R = np.zeros(n)
    for m in midis:
        f = mtof(m)
        for det, pan in [(-0.11, -0.8), (0.0, 0.0), (0.11, 0.8)]:
            ff = f * 2 ** (det / 12)
            v = saw(ff, n, 7000, phase=RNG.uniform(0, 6.28))
            L += v * (1 - pan) / 2
            R += v * (1 + pan) / 2
    e = env_adsr(n, 0.25, 0.6, 0.85, 0.35)
    return np.stack([lp(L, cutoff) * e, lp(R, cutoff) * e], 1) / (len(midis) * 2.2)


def pluck(midi, dur=0.22, bright=3800):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    x = 0.7 * saw(f, n, 8000) + 0.3 * sine(2 * f, n)
    # filtro "abre e fecha": mistura de versões filtradas conforme o envelope
    e = np.exp(-t * 22)
    x = lp(x, 900) * (1 - e) + lp(x, bright) * e
    return x * np.exp(-t * 13) * 0.5


def bell(midi, dur=1.2, amp=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 2.2 * np.exp(-t * 6)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 3.2) * amp


def noise_sweep(dur, f0, f1, amp=0.4, rise=0.7):
    """Whoosh/riser: ruído em faixa que varre de f0 a f1 (Hz), com envelope sobe/desce."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = RNG.standard_normal(n)
    out = np.zeros(n)
    steps = 24
    for i in range(steps):
        a, b = int(i * n / steps), int((i + 1) * n / steps)
        fc = f0 * (f1 / f0) ** ((i + 0.5) / steps)
        seg = bp(noise[max(0, a - 2048):b], fc * 0.7, fc * 1.4)[-(b - a):]
        out[a:b] = seg
    env = np.where(t < dur * rise, (t / (dur * rise)) ** 2, np.exp(-(t - dur * rise) / (dur * (1 - rise) * 0.35 + 1e-3)))
    return out * env * amp


# ------------------------------------------------------------------ trilha
CHORDS = [  # Mi maior: E – B – C#m – A (vozes próximas)
    {"root": 40, "pad": [56, 59, 64, 68], "arp": [64, 68, 71, 76]},
    {"root": 35, "pad": [54, 59, 63, 66], "arp": [63, 66, 71, 75]},
    {"root": 37, "pad": [56, 61, 64, 68], "arp": [64, 68, 73, 76]},
    {"root": 33, "pad": [57, 61, 64, 69], "arp": [64, 69, 73, 76]},
]


def build_music():
    tr = np.zeros((N, 2))
    drums = np.zeros((N, 2))
    k_s, cl_s, hc_s, ho_s, cr_s = kick(), clap(), hat(), hat(True), crash()
    n_bars = 18
    kicks = []
    for k in range(n_bars):
        ch = CHORDS[k % 4]
        t0 = bar_t(k)
        intro = k < 4
        outro_hit = k == 17
        # pad (no intro o filtro vai abrindo)
        cutoff = 900 + 700 * k if intro else (2600 if k < 12 else 3400)
        if outro_hit:
            place(tr, pad_chord(CHORDS[0]["pad"], BAR * 1.6, 3000), t0, 1.0)
        else:
            place(tr, pad_chord(ch["pad"], BAR + 0.35, cutoff), t0, 0.9 if not intro else 0.75 + 0.05 * k)
        if outro_hit:
            continue
        # arpejo em semicolcheias (entra no compasso 2 da intro)
        if k >= 1:
            for i in range(16):
                m = ch["arp"][[0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 3, 1, 2][i]]
                g = 0.18 if intro else 0.24
                if k >= 12:
                    g = 0.27
                place(tr, pluck(m + 12 if (i % 8 == 7 and k >= 4) else m, bright=2400 if intro else 4200), bar_t(k, i / 4), g, pan=-0.45 if i % 2 else 0.45)
        # bateria
        if k >= 4:
            for b in range(4):
                kt = bar_t(k, b)
                place(drums, k_s, kt, 1.0)
                kicks.append(kt)
                if b in (1, 3):
                    place(drums, cl_s, kt, 0.9)
                place(drums, ho_s, bar_t(k, b + 0.5), 0.55, pan=0.2)
                for h in (0.25, 0.75):
                    place(drums, hc_s, bar_t(k, b + h), 0.5, pan=0.25)
            # baixo no contratempo (estilo house)
            for b in range(4):
                place(tr, bass_note(ch["root"] + 12, BEAT * 0.48), bar_t(k, b + 0.5), 0.95)
                if b in (0, 2):
                    place(tr, bass_note(ch["root"] + 12, BEAT * 0.22), bar_t(k, b + 0.75), 0.55)
        elif k >= 2:
            for b in range(4):
                for h in (0.5,):
                    place(drums, hc_s, bar_t(k, b + h), 0.45, pan=0.25)
        # virada de caixa antes da chegada
        if k == 11:
            for i in range(8):
                place(drums, cl_s, bar_t(k, 2 + i * 0.25), 0.35 + 0.08 * i)
    # pratos nos marcos
    for t0 in [TL["routeStart"], TL["arrive"], bar_t(17)]:
        place(drums, cr_s, t0, 1.0, pan=0.1)
    # sino da melodia na parte da loja
    melody = [(12, 0, 76), (12, 1.5, 75), (12, 3, 73), (13, 0, 71), (13, 2, 75), (14, 0, 73), (14, 1.5, 76), (14, 3, 80),
              (15, 0, 76), (15, 2, 73)]
    for k, beat, m in melody:
        place(tr, bell(m), bar_t(k, beat), 0.22, pan=0.15)
    # final: acorde + sino
    place(tr, bell(76, 2.5, 0.4), bar_t(17), 0.5)
    place(tr, bell(83, 2.5, 0.25), bar_t(17) + 0.02, 0.4)
    place(drums, k_s, bar_t(17), 1.1)
    # risers antes do início da rota e da chegada
    place(tr, noise_sweep(BAR * 2, 300, 7000, 0.35, 0.95), TL["routeStart"] - BAR * 2, 0.8)
    place(tr, noise_sweep(BAR * 1.0, 500, 9000, 0.3, 0.95), TL["arrive"] - BAR * 1.0, 0.8)

    # sidechain: o pad/baixo "respiram" a cada bumbo
    t = np.arange(N) / SR
    pump = np.ones(N)
    for kt in kicks:
        s = int(kt * SR)
        e = min(N, s + int(BEAT * SR))
        tt = t[s:e] - kt
        pump[s:e] = np.minimum(pump[s:e], 1 - 0.55 * np.exp(-tt * 9))
    tr *= pump[:, None]
    tr = reverb(tr, 1.8, 0.22)
    drums = reverb(drums, 0.9, 0.08)
    mix = tr * 0.9 + drums * 0.85
    # fade-in curto e fade-out no fim
    fade_in = np.clip(t / 0.25, 0, 1)
    fade_out = np.clip((DUR - t) / 1.2, 0, 1)
    return mix * (fade_in * fade_out)[:, None]


# ------------------------------------------------------------------ efeitos sonoros
def route_time(s):
    """Mesma função de progresso da câmera (Hermite) — instante em que a rota passa pela distância s."""
    turn_m, v_turn = 1645.2, 105.0
    L = SCENE["route"]["length"]

    def prog(t):
        def h(t, t0, t1, p0, p1, m0, m1):
            dt = t1 - t0
            u = min(1, max(0, (t - t0) / dt))
            return (2 * u**3 - 3 * u**2 + 1) * p0 + (u**3 - 2 * u**2 + u) * dt * m0 + (-2 * u**3 + 3 * u**2) * p1 + (u**3 - u**2) * dt * m1
        if t <= TL["routeStart"]:
            return 0
        if t <= TL["turnAt"]:
            return h(t, TL["routeStart"], TL["turnAt"], 0, turn_m, 0, v_turn)
        if t <= TL["arrive"]:
            return h(t, TL["turnAt"], TL["arrive"], turn_m, L, v_turn, 0)
        return L
    lo, hi = TL["routeStart"], TL["arrive"]
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if prog(mid) < s else (lo, mid)
    return (lo + hi) / 2


def line(id_):
    return next(l for l in NARR["lines"] if l["id"] == id_)


def word(id_, prefix):
    return next(w["start"] for w in line(id_)["words"] if w["text"].lower().startswith(prefix))


def pop_sfx(pitch=1.0):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = (380 + 900 * (1 - np.exp(-t * 60))) * pitch
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38) * 0.5


def tick_sfx(f=2300):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.4 * hp(RNG.standard_normal(n), 3000)) * np.exp(-t * 120) * 0.35


def impact_sfx():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    f = 32 + 60 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    hit = lp(RNG.standard_normal(n), 2500) * np.exp(-t * 18) * 0.6
    return np.tanh(1.5 * (boom + hit)) * 0.75


def sparkle_sfx():
    out = np.zeros(int(1.4 * SR))
    for i, m in enumerate([88, 93, 95, 100, 98, 103]):
        b = bell(m, 0.6, 0.18)
        s = int(i * 0.055 * SR)
        out[s:s + len(b)] += b[: len(out) - s]
    return out


def build_sfx():
    tr = np.zeros((N, 2))
    up = noise_sweep(0.7, 400, 5000, 0.4, 0.75)
    down = noise_sweep(0.6, 5000, 500, 0.35, 0.35)
    place(tr, up, 0.05, 0.9, pan=-0.3)
    place(tr, pop_sfx(1.2), 0.85, 0.7)
    place(tr, down, 4.1, 0.8, pan=0.3)
    place(tr, pop_sfx(), TL["descentEnd"] + 0.25, 0.8)                       # etiqueta da praça
    place(tr, bell(84, 0.9, 0.3), TL["routeStart"] + 0.95, 0.8)               # pin pousa
    for s in (330, 560, 950, 1480):                                          # banner troca de instrução
        place(tr, tick_sfx(), route_time(s), 0.8)
    t_blink = route_time(1480) + 0.3                                           # seta de carro até a virada
    k = 0
    while t_blink < TL["turnAt"] + 0.2:
        place(tr, tick_sfx(1900 if k % 2 == 0 else 1400), t_blink, 0.55, pan=-0.5)
        t_blink += 0.38
        k += 1
    place(tr, pop_sfx(0.9), route_time(1690), 0.8)                            # hospital
    place(tr, impact_sfx(), TL["arrive"] - 0.1, 0.9)                          # CHEGOU!
    place(tr, sparkle_sfx(), TL["arrive"] - 0.05, 0.8)
    place(tr, up, TL["arrive"] + 0.7, 0.6, pan=0.3)                           # cartão da loja
    place(tr, pop_sfx(1.3), TL["arrive"] + 1.25, 0.6)                         # etiqueta da loja
    for w, p in (("frente", 1.0), ("ladinho", 1.15)):
        place(tr, pop_sfx(p), word("endereco", w) - 0.08, 0.7)
    place(tr, pop_sfx(1.3), TL["arrive"] + 0.85 + 0.45, 0.7)                  # item "perto do hospital"
    place(tr, noise_sweep(0.9, 300, 3000, 0.35, 0.6), line("convite")["start"] - 0.6, 0.8)
    place(tr, bell(81, 1.4, 0.3), line("convite")["start"] - 0.25, 0.7)
    return reverb(tr, 1.0, 0.15)


# ------------------------------------------------------------------ mixagem
def envelope(x, attack=0.02, release=0.35):
    a = np.exp(-1 / (attack * SR))
    r = np.exp(-1 / (release * SR))
    env = np.zeros_like(x)
    level = 0.0
    xa = np.abs(x)
    # janela de 5 ms para acelerar
    hop = int(0.005 * SR)
    for i in range(0, len(x), hop):
        v = xa[i:i + hop].max() if i < len(x) else 0
        coef = a ** hop if v > level else r ** hop
        level = coef * level + (1 - coef) * v
        env[i:i + hop] = level
    return env


def main():
    music = build_music()
    sfx = build_sfx()
    voice, sr = sf.read(OUT / "narration.wav")
    assert sr == SR
    voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
    voice = hp(voice, 90)
    # leve presença na voz
    voice = voice + 0.22 * bp(voice, 2500, 5500)
    env = envelope(voice)
    duck = 1 - 0.75 * np.clip(env / 0.06, 0, 1)  # até -12 dB na música enquanto há fala
    music_d = music * duck[:, None]
    for name, stem in (("music", music), ("sfx", sfx)):
        stem = stem[: int(DUR * SR)]
        sf.write(OUT / f"{name}.wav", stem * (0.95 / np.abs(stem).max()), SR, subtype="PCM_16")
    mix = 0.32 * music_d + 0.42 * sfx + np.stack([voice, voice], 1) * 1.15
    mix = mix[: int(DUR * SR)]
    peak = np.abs(mix).max()
    mix = np.tanh(mix / peak * 1.1) / np.tanh(1.1) * 0.92  # limitador suave
    sf.write(OUT / "mix.wav", mix, SR, subtype="PCM_16")
    print(f"BPM {BPM:.2f}, compasso {BAR:.3f}s, grade começa em {GRID0:.3f}s; mix {len(mix) / SR:.2f}s")


if __name__ == "__main__":
    main()
