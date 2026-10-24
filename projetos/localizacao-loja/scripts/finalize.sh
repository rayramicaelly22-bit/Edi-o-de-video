#!/usr/bin/env bash
# Passo 4: renderiza o motion graphics por cima do voo tratado e junta o áudio mixado.
# Loudness final: -14 LUFS integrados, pico real -1,5 dBTP (padrão de Reels/Stories).
# Uso: scripts/finalize.sh [saida.mp4]
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:-out/localizacao-loja.mp4}"
# Chromium já instalado (ambiente sem download); fora dele a Remotion usa o próprio Chrome Headless Shell
browser="${REMOTION_BROWSER:-/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell}"
browser_flag=()
[ -x "$browser" ] && browser_flag=(--browser-executable="$browser")
[ "${SKIP_RENDER:-0}" = 1 ] || npx remotion render LocalizacaoLoja out/video_sem_audio.mp4 --gl=swangle --concurrency=4 --crf=16 \
  "${browser_flag[@]}" --muted --log=error
# loudnorm em duas passadas (medição + correção linear)
stats=$(ffmpeg -hide_banner -nostats -i public/audio/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$stats" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_i'])")
mtp=$(echo "$stats" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_tp'])")
mlra=$(echo "$stats" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_lra'])")
mth=$(echo "$stats" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_thresh'])")
# o áudio é completado com silêncio até a duração exata do vídeo (sem cortar os últimos frames);
# o vídeo é reencodado num tamanho bom para o celular (o Instagram recomprime de qualquer jeito)
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 out/video_sem_audio.mp4)
ffmpeg -y -v error -i out/video_sem_audio.mp4 -i public/audio/mix.wav \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$mi:measured_TP=$mtp:measured_LRA=$mlra:measured_thresh=$mth:linear=true,aresample=48000,apad" \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 19 -maxrate 18M -bufsize 36M -profile:v high -level 4.2 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -t "$dur" -movflags +faststart "$out"
echo "ok: $out"
