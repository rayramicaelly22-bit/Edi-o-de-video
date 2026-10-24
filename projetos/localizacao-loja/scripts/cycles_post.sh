#!/usr/bin/env bash
# Passo 2 (versão realista): junta os frames do Cycles (720x1280), amplia para 1080x1920 e dá um tratamento leve.
# Sem tilt-shift nem vinheta: a névoa atmosférica já vem do render (vinheta escurecia justamente a névoa do horizonte).
# Saída no mesmo arquivo que a composição final usa.
# Uso: scripts/cycles_post.sh [pasta_dos_frames] [saida.mp4]
set -euo pipefail
cd "$(dirname "$0")/.."
frames="${1:-out/cycles}"
out="${2:-public/render/drone3d_graded.mp4}"
n=$(ls "$frames"/frame_*.png | wc -l)
expected=$(python3 -c "import json; print(len(json.load(open('public/scene/frames.json'))['frames']))")
[ "$n" -eq "$expected" ] || { echo "faltam frames: $n de $expected em $frames" >&2; exit 1; }
mkdir -p "$(dirname "$out")"
ffmpeg -y -v error -framerate 30 -start_number 1 -i "$frames/frame_%04d.png" -vf "
scale=1080:1920:flags=lanczos,
unsharp=5:5:0.5:5:5:0,
eq=contrast=1.03:saturation=1.05,
format=yuv420p" -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart "$out"
echo "ok: $out ($n frames)"
