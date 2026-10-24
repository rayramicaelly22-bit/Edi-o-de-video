"""Renderiza frames da cena .cache/cidade.blend (montada por blender_build.py) em PNG.

Uso: python scripts/blender_render.py [--frames 91,301 | --range 1-1081] [--out DIR] [--samples N] [--percent P]
                                      [--res WxH] [--threads T --part i/n] [--gpu] [--blur] [--max]
Frames já renderizados são pulados, então dá para interromper e retomar a renderização completa.
Com --part, cada processo pega um frame a cada n (ex.: dois processos com 2 threads cada, --part 0/2 e --part 1/2),
o que sobrepõe as etapas de preparação da cena, que usam um núcleo só.
Com placa de vídeo (--gpu), dá para subir a qualidade: --percent 200 renderiza direto em 1080x1920, e --blur liga o
desfoque de movimento da câmera. --max junta tudo: 1080x1920, 12 amostras, desfoque e denoiser no modo mais preciso
(~40 s por frame em 4 núcleos de CPU).
"""
import argparse
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("--frames", default=None, help="lista separada por vírgula (frames do Blender, 1 = início)")
ap.add_argument("--range", default=None, help="intervalo a-b")
ap.add_argument("--out", default=str(ROOT / "out/cycles"))
ap.add_argument("--samples", type=int, default=None)
ap.add_argument("--percent", type=int, default=None)
ap.add_argument("--res", default=None, help="resolução exata, ex.: 720x1280 (o pós amplia para 1080x1920)")
ap.add_argument("--blend", default=str(ROOT / ".cache/cidade.blend"))
ap.add_argument("--threads", type=int, default=0)
ap.add_argument("--part", default="0/1")
ap.add_argument("--gpu", action="store_true", help="usa a placa de vídeo (OptiX, CUDA, HIP, Metal ou oneAPI), se houver")
ap.add_argument("--blur", action="store_true", help="liga o desfoque de movimento da câmera")
ap.add_argument("--max", action="store_true", help="qualidade máxima: 1080x1920, 12 amostras, desfoque e denoiser preciso")
args = ap.parse_args()
if args.max:
    args.percent = args.percent or 200
    args.samples = args.samples or 12
    args.blur = True

bpy.ops.wm.open_mainfile(filepath=args.blend)
sc = bpy.context.scene
if args.samples:
    sc.cycles.samples = args.samples
if args.percent:
    sc.render.resolution_percentage = args.percent
if args.res:
    sc.render.resolution_x, sc.render.resolution_y = (int(v) for v in args.res.lower().split("x"))
    sc.render.resolution_percentage = 100
if args.threads:
    sc.render.threads_mode = "FIXED"
    sc.render.threads = args.threads
if args.blur:
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.35
    # só a câmera e o pin se movem: desfoque por objeto nos instanciadores e malhas paradas só custaria tempo
    for ob in bpy.data.objects:
        if ob.type != "CAMERA" and ob.name not in ("pin", "brilho_ponta"):
            ob.cycles.use_motion_blur = False
if args.max:
    sc.cycles.denoising_prefilter = "ACCURATE"
    sc.cycles.denoising_quality = "HIGH"
if args.gpu:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    chosen = None
    for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            chosen = kind
            break
    if chosen:
        sc.cycles.device = "GPU"
        print(f"GPU {chosen}: {', '.join(d.name for d in prefs.devices if d.use)}", flush=True)
    else:
        print("nenhuma GPU compatível encontrada; renderizando na CPU", flush=True)

if args.frames:
    frames = [int(x) for x in args.frames.split(",")]
elif args.range:
    a, b = (int(x) for x in args.range.split("-"))
    frames = list(range(a, b + 1))
else:
    frames = list(range(sc.frame_start, sc.frame_end + 1))

part, nparts = (int(x) for x in args.part.split("/"))
frames = frames[part::nparts]
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
todo = [f for f in frames if not (out / f"frame_{f:04d}.png").exists()]
print(f"{len(frames) - len(todo)} prontos, {len(todo)} a renderizar", flush=True)
t_start = time.time()
for i, f in enumerate(todo):
    t0 = time.time()
    sc.frame_set(f)
    sc.render.filepath = str(out / f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    eta = (time.time() - t_start) / (i + 1) * (len(todo) - i - 1)
    print(f"frame {f} {dt:.1f}s  ({i + 1}/{len(todo)}, faltam ~{eta / 60:.0f} min)", flush=True)
