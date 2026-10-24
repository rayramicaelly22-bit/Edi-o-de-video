#!/usr/bin/env bash
# Folha de contato para revisão: extrai frames nos instantes dados (s) e monta uma grade.
# Uso: scripts/contact_sheet.sh video.mp4 saida.jpg 0.5 3 6 ...
set -euo pipefail
video="$1"; out="$2"; shift 2
tmp="$(mktemp -d)"
i=0
for t in "$@"; do
  ffmpeg -v error -y -ss "$t" -i "$video" -frames:v 1 -vf "scale=360:-1,drawtext=text='${t}s':x=10:y=10:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6" "$tmp/$(printf %03d $i).png"
  i=$((i+1))
done
montage "$tmp"/*.png -tile "${COLS:-6}x" -geometry +4+4 -background "#222" "$out"
rm -rf "$tmp"
echo "ok: $out"
