#!/usr/bin/env bash
# Passo 2: tratamento do voo 3D — tilt-shift (desfoque progressivo no topo e na base, "cara de drone"),
# nitidez no centro, contraste/saturação levemente maiores, toque quente e vinheta.
# Uso: scripts/grade.sh out/drone3d.mp4 public/render/drone3d_graded.mp4
set -euo pipefail
in="${1:-out/drone3d.mp4}"
out="${2:-public/render/drone3d_graded.mp4}"
here="$(cd "$(dirname "$0")" && pwd)"
mask="$(mktemp --suffix=.png)"
"${PYTHON:-python3}" "$here/tiltshift_mask.py" "$mask"
# maskedmerge mistura plano a plano: tudo em RGB planar (gbrp) para a máscara valer igual em R, G e B
ffmpeg -y -v error -i "$in" -i "$mask" -filter_complex "
[0:v]format=gbrp,unsharp=5:5:0.45:5:5:0,split=2[base][tmp];
[tmp]gblur=sigma=6:steps=2[blur];
[1:v]format=gbrp,scale=1080:1920[mask];
[base][blur][mask]maskedmerge,
eq=contrast=1.05:saturation=1.10:gamma=0.985,
colorbalance=rs=0.02:bs=-0.03:rm=0.01:bm=-0.015,
vignette=angle=PI/5,
format=yuv420p[v]" -map "[v]" -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart "$out"
rm -f "$mask"
echo "ok: $out"
