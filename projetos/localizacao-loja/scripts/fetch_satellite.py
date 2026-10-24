"""Baixa e compõe as texturas de satélite (Sentinel-2, cor natural) usadas no chão da cena 3D.

Gera em public/scene/:
  sat_region.jpg  — 49 km x 49 km, 24 m/px (descida do drone lá do alto)
  sat_city.jpg    — 12 km x 12 km, 3 m/px (reamostrado do original de 10 m)
e em .cache/:
  ndvi_detail.npz — NDVI de 10 m numa área de 6 km, para posicionar as árvores

Cada pixel vem da primeira cena da lista S2_SCENES em que ele está válido e sem nuvem/sombra.
Dados: Copernicus Sentinel-2 (ESA), processados pela Element 84 (Earth Search).
"""
import json
import os

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

from config import CACHE, ORIGIN_E, ORIGIN_N, PUBLIC, S2_BASE, S2_SCENES

os.environ.update(
    CURL_CA_BUNDLE=os.environ.get("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt"),
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    GDAL_HTTP_MULTIRANGE="YES",
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
)

BAD_SCL = [0, 1, 3, 8, 9, 10]  # sem dado, saturado, sombra de nuvem, nuvens, cirrus


def read_band(scene, name, bounds, shape, resampling):
    with rasterio.open(f"/vsicurl/{S2_BASE}/{scene}/{name}.tif") as ds:
        win = from_bounds(*bounds, ds.transform)
        return ds.read(window=win, out_shape=(ds.count, *shape), resampling=resampling,
                       boundless=True, fill_value=0)


def composite_tci(bounds, shape, resampling):
    out = np.zeros((3, *shape), np.uint8)
    filled = np.zeros(shape, bool)
    for scene in S2_SCENES:
        scl = read_band(scene, "SCL", bounds, shape, Resampling.nearest)[0]
        ok = ~np.isin(scl, BAD_SCL) & ~filled
        if ok.any():
            tci = read_band(scene, "TCI", bounds, shape, resampling)
            out[:, ok] = tci[:, ok]
            filled |= ok
        print(f"  {scene.split('/')[-1]}: preenchido {filled.mean():.3f}", flush=True)
        if filled.all():
            break
    return np.moveaxis(out, 0, -1)


def fill_nodata(rgb):
    """Preenche pixels sem dado (borda da passagem do satélite) com as cores vizinhas, borradas."""
    from scipy.ndimage import gaussian_filter
    hole = (rgb == 0).all(-1)
    if not hole.any():
        return rgb
    out = rgb.astype(np.float32)
    w = (~hole).astype(np.float32)
    for sigma in (8, 24, 64, 160):
        num = np.stack([gaussian_filter(out[..., c] * w, sigma) for c in range(3)], -1)
        den = gaussian_filter(w, sigma)[..., None]
        est = num / np.maximum(den, 1e-6)
        todo = hole & (den[..., 0] > 0.02)
        out[todo] = est[todo]
        w[todo] = 1.0
        hole &= ~todo
    return out.astype(np.uint8)


def grade(rgb):
    """Correção leve: contraste em S, saturação e um toque quente (luz de sol)."""
    x = rgb.astype(np.float32) / 255.0
    x = np.clip((x - 0.04) / 0.92, 0, 1)
    x = x * x * (3 - 2 * x) * 0.35 + x * 0.65  # S-curve suave
    lum = (x * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    x = lum + (x - lum) * 1.18
    x *= [1.03, 1.0, 0.95]
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)


def bounds_around(size_m):
    h = size_m / 2
    return (ORIGIN_E - h, ORIGIN_N - h, ORIGIN_E + h, ORIGIN_N + h)


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, size_m, px, res in [("sat_region", 49152, 2048, Resampling.average),
                                  ("sat_city", 12288, 4096, Resampling.cubic)]:
        print(name, flush=True)
        b = bounds_around(size_m)
        img = grade(fill_nodata(composite_tci(b, (px, px), res)))
        Image.fromarray(img).save(PUBLIC / f"{name}.jpg", quality=90, optimize=True)
        meta[name] = {"size_m": size_m, "px": px}

    print("ndvi", flush=True)
    b = bounds_around(6144)
    shape = (615, 615)
    nir = np.zeros(shape, np.float32); red = np.zeros(shape, np.float32); filled = np.zeros(shape, bool)
    for scene in S2_SCENES:
        scl = read_band(scene, "SCL", b, shape, Resampling.nearest)[0]
        ok = ~np.isin(scl, BAD_SCL) & ~filled
        if ok.any():
            nir[ok] = read_band(scene, "B08", b, shape, Resampling.bilinear)[0][ok]
            red[ok] = read_band(scene, "B04", b, shape, Resampling.bilinear)[0][ok]
            filled |= ok
        if filled.all():
            break
    # Collection 1 L2A: refletância = DN * 0,0001 - 0,1 (offset de 1000 no número digital)
    nir = nir * 1e-4 - 0.1
    red = red * 1e-4 - 0.1
    ndvi = (nir - red) / np.maximum(nir + red, 1e-3)
    np.savez_compressed(CACHE / "ndvi_detail.npz", ndvi=ndvi.astype(np.float16), bounds=np.array(b))
    json.dump(meta, open(CACHE / "satellite_meta.json", "w"), indent=1)
    print("ok", meta)


if __name__ == "__main__":
    main()
