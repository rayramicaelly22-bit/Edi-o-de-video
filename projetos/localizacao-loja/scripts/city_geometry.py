"""Geometria detalhada da cidade para o render realista (Blender/Cycles).

Coordenadas locais em metros no sistema do Blender: x = leste, y = norte, z = altura (origem em config.ORIGIN_LL).
Tudo aqui é numpy/shapely puro; scripts/blender_build.py transforma os buffers em malhas e materiais.
"""
import hashlib
import json
import math

import numpy as np
import pyarrow.parquet as pq
import shapely
import shapely.ops
from shapely import STRtree, from_wkb

from config import CACHE, ORIGIN_E, ORIGIN_N, PUBLIC, to_utm

OV = CACHE / "overture"
DETAIL_HALF = 3072.0     # área com prédios, ruas e árvores
NEAR_ROUTE = 1400.0      # muros, carros e caixas d'água só perto do trajeto (onde a câmera chega perto)


def rand01(key, salt=""):
    return int(hashlib.md5((key + salt).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def to_local(geom):
    def f(c):
        e, n = to_utm(c[:, 0], c[:, 1])
        return np.column_stack([np.asarray(e) - ORIGIN_E, np.asarray(n) - ORIGIN_N])
    return shapely.transform(geom, f)


def inside_detail(g, margin=0.0):
    x0, y0, x1, y1 = g.bounds
    h = DETAIL_HALF + margin
    return x1 > -h and x0 < h and y1 > -h and y0 < h


class MeshBuf:
    """Polígonos soltos (sem vértices compartilhados) com UV por canto e atributos por face."""

    def __init__(self, face_attrs=()):
        self.verts, self.uvs, self.sizes = [], [], []
        self.face_attrs = {k: [] for k in face_attrs}

    def add(self, poly, uv=None, **attrs):
        poly = np.asarray(poly, np.float32)
        self.verts.append(poly)
        self.uvs.append(np.zeros((len(poly), 2), np.float32) if uv is None else np.asarray(uv, np.float32))
        self.sizes.append(len(poly))
        for k in self.face_attrs:
            self.face_attrs[k].append(attrs.get(k, 0.0))

    def arrays(self):
        if not self.verts:
            return None
        out = {"verts": np.concatenate(self.verts), "uvs": np.concatenate(self.uvs), "sizes": np.asarray(self.sizes, np.int32)}
        for k, v in self.face_attrs.items():
            out["attr_" + k] = np.asarray(v, np.float32)
        return out


# ------------------------------------------------------------------ utilidades de polígono
def triangulate(poly):
    """Triângulos (constrained Delaunay) de um polígono 2D com buracos, orientados para cima (anti-horário)."""
    out = []
    for tri in shapely.constrained_delaunay_triangles(poly).geoms:
        c = np.asarray(tri.exterior.coords)[:3]
        if (c[1, 0] - c[0, 0]) * (c[2, 1] - c[0, 1]) - (c[1, 1] - c[0, 1]) * (c[2, 0] - c[0, 0]) < 0:
            c = c[::-1]
        out.append(c)
    return out


def ccw(coords, want_ccw=True):
    c = np.asarray(coords)[:-1] if np.allclose(coords[0], coords[-1]) else np.asarray(coords)
    area2 = np.sum(c[:, 0] * np.roll(c[:, 1], -1) - np.roll(c[:, 0], -1) * c[:, 1])
    return c if (area2 > 0) == want_ccw else c[::-1]


def add_walls(buf, ring2d, z0, z1, attrs, outward=True):
    """Paredes verticais ao longo de um anel 2D. UV: u = metros ao longo do anel, v = altura (m)."""
    c = ccw(ring2d, want_ccw=outward)
    u = 0.0
    n = len(c)
    for i in range(n):
        a, b = c[i], c[(i + 1) % n]
        L = float(np.hypot(*(b - a)))
        if L < 0.05:
            continue
        buf.add([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)],
                [(u, z0), (u + L, z0), (u + L, z1), (u, z1)], **attrs)
        u += L


def add_flat(buf, poly, z, attrs, uv_scale=1.0):
    for t in triangulate(poly):
        buf.add([(p[0], p[1], z) for p in t], [(p[0] * uv_scale, p[1] * uv_scale) for p in t], **attrs)


def roof_face(buf, pts3, eave_dir, attrs):
    """Água do telhado com UV alinhada: u ao longo do beiral, v subindo a inclinação (metros)."""
    p = np.asarray(pts3, np.float64)
    e = np.zeros(3)
    e[:len(eave_dir)] = eave_dir  # direção do beiral é horizontal (vem em 2D)
    e = e / np.linalg.norm(e)
    n = np.cross(p[1] - p[0], p[2] - p[0])
    if n[2] < 0:
        p = p[::-1]
        n = -n
    up = np.cross(n / np.linalg.norm(n), e)
    if up[2] < 0:
        up = -up
    o = p[np.argmin(p @ up)]
    uv = [((q - o) @ e, (q - o) @ up) for q in p]
    buf.add(p, uv, **attrs)


# ------------------------------------------------------------------ satélite (cor de telhado)
class Satellite:
    def __init__(self):
        from PIL import Image
        self.img = np.asarray(Image.open(PUBLIC / "sat_city.jpg").convert("RGB"), np.float32) / 255
        self.size = 12288.0

    def sample(self, x, y):
        px = np.clip(((np.asarray(x) / self.size + 0.5) * self.img.shape[1]).astype(int), 0, self.img.shape[1] - 1)
        py = np.clip(((0.5 - np.asarray(y) / self.size) * self.img.shape[0]).astype(int), 0, self.img.shape[0] - 1)
        return self.img[py, px]


# ------------------------------------------------------------------ prédios
ROOF_TILE, ROOF_FIBER, ROOF_METAL, ROOF_SLAB = 0, 1, 2, 3
WALL_COLORS = ["#f3efe6", "#efe6d2", "#e9dcc3", "#f6f3ee", "#e3e7e8", "#efe2cf", "#ead7cf", "#dfe6d6",
               "#f8f6f2", "#e6dccb", "#f2dcb0", "#d9e3ea", "#c9d9c1", "#f1d7a4", "#e9c9b0", "#ffffff",
               "#bcd3de", "#f0e0a8"]


def hexrgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def building_params(bid, poly, area, sat):
    u = rand01(bid)
    two = rand01(bid, "2")
    if area < 35:
        h = 2.7 + 0.5 * u
    elif area < 260:
        h = 3.1 + 0.7 * u
        if two < 0.11:
            h = 5.9 + 0.7 * u
    elif area < 1200:
        h = 4.2 + 2.6 * u
        if two < 0.25:
            h = 6.5 + 2.5 * u
    else:
        h = 6.5 + 4.0 * u
    c = poly.centroid
    pts = [(c.x, c.y)] + [((c.x + x) / 2, (c.y + y) / 2) for x, y in list(poly.exterior.coords)[:-1][:8]]
    rgb = np.median(sat.sample(np.array([p[0] for p in pts]), np.array([p[1] for p in pts])), axis=0)
    r, g, b = rgb
    if r > g * 1.12 and r > b * 1.35:
        mat = ROOF_TILE if rand01(bid, "fc") > 0.16 else ROOF_FIBER
    elif rgb.mean() > 0.6:
        mat = ROOF_METAL if area > 300 or rand01(bid, "m") < 0.5 else ROOF_FIBER
    else:
        mat = ROOF_FIBER if rand01(bid, "f") < 0.55 else ROOF_TILE
    wall = hexrgb(WALL_COLORS[int(rand01(bid, "w") * len(WALL_COLORS)) % len(WALL_COLORS)])
    return h, mat, wall


def build_buildings(route_line):
    sat = Satellite()
    walls = MeshBuf(("r", "g", "b", "seed", "floors"))
    roofs = MeshBuf(("kind", "tone", "seed"))
    gables = MeshBuf(("r", "g", "b", "seed", "floors"))
    props = {"tanks": [], "panels": MeshBuf(("seed",))}
    polys = []
    rows = pq.read_table(OV / "buildings.parquet", columns=["id", "geometry"]).to_pylist()
    for r in rows:
        g = to_local(from_wkb(r["geometry"]))
        if not inside_detail(g):
            continue
        for poly in getattr(g, "geoms", [g]):
            poly = poly.simplify(0.25)
            if poly.is_empty or poly.area < 9 or poly.geom_type != "Polygon":
                continue
            bid = r["id"]
            area = poly.area
            h, mat, wall = building_params(bid, poly, area, sat)
            floors = 2 if h > 5.5 else 1
            seed = rand01(bid, "s")
            wattrs = dict(r=wall[0], g=wall[1], b=wall[2], seed=seed, floors=floors)
            rattrs = dict(kind=mat, tone=rand01(bid, "t"), seed=seed)
            polys.append(poly)
            near = poly.distance(route_line) < NEAR_ROUTE
            rect = poly.minimum_rotated_rectangle
            rectish = rect.area > 0 and area / rect.area > 0.86 and len(poly.interiors) == 0
            pick = rand01(bid, "roof")
            if rectish and area < 700 and pick < 0.88:
                kind = "hip" if pick < 0.48 else "gable"
                c = np.asarray(rect.exterior.coords)[:4]
                if np.hypot(*(c[2] - c[1])) > np.hypot(*(c[1] - c[0])):
                    c = np.roll(c, -1, axis=0)
                add_walls(walls, np.vstack([c, c[:1]]), 0.0, h, wattrs)
                ridge_z = pitched_roof(roofs, gables, c, h, kind, rattrs, wattrs)
                if near and area < 320 and rand01(bid, "tank") < 0.38:
                    m = c.mean(axis=0)
                    props["tanks"].append([m[0], m[1], ridge_z - 0.35, rand01(bid, "tc"), rand01(bid, "ta") * 6.28])
                if near and kind == "gable" and mat == ROOF_TILE and rand01(bid, "pv") < 0.12:
                    solar_panel(props["panels"], c, h, seed)
            else:
                # laje / telhado plano com platibanda (parapeito)
                top = h + 0.55
                add_walls(walls, poly.exterior.coords, 0.0, top, wattrs)
                for hole in poly.interiors:
                    add_walls(walls, hole.coords, 0.0, top, wattrs, outward=False)
                inner = poly.buffer(-0.15, join_style="mitre")
                if not inner.is_empty:
                    for ip in getattr(inner, "geoms", [inner]):
                        add_walls(walls, ip.exterior.coords, h, top, wattrs, outward=False)
                        add_flat(roofs, ip, h, dict(kind=ROOF_SLAB if mat != ROOF_METAL else ROOF_METAL, tone=rattrs["tone"], seed=seed))
                if near and area < 400 and rand01(bid, "tank") < 0.45:
                    pt = poly.representative_point()
                    props["tanks"].append([pt.x, pt.y, h, rand01(bid, "tc"), rand01(bid, "ta") * 6.28])
    print(f"  prédios: {len(polys)}, caixas d'água: {len(props['tanks'])}")
    return walls, roofs, gables, props, polys


def pitched_roof(roofs, gables, c, h, kind, rattrs, wattrs):
    """Telhado de quatro águas ou de duas águas sobre o retângulo c (c0-c1 = lado comprido), com beiral."""
    ov = 0.5
    e0 = np.hypot(*(c[1] - c[0]))
    e1 = np.hypot(*(c[2] - c[1]))
    ax = (c[1] - c[0]) / e0                 # ao longo da cumeeira
    ay = (c[3] - c[0]) / e1                 # atravessando
    mid = c.mean(axis=0)
    pitch = 0.32 if rattrs["kind"] == 0 else 0.18   # telha cerâmica é mais inclinada que fibrocimento/metal
    rise = min(pitch * (e1 / 2 + ov), 3.2)
    eave_z = h - ov * pitch
    E = [mid + sx * ax * (e0 / 2 + ov) + sy * ay * (e1 / 2 + ov) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    E3 = [(p[0], p[1], eave_z) for p in E]
    ridge_z = h + rise - ov * pitch
    if kind == "hip":
        half_ridge = max(e0 / 2 - e1 / 2, 0.0)
        R0 = mid - ax * half_ridge
        R1 = mid + ax * half_ridge
        R0_3, R1_3 = (R0[0], R0[1], ridge_z), (R1[0], R1[1], ridge_z)
        roof_face(roofs, [E3[0], E3[1], R1_3, R0_3], ax, rattrs)
        roof_face(roofs, [E3[2], E3[3], R0_3, R1_3], -ax, rattrs)
        roof_face(roofs, [E3[1], E3[2], R1_3], ay, rattrs)
        roof_face(roofs, [E3[3], E3[0], R0_3], -ay, rattrs)
    else:
        R0 = mid - ax * (e0 / 2 + ov)
        R1 = mid + ax * (e0 / 2 + ov)
        R0_3, R1_3 = (R0[0], R0[1], ridge_z), (R1[0], R1[1], ridge_z)
        roof_face(roofs, [E3[0], E3[1], R1_3, R0_3], ax, rattrs)
        roof_face(roofs, [E3[2], E3[3], R0_3, R1_3], -ax, rattrs)
        # oitões (paredes triangulares nas pontas)
        for a, b in ((c[3], c[0]), (c[1], c[2])):
            m = (a + b) / 2
            # o ápice do oitão fica na altura da cumeeira (o beiral não conta aqui)
            tri = [(a[0], a[1], h), (b[0], b[1], h), (m[0], m[1], ridge_z)]
            if np.cross(np.subtract(tri[1], tri[0]), np.subtract(tri[2], tri[0]))[:2] @ (m - mid) < 0:
                tri = tri[::-1]
            L = float(np.hypot(*(b - a)))
            gables.add(tri, [(0, h), (L, h), (L / 2, ridge_z)], **wattrs)
    return ridge_z


def solar_panel(buf, c, h, seed):
    """Placas solares na água voltada para o norte (hemisfério sul)."""
    e0 = np.hypot(*(c[1] - c[0]))
    e1 = np.hypot(*(c[2] - c[1]))
    ax = (c[1] - c[0]) / e0
    ay = (c[3] - c[0]) / e1
    if ay[1] < 0:
        ay = -ay
    mid = c.mean(axis=0)
    pitch = 0.32
    w = min(e0 * 0.6, 7.0)
    d0, d1 = e1 * 0.08, e1 * 0.42
    pts = []
    for sx, d in ((-1, d0), (1, d0), (1, d1), (-1, d1)):
        p = mid + sx * ax * w / 2 + ay * d
        z = h + pitch * (e1 / 2 - d) + 0.12
        pts.append((p[0], p[1], z))
    buf.add(pts, [(0, 0), (1, 0), (1, 1), (0, 1)], seed=seed)


# ------------------------------------------------------------------ ruas
ROAD_WIDTH = {"trunk": 15, "primary": 13, "secondary": 12, "tertiary": 10.5, "unclassified": 8,
              "residential": 7.5, "living_street": 6, "service": 4.5, "unknown": 6, "track": 4.5}
PATH_WIDTH = {"footway": 2.2, "path": 1.8, "cycleway": 2.2}
UNPAVED = {"unpaved", "dirt", "gravel", "ground", "sand", "earth", "compacted"}


def build_roads():
    paved, unpaved, paths, center_major, center_all = [], [], [], [], []
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
        is_unpaved = bool(surf & UNPAVED) or cls == "track"
        (unpaved if is_unpaved else paved).append(g.buffer(w / 2, quad_segs=4))
        if not is_unpaved:
            center_all.append((g, w, cls))
            if cls in ("primary", "trunk", "secondary", "tertiary"):
                center_major.append(g)
    clip = shapely.box(-DETAIL_HALF, -DETAIL_HALF, DETAIL_HALF, DETAIL_HALF)
    paved_u = shapely.union_all(paved).intersection(clip)
    unpaved_u = shapely.union_all(unpaved).difference(paved_u).intersection(clip)
    walk_u = shapely.union_all(paths).difference(paved_u).difference(unpaved_u).intersection(clip)
    sidewalk_u = paved_u.buffer(2.0, quad_segs=3).difference(paved_u).difference(unpaved_u).intersection(clip)
    return paved_u, unpaved_u, walk_u, sidewalk_u, center_major, center_all


def dashes(lines, dash=3.0, gap=6.0, width=0.18):
    polys = []
    for g in lines:
        for part in getattr(g, "geoms", [g]):
            d = 0.0
            while d < part.length - dash:
                polys.append(shapely.ops.substring(part, d, d + dash).buffer(width / 2, cap_style="flat"))
                d += dash + gap
    return shapely.union_all(polys) if polys else shapely.GeometryCollection()


def road_meshes():
    paved, unpaved, walk, sidewalk, major, allc = build_roads()
    asphalt = MeshBuf(("seed",))
    for p in getattr(paved, "geoms", [paved]):
        add_flat(asphalt, p, 0.03, dict(seed=0.0))
    dirt = MeshBuf(("seed",))
    for p in getattr(unpaved, "geoms", [unpaved]):
        add_flat(dirt, p, 0.04, dict(seed=0.0))
    # calçada elevada 15 cm com meio-fio (face vertical voltada para o asfalto)
    side = MeshBuf(("seed",))
    for p in getattr(sidewalk, "geoms", [sidewalk]):
        add_flat(side, p, 0.17, dict(seed=0.0))
    for p in getattr(walk, "geoms", [walk]):
        add_flat(side, p, 0.06, dict(seed=0.0))
    curb = MeshBuf(("seed",))
    for p in getattr(paved, "geoms", [paved]):
        add_walls(curb, p.exterior.coords, 0.03, 0.17, dict(seed=0.0), outward=False)
        for hole in p.interiors:
            add_walls(curb, hole.coords, 0.03, 0.17, dict(seed=0.0), outward=True)
    marks = MeshBuf(("seed",))
    m = dashes(major).intersection(paved)
    for p in getattr(m, "geoms", [m]):
        if p.geom_type == "Polygon":
            add_flat(marks, p, 0.045, dict(seed=0.0))
    print(f"  ruas: asfalto {len(asphalt.sizes)} tri, calçada {len(side.sizes)} tri, meio-fio {len(curb.sizes)} quads")
    return {"asphalt": asphalt, "dirt": dirt, "sidewalk": side, "curb": curb, "marks": marks}, paved, unpaved, walk, allc


# ------------------------------------------------------------------ lotes e muros
def build_walls(building_polys, paved, unpaved, route_line):
    """Muros de lote: frente da quadra (com portões), divisas perpendiculares à rua e muro de fundo (perto do trajeto)."""
    rng = np.random.default_rng(11)
    roads = shapely.union_all([paved, unpaved]).buffer(2.2)
    area = route_line.buffer(NEAR_ROUTE)
    blocks = area.difference(roads)
    tree = STRtree(building_polys)
    muros = MeshBuf(("r", "g", "b", "seed", "floors"))
    n_seg = 0

    def emit(line, hgt, col, gates):
        nonlocal n_seg
        for seg in getattr(line, "geoms", [line]):
            if seg.geom_type != "LineString" or seg.length < 0.8:
                continue
            coords = np.asarray(seg.coords)
            for a, b in zip(coords[:-1], coords[1:]):
                L = np.hypot(*(b - a))
                if L < 0.4:
                    continue
                # portões: falhas de ~3 m nos muros da frente
                if gates and L > 6 and rng.random() < 0.55:
                    t0 = rng.uniform(0.2, 0.8 - 3.0 / L) if L > 8 else 0.3
                    pieces = [(a, a + (b - a) * t0), (a + (b - a) * (t0 + 3.0 / L), b)]
                else:
                    pieces = [(a, b)]
                for p, q in pieces:
                    wall_box(muros, p, q, hgt, 0.15, dict(r=col[0], g=col[1], b=col[2], seed=rng.random(), floors=0))
                    n_seg += 1

    def wall_color(front):
        if rng.random() < (0.7 if front else 0.35):
            return hexrgb(WALL_COLORS[rng.integers(len(WALL_COLORS))])
        return [0.6, 0.59, 0.56] if rng.random() < 0.6 else [0.5, 0.49, 0.47]

    for blk in getattr(blocks, "geoms", [blocks]):
        if blk.area < 600 or blk.area > 80000:
            continue
        blk = blk.simplify(0.6)
        if blk.is_empty or blk.geom_type != "Polygon":
            continue
        idx = tree.query(blk, predicate="intersects")
        houses = [building_polys[i] for i in idx if building_polys[i].area < 900]
        if len(houses) < 2:
            continue
        obstacles = shapely.union_all([building_polys[i].buffer(0.4) for i in idx])
        shapely.prepare(blk)
        hc = [np.asarray(h.exterior.coords) for h in houses]
        rp = np.array([[h.representative_point().x, h.representative_point().y] for h in houses])
        ring = ccw(blk.exterior.coords)          # anti-horário: o interior fica à esquerda de cada aresta
        n = len(ring)
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            L = float(np.hypot(*(b - a)))
            if L < 9:
                continue
            t = (b - a) / L
            nrm = np.array([-t[1], t[0]])
            rel = rp - a
            s_, d_ = rel @ t, rel @ nrm
            sel = np.where((s_ > 0) & (s_ < L) & (d_ > 0) & (d_ < 28))[0]
            spans = sorted(((hc[j] - a) @ t).min() for j in sel)
            ends = sorted(((hc[j] - a) @ t).max() for j in sel)
            cuts = []
            for e0, s1 in zip(ends[:-1], spans[1:]):
                cuts.append((e0 + s1) / 2)
            # terrenos sem casa (ou trechos longos): lotes de ~10-12 m
            marks = [0.0] + sorted(cuts) + [L]
            for m0, m1 in zip(marks[:-1], marks[1:]):
                k = int((m1 - m0) // 11.5)
                cuts += [m0 + (m1 - m0) * j / (k + 1) for j in range(1, k + 1)]
            cuts = sorted(c for c in cuts if 3.0 < c < L - 3.0)
            back = []
            for c in cuts:
                o = a + t * c
                ray = shapely.LineString([o + nrm * 0.3, o + nrm * 200])
                hit = ray.intersection(blk.boundary)
                D = min((np.hypot(*(np.asarray(g.coords[0]) - o)) for g in getattr(hit, "geoms", [hit]) if not g.is_empty), default=60.0)
                depth = min(rng.uniform(22.0, 32.0), D / 2 - 0.2)
                if depth < 4:
                    continue
                q = o + nrm * depth
                side = shapely.LineString([o, q]).difference(obstacles)
                emit(side, 1.9 + rng.uniform(-0.3, 0.3), wall_color(False), False)
                back.append(q)
            # muro de fundo ligando o fim das divisas
            for p, q in zip(back[:-1], back[1:]):
                if np.hypot(*(q - p)) < 25:
                    emit(shapely.LineString([p, q]).difference(obstacles), 1.8 + rng.uniform(-0.2, 0.3), wall_color(False), False)
        # frente da quadra
        emit(blk.exterior.difference(obstacles), 2.1 + rng.uniform(-0.25, 0.3), wall_color(True), True)
    print(f"  muros: {n_seg} trechos")
    return muros


def wall_box(buf, a, b, h, t, attrs):
    d = np.asarray(b, float) - np.asarray(a, float)
    L = np.hypot(*d)
    if L < 1e-3:
        return
    n = np.array([-d[1], d[0]]) / L * t / 2
    p = [np.asarray(a) + n, np.asarray(b) + n, np.asarray(b) - n, np.asarray(a) - n]
    z0, z1 = 0.0, h
    for i in range(4):
        c, e = p[i], p[(i + 1) % 4]
        Le = np.hypot(*(e - c))
        buf.add([(c[0], c[1], z0), (e[0], e[1], z0), (e[0], e[1], z1), (c[0], c[1], z1)], [(0, z0), (Le, z0), (Le, z1), (0, z1)], **attrs)
    buf.add([(q[0], q[1], z1) for q in p], [(0, 0), (L, 0), (L, t), (0, t)], **attrs)


# ------------------------------------------------------------------ carros estacionados
CAR_COLORS = [("#f2f2f0", 0.34), ("#b9bcbf", 0.22), ("#1d1f22", 0.15), ("#8e1b1b", 0.09), ("#5b5f63", 0.10),
              ("#1f3f74", 0.05), ("#c8b48a", 0.05)]


def build_cars(center_all, route_line, building_polys):
    rng = np.random.default_rng(5)
    cols = [hexrgb(c) for c, _ in CAR_COLORS]
    probs = np.array([p for _, p in CAR_COLORS])
    probs /= probs.sum()
    blockers = STRtree(building_polys)
    cars = []
    for g, w, cls in center_all:
        if cls not in ("residential", "tertiary", "primary", "unclassified", "secondary"):
            continue
        if g.distance(route_line) > NEAR_ROUTE * 0.8:
            continue
        for part in getattr(g, "geoms", [g]):
            d = 8.0
            while d < part.length - 8.0:
                if rng.random() < (0.16 if cls == "residential" else 0.22):
                    p = part.interpolate(d)
                    q = part.interpolate(min(d + 1.0, part.length))
                    tx, ty = q.x - p.x, q.y - p.y
                    L = math.hypot(tx, ty) or 1
                    tx, ty = tx / L, ty / L
                    side = 1 if rng.random() < 0.5 else -1
                    off = w / 2 - 1.15
                    cx, cy = p.x - ty * off * side, p.y + tx * off * side
                    if not blockers.query(shapely.Point(cx, cy).buffer(2.0), predicate="intersects").size:
                        ang = math.atan2(ty, tx) + (math.pi if rng.random() < 0.5 else 0)
                        ci = rng.choice(len(cols), p=probs)
                        cars.append([cx, cy, ang, int(rng.integers(4)), *cols[ci], rng.random()])
                d += rng.uniform(5.5, 9.0)
    print(f"  carros: {len(cars)}")
    return np.asarray(cars, np.float32)


# ------------------------------------------------------------------ árvores (NDVI, calçadas e praças)
GREEN_USES = {"park", "grass", "pitch", "garden", "playground"}


def load_green_areas():
    polys = []
    for r in pq.read_table(OV / "land_use.parquet").to_pylist():
        if r["class"] not in GREEN_USES:
            continue
        g = to_local(from_wkb(r["geometry"]))
        if not inside_detail(g):
            continue
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon" and 40 < p.area < 60000:
                polys.append((p.buffer(0), r["class"]))
    return polys


def tree_kind(rng, dense, street=False):
    r = rng.random()
    if street:   # calçada: copas médias e pequenas, às vezes uma mangueira ou palmeira
        kind = 1 if r < 0.5 else 2 if r < 0.82 else 0 if r < 0.92 else 3
    else:        # 0 mangueira, 1 copa média, 2 arvoreta, 3 coqueiro, 4 açaizeiro
        kind = 0 if (dense and r < 0.45) else 1 if r < 0.6 else 2 if r < 0.82 else 3 if r < 0.91 else 4
    s = {0: rng.uniform(0.85, 1.3), 1: rng.uniform(0.75, 1.15), 2: rng.uniform(0.7, 1.1), 3: rng.uniform(0.85, 1.15), 4: rng.uniform(0.8, 1.2)}[kind]
    return kind, s


def build_trees(building_polys, paved, unpaved, walk, water, route_line, center_all, green):
    d = np.load(CACHE / "ndvi_detail.npz")
    ndvi = d["ndvi"].astype(np.float32)
    x0, y0, x1, y1 = d["bounds"]
    ny, nx = ndvi.shape
    px = (x1 - x0) / nx
    rng = np.random.default_rng(7)
    cand = []
    # pixels de 10 m misturam copa com telhado: na cidade, NDVI de 0,3 já indica árvore no quintal
    for iy in range(ny):
        for ix in range(nx):
            v = ndvi[iy, ix]
            if v < 0.3:
                continue
            p = min((v - 0.28) / 0.34, 1.0)
            for _ in range(1 + (v > 0.65)):
                if rng.random() > p:
                    continue
                cand.append((x0 + (ix + rng.random()) * px - ORIGIN_E, y1 - (iy + rng.random()) * px - ORIGIN_N, v, 0))
    # praças e áreas verdes: bem arborizadas (evitando os caminhos)
    for poly, cls in green:
        if cls not in ("park", "garden"):
            continue
        bx0, by0, bx1, by1 = poly.bounds
        k = int(poly.area / 85)
        xs, ys = rng.uniform(bx0, bx1, k * 2), rng.uniform(by0, by1, k * 2)
        inside = shapely.contains_xy(poly, xs, ys)
        for x, y in list(zip(xs[inside], ys[inside]))[:k]:
            cand.append((x, y, 0.8, 0))
    # quintais perto do trajeto: mangueiras e frutíferas atrás das casas (o NDVI de 10 m não separa do telhado)
    zone = route_line.buffer(NEAR_ROUTE)
    bx0, by0, bx1, by1 = zone.bounds
    k = int(zone.area / 260)
    xs, ys = rng.uniform(bx0, bx1, k), rng.uniform(by0, by1, k)
    ok = shapely.contains_xy(zone, xs, ys)
    xs, ys = xs[ok], ys[ok]
    near_house = np.zeros(len(xs), bool)
    near_house[STRtree(building_polys).query(shapely.points(xs, ys), predicate="dwithin", distance=12.0)[0]] = True
    for x, y in zip(xs[near_house], ys[near_house]):
        cand.append((x, y, 0.7, 0))
    # árvores de calçada nas ruas perto do trajeto
    for g, w, cls in center_all:
        if cls not in ("residential", "tertiary", "primary", "secondary", "unclassified") or g.distance(route_line) > NEAR_ROUTE:
            continue
        for part in getattr(g, "geoms", [g]):
            for side in (-1, 1):
                dd = rng.uniform(3, 12)
                while dd < part.length - 3:
                    if rng.random() < 0.28:
                        p = part.interpolate(dd)
                        q = part.interpolate(min(dd + 1.0, part.length))
                        tx, ty = q.x - p.x, q.y - p.y
                        L = math.hypot(tx, ty) or 1
                        off = w / 2 + 1.0
                        cand.append((p.x - ty / L * off * side, p.y + tx / L * off * side, 0.6, 1))
                    dd += rng.uniform(9, 16)
    cand = np.array(cand, np.float32)
    pts = shapely.points(cand[:, 0], cand[:, 1])
    keep = np.ones(len(cand), bool)
    keep[STRtree([b.buffer(1.2) for b in building_polys]).query(pts, predicate="intersects")[0]] = False
    no_go = shapely.union_all([paved.buffer(0.6), unpaved.buffer(0.6), walk.buffer(1.2), water])
    shapely.prepare(no_go)
    keep &= ~shapely.contains_xy(no_go, cand[:, 0], cand[:, 1])
    cand = cand[keep]
    dist = shapely.distance(shapely.points(cand[:, 0], cand[:, 1]), route_line)
    cand = cand[rng.random(len(cand)) < np.clip(1.25 - dist / 2200.0, 0.18, 1.0)]
    out = []
    for x, y, v, street in cand:
        kind, s = tree_kind(rng, v > 0.75, bool(street))
        out.append([x, y, kind, s, rng.random() * 6.283, rng.random()])
    print(f"  árvores: {len(out)} ({int(cand[:, 3].sum())} de calçada)")
    return np.asarray(out, np.float32)


def build_grass(green, building_polys):
    buf = MeshBuf(("seed",))
    blockers = shapely.union_all(building_polys)
    for poly, cls in green:
        p = poly.difference(blockers)
        for q in getattr(p, "geoms", [p]):
            if q.geom_type == "Polygon" and q.area > 4:
                add_flat(buf, q, 0.02, dict(seed=1.0 if cls == "pitch" else 0.0))
    return buf


# ------------------------------------------------------------------ água
def build_water():
    buf = MeshBuf(("seed",))
    polys = []
    for r in pq.read_table(OV / "water.parquet").to_pylist():
        g = to_local(from_wkb(r["geometry"]))
        if g.geom_type not in ("Polygon", "MultiPolygon") or not inside_detail(g):
            continue
        for p in getattr(g, "geoms", [g]):
            p = p.buffer(0)
            polys.append(p)
            add_flat(buf, p, 0.08, dict(seed=0.0))
    return buf, (shapely.union_all(polys) if polys else shapely.GeometryCollection())


def route_line_local():
    scene = json.load(open(PUBLIC / "scene.json"))
    pts = np.asarray(scene["route"]["points"])
    return shapely.LineString(np.column_stack([pts[:, 0], -pts[:, 1]])), scene


def main():
    """Gera tudo e salva em .cache/city_geometry.npz (lido por scripts/blender_build.py)."""
    import time
    t0 = time.time()
    route_line, scene = route_line_local()
    print("ruas…")
    roads, paved, unpaved, walk, center_all = road_meshes()
    print("prédios…")
    walls, roofs, gables, props, bpolys = build_buildings(route_line)
    print("água…")
    water, water_u = build_water()
    print("muros…")
    muros = build_walls(bpolys, paved, unpaved, route_line)
    print("carros…")
    cars = build_cars(center_all, route_line, bpolys)
    print("árvores…")
    green = load_green_areas()
    trees = build_trees(bpolys, paved, unpaved, walk, water_u, route_line, center_all, green)
    grass = build_grass(green, bpolys)
    out = {}
    for name, buf in [("walls", walls), ("roofs", roofs), ("gables", gables), ("panels", props["panels"]), ("water", water),
                      ("muros", muros), ("grass", grass)] + [(k, v) for k, v in roads.items()]:
        arrs = buf.arrays()
        if arrs is None:
            continue
        for k, v in arrs.items():
            out[f"{name}__{k}"] = v
    out["tanks"] = np.asarray(props["tanks"], np.float32).reshape(-1, 5)
    out["cars"] = cars
    out["trees"] = trees
    np.savez_compressed(CACHE / "city_geometry.npz", **out)
    print(f"ok em {time.time() - t0:.0f}s: " + ", ".join(f"{k.split('__')[0]}={len(v)}" for k, v in out.items() if k.endswith("__sizes")))


if __name__ == "__main__":
    main()
