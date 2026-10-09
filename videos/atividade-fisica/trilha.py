"""Compõe a trilha de fundo e os efeitos sonoros (tudo sintetizado aqui, sem direitos de terceiros).

Uso: python trilha.py   (depois de rodar narracao.py, porque a trilha segue a timeline)

Saídas:
  motion/public/trilha.wav       -> música, 120 BPM, com o "drop" no título
  motion/public/sfx/*.wav        -> whoosh, impacto e pop das animações
"""
import json
import os
import wave

import numpy as np
from pedalboard import Compressor, Delay, HighpassFilter, LowpassFilter, PeakFilter, Pedalboard, Reverb
from scipy.signal import butter, sosfilt

AQUI = os.path.dirname(os.path.abspath(__file__))
SR = 48000
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)

# vi - IV - I - V em Ré maior (Si menor, Sol, Ré, Lá): baixo, acorde do pad e notas do pluck
ACORDES = [
    {"baixo": 47, "pad": [59, 62, 66, 69], "pluck": [71, 74, 78, 81]},  # Bm7
    {"baixo": 43, "pad": [59, 62, 67, 66], "pluck": [71, 74, 79, 78]},  # Gmaj7
    {"baixo": 50, "pad": [57, 62, 66, 69], "pluck": [69, 74, 78, 81]},  # D
    {"baixo": 45, "pad": [57, 61, 64, 69], "pluck": [69, 73, 76, 81]},  # A
]
FINAL = {"baixo": 38, "pad": [57, 62, 66, 69, 74], "pluck": [74, 78, 81, 86]}  # D aberto
# ritmo do pluck em semicolcheias dentro do compasso
PLUCK_RITMO = [0, 3, 6, 8, 10, 12, 14]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def serra(freq, n, fase=0.0):
    # dente de serra com PolyBLEP (sem aliasing áspero)
    dt = freq / SR
    p = (fase + dt * np.arange(n)) % 1.0
    y = 2 * p - 1
    a = p < dt
    t = p[a] / dt
    y[a] -= t + t - t * t - 1
    b = p > 1 - dt
    t = (p[b] - 1) / dt
    y[b] -= t * t + t + t + 1
    return y


def envelope(n, ataque, decaimento, sustentacao, soltura):
    t = np.arange(n) / SR
    dur = n / SR
    env = np.where(t < ataque, t / max(ataque, 1e-4),
                   sustentacao + (1 - sustentacao) * np.exp(-(t - ataque) / max(decaimento, 1e-4)))
    fim = dur - soltura
    env = np.where(t > fim, env * np.clip((dur - t) / max(soltura, 1e-4), 0, 1), env)
    return env


def passa(sig, tipo, corte, ordem=2):
    sos = butter(ordem, corte, btype=tipo, fs=SR, output="sos")
    return sosfilt(sos, sig)


class Faixa:
    def __init__(self, dur):
        self.buf = np.zeros((2, int(dur * SR) + SR))

    def soma(self, sig, inicio, pan=0.0, ganho=1.0):
        i = int(round(inicio * SR))
        if i >= self.buf.shape[1]:
            return
        if i < 0:
            sig = sig[..., -i:]
            i = 0
        if sig.ndim == 1:
            esq, dir_ = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
            sig = np.vstack([sig * esq * 1.414, sig * dir_ * 1.414])
        n = min(sig.shape[1], self.buf.shape[1] - i)
        self.buf[:, i:i + n] += sig[:, :n] * ganho


# ---------- instrumentos ----------

def bumbo():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t / 0.035)
    corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.26)
    clique = passa(rng.standard_normal(n), "highpass", 3000) * np.exp(-t / 0.004) * 0.25
    return np.tanh(1.6 * (corpo + clique)) * 0.9


def palma():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    ruido = passa(rng.standard_normal(n), "bandpass", [900, 4500])
    env = np.zeros(n)
    for k, atraso in enumerate([0, 0.011, 0.022]):
        env += np.where(t >= atraso, np.exp(-(t - atraso) / (0.008 if k < 2 else 0.16)), 0)
    return ruido * env * 0.5


def chimbal(aberto=False):
    n = int((0.3 if aberto else 0.08) * SR)
    t = np.arange(n) / SR
    ruido = passa(rng.standard_normal(n), "highpass", 7500, 4)
    return ruido * np.exp(-t / (0.11 if aberto else 0.022)) * 0.35


def shaker():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    ruido = passa(rng.standard_normal(n), "bandpass", [5000, 11000])
    return ruido * np.sin(np.pi * t / t[-1]) ** 2 * 0.18


def pad(notas, dur, brilho=2600):
    n = int(dur * SR)
    out = np.zeros((2, n))
    for m in notas:
        for k, cents in enumerate([-16, -9, -4, 0, 4, 9, 16]):
            v = serra(hz(m) * 2 ** (cents / 1200), n, rng.random())
            out[k % 2] += v
    out = np.vstack([passa(out[0], "lowpass", brilho), passa(out[1], "lowpass", brilho)])
    return out * envelope(n, 0.35, 0.6, 0.85, 0.5) / (len(notas) * 4.5)


def baixo(nota, dur):
    n = int(dur * SR)
    sub = np.sin(2 * np.pi * hz(nota) * np.arange(n) / SR)
    grave = passa(serra(hz(nota), n), "lowpass", 420)
    return (0.75 * sub + 0.45 * grave) * envelope(n, 0.01, 0.25, 0.8, 0.08)


def pluck(nota, dur=0.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    bruto = 0.6 * serra(hz(nota), n) + 0.4 * np.sign(np.sin(2 * np.pi * hz(nota) * t))
    escuro = passa(bruto, "lowpass", 900)
    claro = passa(bruto, "lowpass", 5200)
    filtro = np.exp(-t / 0.06)
    return (escuro + (claro - escuro) * filtro) * np.exp(-t / 0.13) * 0.32


def subida(dur):
    # riser: ruído com filtro abrindo + volume crescendo
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    bloco = 2048
    ruido = rng.standard_normal(n)
    for i in range(0, n, bloco):
        frac = i / n
        centro = 400 * (9000 / 400) ** frac
        out[i:i + bloco] = passa(ruido[i:i + bloco], "bandpass", [centro * 0.7, min(centro * 1.4, 20000)])
    return out * (t / dur) ** 2 * 0.5


def impacto():
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    f = 38 + 60 * np.exp(-t / 0.08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    prato = passa(rng.standard_normal(n), "highpass", 2500) * np.exp(-t / 0.45) * 0.35
    return np.tanh(1.3 * boom) * 0.8 + prato


def bombeamento(n, inicios_bumbo, profundidade=0.55):
    # sidechain: o volume afunda a cada bumbo e volta em ~200 ms
    env = np.ones(n)
    curva = 1 - profundidade * np.exp(-np.arange(int(0.45 * SR)) / SR / 0.12)
    for k in inicios_bumbo:
        i = int(round(k * SR))
        j = min(i + len(curva), n)
        if i < n:
            env[i:j] = np.minimum(env[i:j], curva[:j - i])
    return env


# ---------- arranjo ----------

def main():
    tl = json.load(open(os.path.join(AQUI, "motion", "src", "timeline.json"), encoding="utf-8"))
    cenas = {c["id"]: c for c in tl["cenas"]}
    l03 = cenas["gancho"]["falas"][-1]
    drop = next(w["s"] for w in l03["palavras"] if w["w"].startswith("Atividade"))
    dur = tl["duracao"] + 0.5
    quebra_ini = cenas["dezmil"]["s"]
    escuro = (cenas["mundo"]["s"], cenas["dezmil"]["s"])
    ultima_fala = cenas["fechamento"]["falas"][-1]["e"]

    primeiro = int(np.floor(-drop / BAR))
    # o acorde final cai no primeiro compasso depois da última frase
    ultimo = int(np.ceil((ultima_fala + 0.2 - drop) / BAR))
    t_fim = drop + ultimo * BAR
    # compasso do breakdown: o primeiro que começa depois do início das curiosidades
    quebra = int(np.ceil((quebra_ini - drop) / BAR))

    bateria, graves, pads, plucks, efeitos = (Faixa(dur) for _ in range(5))
    k_bumbo, k_palma = bumbo(), palma()
    bumbos = []

    for b in range(primeiro, ultimo):
        t0 = drop + b * BAR
        ac = ACORDES[b % 4]
        intro = b < 0
        pausa_bateria = quebra <= b < quebra + 2

        # pad em todo o vídeo (na intro, mais fechado)
        brilho = 900 + 1700 * (b - primeiro) / max(-primeiro, 1) if intro else (1500 if pausa_bateria else 2600)
        pads.soma(pad(ac["pad"], BAR + 0.5, brilho), t0, ganho=0.9 if intro else 1.0)

        if not intro and not pausa_bateria:
            for beat in range(4):
                tb = t0 + beat * BEAT
                bateria.soma(k_bumbo, tb, ganho=0.95)
                bumbos.append(tb)
                bateria.soma(chimbal(True), tb + BEAT / 2, pan=0.25, ganho=0.55)
                if beat in (1, 3):
                    bateria.soma(k_palma, tb, pan=-0.05, ganho=0.8)
                for s in range(4):
                    bateria.soma(shaker(), tb + s * BEAT / 4, pan=-0.35, ganho=0.6 if s % 2 else 0.35)
            # baixo: nota longa + repique na contratempo
            graves.soma(baixo(ac["baixo"], BAR - 0.05), t0, ganho=0.9)
            for beat in range(4):
                graves.soma(baixo(ac["baixo"] + 12, 0.18), t0 + beat * BEAT + BEAT / 2, ganho=0.25)

        # pluck: entra 4 compassos antes do drop e some na parte dos dados "pesados"
        sem_pluck = escuro[0] <= t0 < escuro[1]
        if b >= -4 and not sem_pluck:
            for i, s in enumerate(PLUCK_RITMO):
                nota = ac["pluck"][i % len(ac["pluck"])]
                plucks.soma(pluck(nota), t0 + s * BEAT / 4, pan=(-0.4 if i % 2 else 0.4), ganho=0.5 if intro else 0.75)

    # final: acorde de Ré sustentado enquanto as fontes aparecem
    resto = dur - t_fim
    pads.soma(pad(FINAL["pad"], resto, 2200) * np.linspace(1, 0, int(resto * SR)), t_fim)
    graves.soma(baixo(FINAL["baixo"], min(resto, 3.0)), t_fim, ganho=0.9)
    efeitos.soma(impacto(), t_fim, ganho=0.6)
    for i, nota in enumerate(FINAL["pluck"]):
        plucks.soma(pluck(nota, 0.6), t_fim + i * BEAT / 2, pan=(-0.3 if i % 2 else 0.3), ganho=0.7)

    # riser antes do drop, impacto no drop e risers curtos antes da volta do breakdown
    efeitos.soma(subida(2 * BAR), drop - 2 * BAR, ganho=0.6)
    efeitos.soma(impacto(), drop, ganho=0.9)
    volta = drop + (quebra + 2) * BAR
    efeitos.soma(subida(BAR), volta - BAR, ganho=0.5)
    efeitos.soma(impacto(), volta, ganho=0.5)

    # sidechain no pad e no baixo
    n = pads.buf.shape[1]
    pads.buf *= bombeamento(n, bumbos)
    graves.buf *= bombeamento(n, bumbos, 0.7)

    # efeitos por grupo
    pads.buf = Pedalboard([Reverb(room_size=0.7, wet_level=0.3, dry_level=0.8, width=1.0)])(pads.buf.astype(np.float32), SR)
    plucks.buf = Pedalboard([HighpassFilter(300), Delay(delay_seconds=BEAT * 0.75, feedback=0.3, mix=0.25),
                             Reverb(room_size=0.55, wet_level=0.25, dry_level=0.85)])(plucks.buf.astype(np.float32), SR)
    bateria.buf = Pedalboard([Reverb(room_size=0.25, wet_level=0.08, dry_level=1.0)])(bateria.buf.astype(np.float32), SR)
    efeitos.buf = Pedalboard([Reverb(room_size=0.8, wet_level=0.3, dry_level=0.8)])(efeitos.buf.astype(np.float32), SR)

    mix = bateria.buf * 0.8 + graves.buf * 0.75 + pads.buf * 0.55 + plucks.buf * 0.6 + efeitos.buf * 0.7
    # abre espaço para a voz (1–4 kHz) e cola a mixagem; o volume final é ajustado no vídeo
    master = Pedalboard([
        HighpassFilter(30),
        PeakFilter(cutoff_frequency_hz=2400, gain_db=-4.0, q=0.7),
        LowpassFilter(16000),
        Compressor(threshold_db=-18, ratio=2.5, attack_ms=10, release_ms=150),
    ])
    mix = master((mix / np.max(np.abs(mix)) * 0.7).astype(np.float32), SR)
    mix *= 0.89 / np.max(np.abs(mix))  # pico em -1 dBFS
    # fade-in curto no começo
    fi = int(0.4 * SR)
    mix[:, :fi] *= np.linspace(0, 1, fi)
    salvar(os.path.join(AQUI, "motion", "public", "trilha.wav"), mix[:, :int(dur * SR)])

    # efeitos das animações
    pasta = os.path.join(AQUI, "motion", "public", "sfx")
    os.makedirs(pasta, exist_ok=True)
    salvar(os.path.join(pasta, "whoosh.wav"), whoosh())
    salvar(os.path.join(pasta, "pop.wav"), pop())
    salvar(os.path.join(pasta, "impacto.wav"), np.vstack([impacto()] * 2) * 0.8)
    print(f"trilha: {dur:.1f}s | drop em {drop:.2f}s | breakdown em {drop + quebra * BAR:.1f}s | final em {t_fim:.1f}s")


def whoosh():
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    ruido = rng.standard_normal(n)
    out = np.zeros(n)
    bloco = 1024
    for i in range(0, n, bloco):
        frac = i / n
        centro = 600 + 3800 * np.sin(np.pi * frac)
        out[i:i + bloco] = passa(ruido[i:i + bloco], "bandpass", [centro * 0.6, centro * 1.5])
    env = np.sin(np.pi * t / t[-1]) ** 1.5
    pan = np.linspace(-0.8, 0.8, n)
    return np.vstack([out * env * (1 - pan) / 2, out * env * (1 + pan) / 2]) * 0.9


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t / 0.03) + 300
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03)
    return np.vstack([s, s]) * 0.6


def salvar(caminho, audio):
    audio = np.clip(audio, -1, 1)
    with wave.open(caminho, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio.T * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    main()
