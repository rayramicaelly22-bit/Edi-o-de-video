"""Gera a geometria 3D da cena (ruas, prédios, água, árvores) e o scene.json com rota e pontos.

Entradas (.cache/): Overture Maps (parquet), route.geojson, ndvi_detail.npz e public/scene/sat_city.jpg
Saídas (public/scene/): <camada>.bin + scene.json (manifesto com offsets dos buffers)

Coordenadas locais em metros: x = leste, y = altura, z = -norte, origem em config.ORIGIN_LL.
"""
import hashlib
import json
import math

import numpy as np
import pyarrow.parquet as pq
import shapely
import shapely.ops
from PIL import Image
from shapely import STRtree, from_wkb

from config import (CACHE, HOSPITAL_SAO_PAULO, LAGO_VERDE, ORIGIN_E, ORIGIN_LL, ORIGIN_N,
                    PRACA_CELIO_MIRANDA, PUBLIC, STORE_ALONG_M, STORE_NUMBER, STORE_SIDE_OFFSET_M,
                    to_utm)

OV = CACHE / "overture"
DETAIL_HALF = 3072.0  # metade do lado da área com geometria 3D (6,1 km)


def rand01(key, salt=""):
    """Pseudoaleatório determinístico a partir de um texto (id do Overture)."""
    return int(hashlib.md5((key + salt).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def to_local(geom):
    def f(c):
        e, n = to_utm(c[:, 0], c[:, 1])
        return np.column_stack([np.asarray(e) - ORIGIN_E, np.asarray(n) - ORIGIN_N])
    return shapely.transform(geom, f)  # (x = leste, y = norte); vira (x, -z) na exportação


def inside_detail(g, margin=0.0):
    x0, y0, x1, y1 = g.bounds
    h = DETAIL_HALF + margin
    return x1 > -h and x0 < h and y1 > -h and y0 < h


class Layer:
    """Acumula triângulos (posição, normal, cor) de uma camada e exporta como buffers binários."""

    def __init__(self):
        self.pos, self.nrm, self.col = [], [], []

    def add(self, tri_xyz, normal, color):
        self.pos.append(np.asarray(tri_xyz, np.float32).reshape(-1, 3))
        n = np.broadcast_to(np.asarray(normal, np.float32), (len(self.pos[-1]), 3))
        self.nrm.append(n)
        c = np.asarray(color, np.float32)
        self.col.append(np.broadcast_to(c, (len(self.pos[-1]), 3)) if c.ndim == 1 else c)

    def export(self, name, blob, manifest):
        if not self.pos:
            return
        pos = np.concatenate(self.pos).astype(np.float32)
        nrm = np.clip(np.concatenate(self.nrm) * 127, -127, 127).astype(np.int8)
        col = np.clip(np.concatenate(self.col) * 255, 0, 255).astype(np.uint8)
        entry = {"count": len(pos)}
        for key, arr in [("position", pos), ("normal", nrm), ("color", col)]:
            while len(blob) % 4:
                blob.append(0)
            entry[key] = {"offset": len(blob), "length": arr.size, "type": arr.dtype.name}
            blob.extend(arr.tobytes())
        manifest[name] = entry
        print(f"  {name}: {len(pos) // 3} triângulos")


def flat_triangles(poly, y):
    """Triangula um polígono (com buracos) no plano y, devolvendo vértices (x, y, z)."""
    tris = shapely.constrained_delaunay_triangles(poly)
    out = []
    for t in tris.geoms:
        c = np.asarray(t.exterior.coords)[:3]
        # garante orientação anti-horária vista de cima (normal +y no espaço da cena)
        if (c[1, 0] - c[0, 0]) * (c[2, 1] - c[0, 1]) - (c[1, 1] - c[0, 1]) * (c[2, 0] - c[0, 0]) < 0:
            c = c[::-1]
        out.append([(p[0], y, -p[1]) for p in c])
    return np.asarray(out, np.float32).reshape(-1, 3)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


# ---------------------------------------------------------------- satélite (amostragem de cor)
SAT = np.asarray(Image.open(PUBLIC / "sat_city.jpg").convert("RGB"), np.float32) / 255
SAT_SIZE = 12288.0


def sat_sample(x, y):
    """Cor do satélite (cidade, 3 m/px) no ponto local (x leste, y norte)."""
    px = (np.asarray(x) / SAT_SIZE + 0.5) * SAT.shape[1]
    py = (0.5 - np.asarray(y) / SAT_SIZE) * SAT.shape[0]
    px = np.clip(px.astype(int), 0, SAT.shape[1] - 1)
    py = np.clip(py.astype(int), 0, SAT.shape[0] - 1)
    return SAT[py, px]


# ---------------------------------------------------------------- ruas
ROAD_WIDTH = {"trunk": 15, "primary": 13, "secondary": 12, "tertiary": 10.5, "unclassified": 8,
              "residential": 7.5, "living_street": 6, "service": 4.5, "unknown": 6, "track": 4.5}
PATH_WIDTH = {"footway": 2.2, "path": 1.8, "cycleway": 2.2}
UNPAVED = {"unpaved", "dirt", "gravel", "ground", "sand", "earth", "compacted"}


def build_roads():
    paved, unpaved, paths, centerlines = [], [], [], []
    for r in pq.read_table(OV / "segments.parquet").to_pylist():
        if r["subtype"] != "road":
            continue
        g = to_local(from_wkb(r["geometry"]))
        if not inside_detail(g, 300):
            continue
        cls = r["class"]
        surf = {s["value"] for s in (r["road_surface"] or [])}
        if cls in PATH_WIDTH:
            paths.append(g.buffer(PATH_WIDTH[cls] / 2, quad_segs=3))
            continue
        w = ROAD_WIDTH.get(cls, 6)
        (unpaved if (surf & UNPAVED or cls == "track") else paved).append(g.buffer(w / 2, quad_segs=4))
        if cls in ("primary", "trunk", "secondary", "tertiary") and not (surf & UNPAVED):
            centerlines.append(g)
    clip = shapely.box(-DETAIL_HALF, -DETAIL_HALF, DETAIL_HALF, DETAIL_HALF)
    paved_u = shapely.union_all(paved).intersection(clip)
    unpaved_u = shapely.union_all(unpaved).difference(paved_u).intersection(clip)
    walk_u = shapely.union_all(paths).difference(paved_u).difference(unpaved_u).intersection(clip)
    # calçada/meio-fio: faixa clara em volta do asfalto
    curb_u = paved_u.buffer(1.6, quad_segs=3).difference(paved_u).difference(unpaved_u).intersection(clip)
    return paved_u, unpaved_u, walk_u, curb_u, centerlines


def dashes(lines, dash=3.0, gap=6.0, width=0.22):
    """Faixa central tracejada (branca) nas avenidas."""
    polys = []
    for g in lines:
        for part in getattr(g, "geoms", [g]):
            d = 0.0
            while d < part.length - dash:
                seg = shapely.ops.substring(part, d, d + dash)
                polys.append(seg.buffer(width / 2, cap_style="flat"))
                d += dash + gap
    return shapely.union_all(polys) if polys else shapely.GeometryCollection()


# ---------------------------------------------------------------- prédios
WALLS = ["#f2ede3", "#efe6d2", "#e9dcc3", "#f4efe8", "#e3e7e8", "#efe2cf", "#e8d9d2", "#dfe6d6",
         "#f6f3ee", "#e6dccb", "#f0d9b5", "#d9e3ea"]
ROOF_TILE = ["#b45a34", "#a64f2f", "#bf6a40", "#9e4a2e", "#c47450", "#ad5c3b"]
ROOF_METAL = ["#d4d6d6", "#c9cdcf", "#dedcd6", "#bfc4c6"]
ROOF_FIBER = ["#9a9c9b", "#8b8f90", "#a7a8a5", "#7f8486"]


def building_style(bid, poly, area):
    u = rand01(bid)
    if area < 40:
        h = 2.8 + 0.6 * u
    elif area < 260:
        h = 3.4 + 0.9 * u
        if rand01(bid, "2") < 0.10:
            h = 6.2 + 0.8 * u  # sobrado
    elif area < 1000:
        h = 4.8 + 2.4 * u
    else:
        h = 7.0 + 3.5 * u
    # cor do telhado guiada pela cor do satélite dentro da pegada
    c = poly.centroid
    pts = [(c.x, c.y)] + [((c.x + x) / 2, (c.y + y) / 2) for x, y in list(poly.exterior.coords)[:-1][:6]]
    rgb = np.median(sat_sample(np.array([p[0] for p in pts]), np.array([p[1] for p in pts])), axis=0)
    r, g, b = rgb
    bright = rgb.mean()
    if r > g * 1.12 and r > b * 1.35:
        pal = ROOF_TILE
    elif bright > 0.62:
        pal = ROOF_METAL
    else:
        pal = ROOF_FIBER if rand01(bid, "f") < 0.6 else ROOF_TILE
    roof = hexrgb(pal[int(rand01(bid, "r") * len(pal)) % len(pal)]) * (0.92 + 0.12 * rand01(bid, "v"))
    wall = hexrgb(WALLS[int(rand01(bid, "w") * len(WALLS)) % len(WALLS)])
    return h, np.clip(roof, 0, 1), wall


def add_walls(layer, ring, h, wall, y0=0.0, courtyard=False):
    c = np.asarray(ring.coords)
    # anti-horário visto de cima => normais para fora; num pátio interno as paredes olham para dentro
    if shapely.LinearRing(c).is_ccw == courtyard:
        c = c[::-1]
    bottom = wall * 0.78
    for (x0, z0), (x1, z1) in zip(c[:-1], c[1:]):
        dx, dz = x1 - x0, z1 - z0
        L = math.hypot(dx, dz)
        if L < 0.05:
            continue
        n = (dz / L, 0, dx / L)  # normal para fora (y norte -> z = -norte)
        A, B = (x0, y0, -z0), (x1, y0, -z1)
        C, D = (x1, h, -z1), (x0, h, -z0)
        layer.add([A, B, C, A, C, D], n, np.array([bottom, bottom, wall, bottom, wall, wall]))


def tri_normal(a, b, c):
    n = np.cross(np.subtract(b, a), np.subtract(c, a))
    return n / (np.linalg.norm(n) + 1e-9)


def add_hip_roof(layer, rect, h, roof):
    """Telhado de quatro águas sobre o retângulo mínimo da pegada."""
    c = np.asarray(rect.exterior.coords)[:4]
    e0 = np.linalg.norm(c[1] - c[0]); e1 = np.linalg.norm(c[2] - c[1])
    if e1 > e0:
        c = np.roll(c, -1, axis=0); e0, e1 = e1, e0
    # c0-c1 é o lado comprido; cumeeira paralela a ele
    mid = c.mean(axis=0)
    axis = (c[1] - c[0]) / e0
    half_ridge = max(e0 / 2 - e1 / 2, 0.0)
    rise = min(0.32 * e1 / 2, 2.6)
    r0 = mid - axis * half_ridge; r1 = mid + axis * half_ridge
    P = lambda p, y: (float(p[0]), y, float(-p[1]))
    R0, R1 = P(r0, h + rise), P(r1, h + rise)
    C = [P(p, h) for p in c]
    faces = [(C[0], C[1], R1, R0), (C[2], C[3], R0, R1)]  # águas compridas
    tris = []
    for a, b, rr1, rr0 in faces:
        tris += [(a, b, rr1), (a, rr1, rr0)]
    tris += [(C[1], C[2], R1), (C[3], C[0], R0)]  # águas das pontas
    for t in tris:
        n = tri_normal(*t)
        if n[1] < 0:
            t = (t[0], t[2], t[1]); n = -n
        shade = roof * (0.9 + 0.1 * n[1])
        layer.add(list(t), n, shade)
    # beiral: as paredes vão só até h; nada a fazer para o "oitão" (quatro águas não tem)


def build_buildings(road_union):
    layer = Layer()
    polys = []
    rows = pq.read_table(OV / "buildings.parquet", columns=["id", "geometry"]).to_pylist()
    n_hip = 0
    for r in rows:
        g = to_local(from_wkb(r["geometry"]))
        if not inside_detail(g):
            continue
        for poly in getattr(g, "geoms", [g]):
            poly = poly.simplify(0.25)
            if poly.is_empty or poly.area < 9:
                continue
            area = poly.area
            h, roof, wall = building_style(r["id"], poly, area)
            polys.append(poly)
            rect = poly.minimum_rotated_rectangle
            rectish = rect.area > 0 and area / rect.area > 0.86
            if rectish and area < 600 and len(poly.interiors) == 0:
                add_walls(layer, rect.exterior, h, wall)
                add_hip_roof(layer, rect, h, roof)
                n_hip += 1
            else:
                add_walls(layer, poly.exterior, h, wall)
                for hole in poly.interiors:
                    add_walls(layer, hole, h, wall, courtyard=True)
                layer.add(flat_triangles(poly, h), (0, 1, 0), roof)
    print(f"  prédios: {len(polys)} ({n_hip} com telhado de quatro águas)")
    return layer, polys


# ---------------------------------------------------------------- árvores (NDVI)
def build_trees(building_polys, road_union, water_union, route_line):
    d = np.load(CACHE / "ndvi_detail.npz")
    ndvi = d["ndvi"].astype(np.float32)
    x0, y0, x1, y1 = d["bounds"]  # UTM
    ny, nx = ndvi.shape
    px = (x1 - x0) / nx
    rng = np.random.default_rng(7)
    cand = []
    for iy in range(ny):
        for ix in range(nx):
            v = ndvi[iy, ix]
            if v < 0.58:
                continue
            p = min((v - 0.55) / 0.22, 1.0)
            k = 1 + (v > 0.72)
            for _ in range(k):
                if rng.random() > p:
                    continue
                e = x0 + (ix + rng.random()) * px
                n = y1 - (iy + rng.random()) * px
                cand.append((e - ORIGIN_E, n - ORIGIN_N, v))
    cand = np.array(cand, np.float32)
    print(f"  candidatos a árvore: {len(cand)}")
    pts = shapely.points(cand[:, 0], cand[:, 1])
    blocked = STRtree(building_polys).query(pts, predicate="intersects")[0]
    keep = np.ones(len(cand), bool); keep[blocked] = False
    # nada de árvore no meio da rua ou dentro do lago
    no_go = shapely.union_all([road_union.buffer(1.0), water_union])
    shapely.prepare(no_go)
    keep &= ~shapely.contains_xy(no_go, cand[:, 0], cand[:, 1])
    cand = cand[keep]
    # densidade cai longe da rota (o drone só vê de perto o entorno do trajeto)
    dist = shapely.distance(shapely.points(cand[:, 0], cand[:, 1]), route_line)
    keep_p = np.clip(1.25 - dist / 2200.0, 0.18, 1.0)
    cand = cand[rng.random(len(cand)) < keep_p]
    greens = [hexrgb(h) for h in ["#3f6b2a", "#4a7a33", "#355f25", "#557f38", "#2f5622", "#62893f"]]
    out = []
    for x, y, v in cand:
        r = 2.0 + 2.2 * rng.random() + (1.0 if v > 0.75 else 0.0)
        hc = r * (1.1 + 0.8 * rng.random()) + 1.5
        col = greens[rng.integers(len(greens))] * (0.85 + 0.25 * rng.random())
        out.append([x, hc, -y, r, r * (0.72 + 0.2 * rng.random()), r, rng.random() * 6.283, *col])
    print(f"  árvores: {len(out)}")
    return np.asarray(out, np.float32)


# ---------------------------------------------------------------- água
def build_water():
    layer = Layer()
    polys = []
    for r in pq.read_table(OV / "water.parquet").to_pylist():
        g = to_local(from_wkb(r["geometry"]))
        if g.geom_type not in ("Polygon", "MultiPolygon") or not inside_detail(g):
            continue
        for poly in getattr(g, "geoms", [g]):
            poly = poly.buffer(0)
            polys.append(poly)
            layer.add(flat_triangles(poly, 0.12), (0, 1, 0), hexrgb("#2f6f6a"))
    return layer, shapely.union_all(polys) if polys else shapely.GeometryCollection()


# ---------------------------------------------------------------- rota e pontos
def build_route_and_pois():
    rt = json.load(open(CACHE / "route.geojson"))
    line = to_local(shapely.LineString(rt["geometry"]["coordinates"]))
    line = shapely.segmentize(line, 2.0)
    pts = np.asarray(line.coords)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    along = np.concatenate([[0], np.cumsum(seg)])
    steps = []
    acc = 0.0
    for name, length in rt["properties"]["steps"]:
        steps.append({"name": name, "from": round(acc, 1), "to": round(acc + length, 1)})
        acc += length

    def ll_local(lon, lat):
        e, n = to_utm(lon, lat)
        return [round(e - ORIGIN_E, 2), round(-(n - ORIGIN_N), 2)]

    # avenida Barão de Araruna (para posicionar a loja e a Júnior Bike pela numeração métrica)
    av = [to_local(from_wkb(r["geometry"])) for r in pq.read_table(OV / "segments.parquet").to_pylist()
          if "Araruna" in ((r["names"] or {}).get("primary") or "")]
    av = shapely.line_merge(shapely.MultiLineString([list(a.coords) for a in av]))
    if av.geom_type != "LineString":
        av = max(av.geoms, key=lambda a: a.length)
    if av.coords[0][1] > av.coords[-1][1]:  # orienta do sudeste (nº baixos) para o noroeste
        av = shapely.LineString(list(av.coords)[::-1])
    p = av.interpolate(STORE_ALONG_M); q = av.interpolate(STORE_ALONG_M + 1)
    tx, ty = q.x - p.x, q.y - p.y; L = math.hypot(tx, ty); tx, ty = tx / L, ty / L
    left = (-ty, tx)  # à esquerda de quem anda para o noroeste = lado sudoeste (ímpares)
    store = (p.x + left[0] * STORE_SIDE_OFFSET_M, p.y + left[1] * STORE_SIDE_OFFSET_M)
    junior = (p.x - left[0] * STORE_SIDE_OFFSET_M, p.y - left[1] * STORE_SIDE_OFFSET_M)
    store_on_road = (p.x, p.y)
    pois = {
        "store": [round(store[0], 2), round(-store[1], 2)],
        "storeOnAvenue": [round(store_on_road[0], 2), round(-store_on_road[1], 2)],
        "juniorBike": [round(junior[0], 2), round(-junior[1], 2)],
        "avenueHeading": [round(tx, 4), round(-ty, 4)],
        "praca": ll_local(*PRACA_CELIO_MIRANDA),
        "hospital": ll_local(*HOSPITAL_SAO_PAULO),
        "lagoVerde": ll_local(*LAGO_VERDE),
    }
    route = {"points": [[round(x, 2), round(-y, 2)] for x, y in pts], "along": [round(a, 2) for a in along],
             "length": round(float(along[-1]), 1), "steps": steps}
    return route, pois, line


def main():
    blob = bytearray()
    manifest = {}
    print("ruas…")
    paved, unpaved, walk, curb, centerlines = build_roads()
    roads = Layer()
    roads.add(flat_triangles(curb, 0.06), (0, 1, 0), hexrgb("#cfc8bb"))
    roads.add(flat_triangles(walk, 0.07), (0, 1, 0), hexrgb("#c2b8a6"))
    roads.add(flat_triangles(unpaved, 0.09), (0, 1, 0), hexrgb("#a8694a"))
    roads.add(flat_triangles(paved, 0.10), (0, 1, 0), hexrgb("#5a5d63"))
    marks = dashes(centerlines).intersection(paved)
    roads.add(flat_triangles(marks, 0.12), (0, 1, 0), hexrgb("#e9e4d6"))
    roads.export("roads", blob, manifest)
    print("água…")
    water, water_union = build_water()
    water.export("water", blob, manifest)
    print("prédios…")
    road_union = shapely.union_all([paved, unpaved])
    bl, bpolys = build_buildings(road_union)
    bl.export("buildings", blob, manifest)
    print("rota e pontos…")
    route, pois, route_line = build_route_and_pois()
    print("árvores…")
    trees = build_trees(bpolys, road_union, water_union, route_line)
    while len(blob) % 4:
        blob.append(0)
    manifest["trees"] = {"count": len(trees), "stride": trees.shape[1],
                         "data": {"offset": len(blob), "length": trees.size, "type": "float32"}}
    blob.extend(trees.tobytes())
    (PUBLIC / "scene.bin").write_bytes(bytes(blob))
    sat = json.load(open(CACHE / "satellite_meta.json"))
    scene = {
        "origin": {"lon": ORIGIN_LL[0], "lat": ORIGIN_LL[1], "crs": "EPSG:32723"},
        "detailHalf": DETAIL_HALF,
        "satellite": sat,
        "layers": manifest,
        "route": route,
        "pois": pois,
        "store": {"number": STORE_NUMBER},
    }
    json.dump(scene, open(PUBLIC / "scene.json", "w"))
    print(f"scene.bin: {len(blob) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
