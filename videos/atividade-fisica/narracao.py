"""Gera a narração com a voz de IA (Kokoro) e a linha do tempo do vídeo.

Uso: python narracao.py <pasta-dos-modelos-kokoro>

Saídas:
  motion/public/narracao.wav  -> faixa de voz completa, já com as pausas
  motion/src/timeline.json    -> início/fim de cada cena, fala, palavra e legenda (em segundos)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import pyloudnorm
from kokoro_onnx import Kokoro
from pedalboard import Compressor, HighpassFilter, Pedalboard, PeakFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
SR = 24000
# loudness da voz tratada (a mixagem final fica perto de -14 LUFS, padrão de YouTube/Instagram)
LUFS_VOZ = -15.0

# peso extra (em fonemas) da pausa que a voz faz depois de cada pontuação
PESO_PAUSA = {",": 4, ":": 6, ".": 9, "?": 9, "!": 9}
# legenda: tamanho máximo de cada bloco e palavras que não devem fechar um bloco
LEG_CARACTERES = 46
NUMEROS = {"um", "uma", "dois", "duas", "três", "cinco", "sete", "oito", "nove", "dez", "dezessete", "dezenove", "vinte",
           "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "cento", "trezentos", "mil", "novecentos"}
# palavras que continuam um número ("vinte | e dois", "dezenove | por cento")
CONTINUA = {"e", "a", "por", "cento", "mil", "vírgula", "bilhão", "anos", "minutos", "passos", "horas", "dias"}
FRACAS = {"a", "o", "as", "os", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "um", "uma",
          "que", "com", "por", "para", "se", "ao", "à", "seu", "sua", "mais", "não", "é", "ou", "só"}


def aparar(audio, limiar_db=-42, folga=0.03):
    # tira o silêncio do começo e do fim, deixando uma folga pequena
    nivel = 20 * np.log10(np.abs(audio) + 1e-9)
    acima = np.where(nivel > limiar_db)[0]
    if len(acima) == 0:
        return audio
    ini = max(acima[0] - int(folga * SR), 0)
    fim = min(acima[-1] + int(folga * SR), len(audio))
    return audio[ini:fim]


def tempos_das_palavras(kokoro, texto, duracao):
    # estimativa: cada palavra ocupa tempo proporcional ao número de fonemas,
    # e a pontuação soma o peso da pausa que a voz faz
    palavras = texto.split()
    pesos = []
    for p in palavras:
        limpa = re.sub(r"[^\wÀ-ÿ-]", "", p)
        fon = re.sub(r"[ˈˌ\s]", "", kokoro.tokenizer.phonemize(limpa, "pt-br")) if limpa else ""
        pausa = PESO_PAUSA.get(p[-1], 0)
        pesos.append((max(len(fon), 1), pausa))
    total = sum(f + q for f, q in pesos)
    t, out = 0.0, []
    for p, (f, q) in zip(palavras, pesos):
        ini = t
        fim = ini + duracao * f / total
        t = fim + duracao * q / total
        out.append({"w": p, "s": round(ini, 3), "e": round(fim, 3)})
    return out


def _texto(ws):
    return " ".join(w["w"] for w in ws)


def _dividir(frase, partes):
    # corta a frase em `partes` blocos de tamanho parecido, sem terminar bloco em palavra fraca
    if partes <= 1 or len(frase) < 2:
        return [frase]
    alvo = len(_texto(frase)) / partes
    melhor = None
    for i in range(1, len(frase)):
        ant = re.sub(r"\W", "", frase[i - 1]["w"].lower())
        prox = re.sub(r"\W", "", frase[i]["w"].lower())
        if ant in FRACAS or (ant in NUMEROS and prox in CONTINUA):
            continue
        custo = abs(len(_texto(frase[:i])) - alvo)
        if melhor is None or custo < melhor[0]:
            melhor = (custo, i)
    i = melhor[1] if melhor else len(frase) // 2
    return [frase[:i]] + _dividir(frase[i:], partes - 1)


def blocos_de_legenda(palavras):
    # 1) corta na pontuação
    frases, atual = [], []
    for w in palavras:
        atual.append(w)
        if w["w"][-1] in ".,?!:;":
            frases.append(atual)
            atual = []
    if atual:
        frases.append(atual)
    # 2) junta pedaços vizinhos da mesma frase enquanto couberem
    juntas = []
    for f in frases:
        if juntas and juntas[-1][-1]["w"][-1] not in ".?!" and len(_texto(juntas[-1] + f)) <= LEG_CARACTERES:
            juntas[-1] = juntas[-1] + f
        else:
            juntas.append(f)
    # 3) divide os longos em blocos equilibrados
    blocos = []
    for f in juntas:
        for b in _dividir(f, -(-len(_texto(f)) // LEG_CARACTERES)):
            blocos.append({"texto": _texto(b), "s": b[0]["s"], "e": b[-1]["e"]})
    return blocos


def tratar(voz, destino):
    # limpa o grave, dá presença e comprime; depois acerta o volume e segura os picos
    # com o limitador do FFmpeg (o Limiter do pedalboard aplica ganho de compensação)
    cadeia = Pedalboard([
        HighpassFilter(75),
        PeakFilter(cutoff_frequency_hz=3200, gain_db=2.0, q=0.9),
        Compressor(threshold_db=-24, ratio=3, attack_ms=4, release_ms=70),
    ])
    voz = cadeia(voz.astype(np.float32), SR).reshape(-1)
    voz *= 10 ** ((LUFS_VOZ - pyloudnorm.Meter(SR).integrated_loudness(voz)) / 20)
    with tempfile.TemporaryDirectory() as tmp:
        bruto = os.path.join(tmp, "voz.f32")
        voz.astype(np.float32).tofile(bruto)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", bruto,
                        "-af", "alimiter=limit=0.84:attack=3:release=60:level=disabled",
                        "-ar", "48000", "-c:a", "pcm_s16le", destino], check=True)


def main():
    modelos = sys.argv[1]
    roteiro = json.load(open(os.path.join(AQUI, "roteiro.json"), encoding="utf-8"))
    kokoro = Kokoro(os.path.join(modelos, "kokoro-v1.0.onnx"), os.path.join(modelos, "voices-v1.0.bin"))

    trilha = []  # pedaços de áudio na ordem
    t = 0.0
    cenas = []
    legendas = []

    def silencio(seg):
        nonlocal t
        trilha.append(np.zeros(int(round(seg * SR)), dtype=np.float32))
        t += len(trilha[-1]) / SR

    for cena in roteiro["cenas"]:
        ini_cena = t
        silencio(cena.get("pausaAntes", 0))
        falas = []
        for n, fala in enumerate(cena["falas"]):
            if n:
                silencio(roteiro["pausaEntreFalas"])
            audio, sr = kokoro.create(fala["texto"], voice=roteiro["voz"], speed=roteiro["velocidade"], lang="pt-br")
            assert sr == SR
            audio = aparar(audio.astype(np.float32))
            dur = len(audio) / SR
            palavras = tempos_das_palavras(kokoro, fala["texto"], dur)
            for w in palavras:
                w["s"] = round(w["s"] + t, 3)
                w["e"] = round(w["e"] + t, 3)
            falas.append({"id": fala["id"], "texto": fala["texto"], "s": round(t, 3), "e": round(t + dur, 3), "palavras": palavras})
            legendas += blocos_de_legenda(palavras)
            trilha.append(audio)
            t += dur
            print(f"{fala['id']}  {dur:5.2f}s  {fala['texto'][:60]}")
        silencio(cena.get("pausaDepois", 0))
        falta = cena.get("duracaoMinima", 0) - (t - ini_cena)
        if falta > 0:
            silencio(falta)
        cenas.append({"id": cena["id"], "s": round(ini_cena, 3), "falas": falas})

    for i, c in enumerate(cenas):
        c["e"] = cenas[i + 1]["s"] if i + 1 < len(cenas) else round(t, 3)

    os.makedirs(os.path.join(AQUI, "motion", "public"), exist_ok=True)
    tratar(np.concatenate(trilha), os.path.join(AQUI, "motion", "public", "narracao.wav"))

    timeline = {"duracao": round(t, 3), "cenas": cenas, "legendas": legendas}
    with open(os.path.join(AQUI, "motion", "src", "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=1)
    print(f"duração total: {t:.1f}s ({int(t // 60)}:{t % 60:04.1f})")


if __name__ == "__main__":
    main()
