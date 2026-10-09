"""Masteriza o áudio do vídeo renderizado e gera o arquivo de entrega.

Uso: python finalizar.py

Lê motion/out/video_bruto.mp4 e grava motion/out/atividade-fisica.mp4 com o áudio em -14 LUFS
(padrão de YouTube/Instagram) e pico máximo de -1,5 dBTP. O vídeo é copiado sem recodificar.
"""
import json
import os
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
ENTRADA = os.path.join(AQUI, "motion", "out", "video_bruto.mp4")
SAIDA = os.path.join(AQUI, "motion", "out", "atividade-fisica.mp4")
ALVO = "I=-14:TP=-1.5:LRA=11"


def main():
    # 1ª passada: mede o loudness
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", ENTRADA, "-af", f"loudnorm={ALVO}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    print(f"antes: {m['input_i']} LUFS, pico {m['input_tp']} dBTP")
    # 2ª passada: aplica a correção linear com os valores medidos
    filtro = (f"loudnorm={ALVO}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ENTRADA, "-c:v", "copy", "-af", filtro, "-ar", "48000",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", SAIDA], check=True)
    print(f"pronto: {SAIDA}")


if __name__ == "__main__":
    main()
