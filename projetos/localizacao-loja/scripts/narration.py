"""Gera a narração com IA (Supertonic 3, rodando local) sincronizada com o voo do drone.

Modelo: sherpa-onnx-supertonic-3-tts-int8-2026-05-11 (release "tts-models" do k2-fsa/sherpa-onnx),
licença OpenRAIL-M (Supertone Inc.). Opcional: Whisper turbo (sherpa-onnx-whisper-turbo) para conferir
a pronúncia — se não estiver em .cache/asr, a conferência é pulada.

Lê src/timeline.json (momentos do voo), posiciona cada fala ancorada nesses momentos e grava:
  public/audio/narration.wav  — faixa da narração do tamanho do vídeo (44,1 kHz, mono)
  public/audio/narration.json — falas, palavras e blocos de legenda com início/fim em segundos
e atualiza "pullBack"/"end" em src/timeline.json conforme a duração das últimas falas.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
TTS_DIR = ROOT / ".cache/tts/sherpa-onnx-supertonic-3-tts-int8-2026-05-11"
ASR_DIR = ROOT / ".cache/asr/sherpa-onnx-whisper-turbo"
TIMELINE = ROOT / "src/timeline.json"
OUT = ROOT / "public/audio"

VOICE_SID = 0     # voz feminina F1 do Supertonic 3 (escolhida por timbre limpo e boa entonação)
SPEED = 1.12
SR = 44100

# Cada fala: lista de tokens; um token é "palavra" ou ("como aparece na legenda", "como é falado").
LINES = [
    {"id": "intro", "tokens": "Sabe onde fica a nossa loja aqui em Paragominas? Vem que eu te mostro!"},
    {"id": "centro", "tokens": ["Saindo", "do", "centro,", "da", "Praça", "Célio", "Miranda,", "siga", "até", "a", "rotatória", "da",
                                ("PA-125", "pê-á cento e vinte e cinco"), "e", "entre", "na", "Rua", "Equador,", "que", "vira", "a",
                                "Avenida", "Vinícius", "de", "Moraes."]},
    {"id": "reto", "tokens": "Aí é só seguir reto!"},
    {"id": "virada", "tokens": "No final da avenida, vire à esquerda na Barão de Araruna."},
    {"id": "chegou", "tokens": "Passou o Hospital São Paulo? Chegou!"},
    {"id": "endereco", "tokens": ["É", "o", "número", ("885,", "oitocentos e oitenta e cinco,"), "no", "Promissão:", "bem", "em",
                                  "frente", "à", "Júnior", "Bike,", "do", "ladinho", "da", "Vila", "Pet."]},
    {"id": "convite", "tokens": "Vem fazer uma visita, a gente te espera!"},
]


CLIPS = ROOT / ".cache/tts_clips"


def clip_path(line_id, spoken):
    import hashlib
    key = hashlib.sha1(f"{spoken}|{VOICE_SID}|{SPEED}|16".encode()).hexdigest()[:10]
    return CLIPS / f"{line_id}-{key}.wav"


def tokens_of(line):
    toks = line["tokens"]
    if isinstance(toks, str):
        toks = toks.split()
    return [(t, t) if isinstance(t, str) else t for t in toks]


def syllables(word):
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    # ditongos com 'i'/'u' átonos contam como uma sílaba: aproximação suficiente para legenda
    return max(1, n)


def make_tts():
    import sherpa_onnx
    d = TTS_DIR
    cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        supertonic=sherpa_onnx.OfflineTtsSupertonicModelConfig(
            duration_predictor=str(d / "duration_predictor.int8.onnx"), text_encoder=str(d / "text_encoder.int8.onnx"),
            vector_estimator=str(d / "vector_estimator.int8.onnx"), vocoder=str(d / "vocoder.int8.onnx"),
            tts_json=str(d / "tts.json"), unicode_indexer=str(d / "unicode_indexer.bin"), voice_style=str(d / "voice.bin")),
        num_threads=4, provider="cpu"))
    tts = sherpa_onnx.OfflineTts(cfg)

    def synth(text):
        g = sherpa_onnx.GenerationConfig()
        g.sid = VOICE_SID
        g.num_steps = 16
        g.speed = SPEED
        g.extra["lang"] = "pt"
        au = tts.generate(text, g)
        a = np.asarray(au.samples, np.float32)
        assert au.sample_rate == SR, au.sample_rate
        return a
    return synth


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def trim(a, thr_db=-42, pad=0.03):
    win = int(0.01 * SR)
    env = np.array([rms_db(a[i:i + win]) for i in range(0, len(a) - win, win)])
    on = np.where(env > thr_db)[0]
    s = max(0, on[0] * win - int(pad * SR))
    e = min(len(a), (on[-1] + 1) * win + int(pad * SR))
    out = a[s:e].copy()
    fade = int(0.006 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def pauses(a, thr_db=-38, min_len=0.09):
    """Intervalos de silêncio internos (s) de uma fala já aparada."""
    win = int(0.01 * SR)
    env = np.array([rms_db(a[i:i + win]) for i in range(0, len(a) - win, win)])
    quiet = env < thr_db
    out, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_len and i > 0 and j < len(quiet):
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def word_times(tokens, audio):
    """Distribui o tempo da fala entre as palavras: pausas detectadas casadas com a pontuação, e dentro
    de cada trecho, tempo proporcional ao número de sílabas faladas."""
    dur = len(audio) / SR
    gaps = pauses(audio)
    punct_idx = [i for i, (disp, _) in enumerate(tokens[:-1]) if re.search(r"[,.:;?!]$", disp)]
    # casa as maiores pausas com as pontuações, na ordem
    use = sorted(sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:len(punct_idx)])
    groups, start = [], 0
    for k, pi in enumerate(punct_idx[:len(use)]):
        groups.append((start, pi + 1))
        start = pi + 1
    groups.append((start, len(tokens)))
    bounds = [0.0]
    for g in use:
        bounds += [g[0], g[1]]
    bounds.append(dur)
    out = []
    for gi, (a, b) in enumerate(groups):
        t0, t1 = bounds[2 * gi], bounds[2 * gi + 1]
        syl = [sum(syllables(w) for w in sp.split()) + 0.6 for _, sp in tokens[a:b]]
        tot = sum(syl)
        t = t0
        for (disp, _), s in zip(tokens[a:b], syl):
            d = (t1 - t0) * s / tot
            out.append({"text": disp, "start": round(t, 3), "end": round(t + d, 3)})
            t += d
    return out


PARAKEET_DIR = ROOT / ".cache/asr/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"


def _norm_words(text):
    """Minúsculas, sem acento/pontuação, números por extenso — para casar roteiro e reconhecimento."""
    from num2words import num2words
    text = re.sub(r"\d+", lambda m: " " + num2words(int(m.group()), lang="pt_BR") + " ", text)
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", text.replace("-", " ")).split()


def make_aligner():
    """Tempos reais de cada palavra com o Parakeet TDT v3 (timestamps por token), se o modelo estiver presente."""
    if not PARAKEET_DIR.exists():
        return None
    import difflib
    import sherpa_onnx
    d = PARAKEET_DIR
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        str(d / "encoder.int8.onnx"), str(d / "decoder.int8.onnx"), str(d / "joiner.int8.onnx"), str(d / "tokens.txt"),
        num_threads=4, provider="cpu", decoding_method="greedy_search", model_type="nemo_transducer")

    def align(tokens, audio):
        pad = 0.5
        a = np.concatenate([np.zeros(int(pad * SR), np.float32), audio, np.zeros(int(pad * SR), np.float32)])
        x = np.interp(np.arange(0, len(a), SR / 16000), np.arange(len(a)), a).astype(np.float32)
        st = rec.create_stream()
        st.accept_waveform(16000, x)
        rec.decode_stream(st)
        r = st.result
        # junta sub-tokens em palavras (início de palavra vem marcado com espaço ou "▁")
        hyp = []
        for tok, ts, du in zip(r.tokens, r.timestamps, r.durations):
            if tok.startswith((" ", "▁")) or not hyp:
                hyp.append([tok.lstrip(" ▁"), ts - pad, ts + du - pad])
            else:
                hyp[-1][0] += tok
                hyp[-1][2] = ts + du - pad
        # cada palavra reconhecida pode virar várias normalizadas ("885" -> "oitocentos e oitenta e cinco")
        hyp_n = []
        for w, s0, e0 in hyp:
            parts = _norm_words(w) or [""]
            for k, p in enumerate(parts):
                frac0, frac1 = k / len(parts), (k + 1) / len(parts)
                hyp_n.append((p, s0 + (e0 - s0) * frac0, s0 + (e0 - s0) * frac1))
        # palavras faladas do roteiro, lembrando a qual token de legenda cada uma pertence
        spoken = []
        for i, (_, sp) in enumerate(tokens):
            for p in _norm_words(sp):
                spoken.append((p, i))
        sm = difflib.SequenceMatcher(a=[p for p, _ in spoken], b=[p for p, _, _ in hyp_n], autojunk=False)
        times = [None] * len(spoken)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                h = hyp_n[blk.b + k]
                times[blk.a + k] = (h[1], h[2])
        # interpola o que não casou
        known = [i for i, t in enumerate(times) if t]
        if not known:
            return None
        dur = len(audio) / SR
        for i in range(len(times)):
            if times[i] is None:
                prev = max([k for k in known if k < i], default=None)
                nxt = min([k for k in known if k > i], default=None)
                t0 = times[prev][1] if prev is not None else 0.0
                t1 = times[nxt][0] if nxt is not None else dur
                gap_n = (nxt if nxt is not None else len(times)) - (prev if prev is not None else -1) - 1
                pos = i - (prev if prev is not None else -1) - 1
                times[i] = (t0 + (t1 - t0) * pos / gap_n, t0 + (t1 - t0) * (pos + 1) / gap_n)
        out = []
        for i, (disp, _) in enumerate(tokens):
            ts = [times[k] for k, (_, ti) in enumerate(spoken) if ti == i]
            s0 = max(0.0, min(t[0] for t in ts))
            e0 = min(dur, max(t[1] for t in ts))
            out.append({"text": disp, "start": round(s0, 3), "end": round(max(e0, s0 + 0.05), 3)})
        matched = sum(1 for blk in sm.get_matching_blocks() for _ in range(blk.size))
        print(f"    alinhamento: {matched}/{len(spoken)} palavras casadas ({r.text.strip()})")
        return out
    return align


def caption_chunks(words, max_words=3, max_chars=20):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        text = " ".join(x["text"] for x in cur)
        if len(cur) >= max_words or len(text) >= max_chars or re.search(r"[,.:;?!]$", w["text"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [{"text": " ".join(x["text"] for x in c), "start": c[0]["start"], "end": c[-1]["end"],
             "words": c} for c in chunks]


def main():
    T = json.loads(TIMELINE.read_text())
    synth = make_tts()
    clips = {}
    for line in LINES:
        toks = tokens_of(line)
        spoken = " ".join(sp for _, sp in toks)
        # o Supertonic sorteia o ruído a cada chamada (o pip 2.0.0 ainda não aceita "seed"): guarda cada fala
        # gerada para que rodar o script de novo não mude a voz já aprovada
        cached = clip_path(line["id"], spoken)
        if cached.exists():
            audio, _ = sf.read(cached, dtype="float32")
        else:
            audio = trim(synth(spoken))
            cached.parent.mkdir(parents=True, exist_ok=True)
            sf.write(cached, audio, SR, subtype="FLOAT")
        clips[line["id"]] = (toks, audio)
        print(f"{line['id']:9} {len(audio) / SR:5.2f}s  {spoken}")
    dur = {k: len(v[1]) / SR for k, v in clips.items()}

    # posicionamento ancorado no voo
    start = {}
    start["intro"] = 0.45
    # a frase do trajeto começa já sobre a praça e termina quando a rota entra na Vinícius de Moraes
    start["centro"] = T["descentEnd"] + 1.0
    start["reto"] = start["centro"] + dur["centro"] + 0.45
    start["virada"] = T["turnAt"] + 0.55 - dur["virada"]
    start["chegou"] = T["arrive"] + 0.05 - dur["chegou"]
    start["endereco"] = T["arrive"] + 0.9
    start["convite"] = max(start["endereco"] + dur["endereco"] + 0.7, T["pullBack"] + 0.3)
    order = [l["id"] for l in LINES]
    for a, b in zip(order, order[1:]):
        gap = start[b] - (start[a] + dur[a])
        flag = "  <-- SOBREPOSIÇÃO!" if gap < 0.2 else ""
        print(f"  {a} -> {b}: folga {gap:5.2f}s{flag}")
        if gap < 0.2:
            sys.exit("Falas sobrepostas: ajuste src/timeline.json (ou SPEED) e rode de novo.")

    # o vídeo acaba 2,6 s depois do convite; o afastamento final começa logo após o endereço
    T["end"] = round(start["convite"] + dur["convite"] + 2.6, 2)
    T["pullBack"] = round(min(T["pullBack"], start["convite"] - 0.3), 2)
    TIMELINE.write_text(json.dumps(T, indent=2) + "\n")

    OUT.mkdir(parents=True, exist_ok=True)
    track = np.zeros(int(T["end"] * SR) + SR, np.float32)
    meta = {"voice": f"Supertonic 3 (sid {VOICE_SID}, velocidade {SPEED})", "lines": []}
    align = make_aligner()
    for line in LINES:
        toks, a = clips[line["id"]]
        a = a * (10 ** ((-19.0 - rms_db(a[np.abs(a) > 0.01])) / 20))  # nivela as falas entre si
        s = int(start[line["id"]] * SR)
        track[s:s + len(a)] += a
        local = (align(toks, a) if align else None) or word_times(toks, a)
        words = [{**w, "start": round(w["start"] + start[line["id"]], 3), "end": round(w["end"] + start[line["id"]], 3)}
                 for w in local]
        meta["lines"].append({"id": line["id"], "text": " ".join(d for d, _ in toks),
                              "start": round(start[line["id"]], 3), "end": round(start[line["id"]] + len(a) / SR, 3),
                              "words": words, "captions": caption_chunks(words)})
    track = track[:int(T["end"] * SR)]
    peak = np.abs(track).max()
    if peak > 0.98:
        track *= 0.98 / peak
    sf.write(OUT / "narration.wav", track, SR, subtype="PCM_16")
    (OUT / "narration.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"timeline: {T}")

    if ASR_DIR.exists():
        import sherpa_onnx
        asr = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(ASR_DIR / "turbo-encoder.int8.onnx"), decoder=str(ASR_DIR / "turbo-decoder.int8.onnx"),
            tokens=str(ASR_DIR / "turbo-tokens.txt"), language="pt", task="transcribe", num_threads=4)
        pad = np.zeros(int(0.6 * SR), np.float32)  # sem silêncio nas pontas o Whisper come a última palavra
        for line in LINES:
            a = np.concatenate([pad, clips[line["id"]][1], pad])
            x = np.interp(np.arange(0, len(a), SR / 16000), np.arange(len(a)), a).astype(np.float32)
            st = asr.create_stream()
            st.accept_waveform(16000, x)
            asr.decode_stream(st)
            print(f"  Whisper [{line['id']}]: {st.result.text.strip()}")


if __name__ == "__main__":
    main()
