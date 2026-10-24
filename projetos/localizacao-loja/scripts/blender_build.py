"""Monta a cena realista no Blender (Cycles) e salva em .cache/cidade.blend.

Uso (com o Python que tem o pacote bpy): python scripts/blender_build.py
Entradas: .cache/city_geometry.npz (scripts/city_geometry.py), public/scene/{scene,frames}.json e as texturas de satélite.
A câmera e as animações vêm de frames.json (exportado do TypeScript), então o render fica alinhado com os overlays.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
SCENE_DIR = ROOT / "public/scene"
RES = (540, 960)           # renderizado na metade e ampliado para 1080x1920 no pós (~5 s por frame em 4 núcleos)
SUN_AZ, SUN_EL = 250.0, 36.0
HAZE_AMOUNT = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8
HAZE_COLOR = (0.5, 0.56, 0.64, 1.0)
MIST_DEPTH = 100000.0      # passe Mist linear até 100 km; o trecho de névoa de cada frame é recortado no compositor

G = np.load(CACHE / "city_geometry.npz")
SCENE = json.load(open(SCENE_DIR / "scene.json"))
FRAMES = json.load(open(SCENE_DIR / "frames.json"))["frames"]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def srgb(h):
    """Hex sRGB -> RGBA linear (para cores fixas dos materiais)."""
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


# ------------------------------------------------------------------ mini-DSL para nós de material
class Nodes:
    def __init__(self, tree):
        self.t = tree
        self.nodes = tree.nodes
        self.links = tree.links

    def new(self, kind, **props):
        n = self.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.links.new(a, b)

    def _in(self, sock, value):
        if hasattr(value, "is_output"):
            self.link(value, sock)
        elif value is not None:
            sock.default_value = value

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self._in(n.inputs[i], v)
        return n.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        n = self.new("ShaderNodeVectorMath", operation=op)
        self._in(n.inputs[0], a)
        if b is not None:
            self._in(n.inputs[1], b)
        if scale is not None:
            self._in(n.inputs["Scale"], scale)
        return n.outputs[0] if op not in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else n.outputs["Value"]

    def mix(self, fac, a, b, blend="MIX", kind="RGBA"):
        n = self.new("ShaderNodeMix", data_type=kind, blend_type=blend, clamp_factor=True)
        suffix = {"RGBA": "Color", "FLOAT": "Float", "VECTOR": "Vector"}[kind]
        socks = {s.identifier: s for s in n.inputs}
        self._in(socks["Factor_Float"], fac)
        self._in(socks["A_" + suffix], a)
        self._in(socks["B_" + suffix], b)
        return {s.identifier: s for s in n.outputs}["Result_" + suffix]

    def attr(self, name, kind="GEOMETRY"):
        return self.new("ShaderNodeAttribute", attribute_name=name, attribute_type=kind)

    def noise(self, vec, scale, detail=2.0, rough=0.5, dims="3D"):
        n = self.new("ShaderNodeTexNoise", noise_dimensions=dims)
        self._in(n.inputs["Vector"], vec)
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        return n.outputs["Fac"]

    def ramp(self, fac, stops, interp="LINEAR"):
        n = self.new("ShaderNodeValToRGB")
        n.color_ramp.interpolation = interp
        self._in(n.inputs["Fac"], fac)
        els = n.color_ramp.elements
        for i, (pos, col) in enumerate(stops):
            e = els[i] if i < len(els) else els.new(pos)
            e.position = pos
            e.color = col
        return n.outputs["Color"]

    def smooth(self, e0, e1, x):
        n = self.new("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
        self._in(n.inputs["Value"], x)
        n.inputs["From Min"].default_value = e0
        n.inputs["From Max"].default_value = e1
        return n.outputs["Result"]

    def scale_color(self, col, f):
        return self.mix(1.0, col, f, blend="MULTIPLY")

    def separate(self, vec):
        n = self.new("ShaderNodeSeparateXYZ")
        self._in(n.inputs[0], vec)
        return n.outputs

    def combine(self, x, y, z):
        n = self.new("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self._in(n.inputs[i], v)
        return n.outputs[0]

    def bump(self, height, strength=0.4, distance=0.05, normal=None):
        n = self.new("ShaderNodeBump")
        self._in(n.inputs["Height"], height)
        n.inputs["Strength"].default_value = strength
        n.inputs["Distance"].default_value = distance
        if normal is not None:
            self._in(n.inputs["Normal"], normal)
        return n.outputs["Normal"]

    def principled(self, color, rough=0.8, metallic=0.0, normal=None, coat=0.0, emission=None, estrength=0.0, alpha=None):
        b = self.new("ShaderNodeBsdfPrincipled")
        self._in(b.inputs["Base Color"], color)
        self._in(b.inputs["Roughness"], rough)
        self._in(b.inputs["Metallic"], metallic)
        if normal is not None:
            self._in(b.inputs["Normal"], normal)
        if coat:
            b.inputs["Coat Weight"].default_value = coat
        if emission is not None:
            self._in(b.inputs["Emission Color"], emission)
            b.inputs["Emission Strength"].default_value = estrength
        if alpha is not None:
            self._in(b.inputs["Alpha"], alpha)
        return b.outputs["BSDF"]


def material(name, build):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N = Nodes(nt)
    out = N.new("ShaderNodeOutputMaterial")
    N.link(build(N), out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ materiais
def mat_roof(N):
    uv = N.separate(N.new("ShaderNodeUVMap", uv_map="UVMap").outputs["UV"])
    u, v = uv[0], uv[1]
    kind = N.attr("kind").outputs["Fac"]
    tone = N.attr("tone").outputs["Fac"]
    seed = N.attr("seed").outputs["Fac"]
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    mold = N.smooth(0.5, 0.78, N.noise(pos, 0.22, 3.0, 0.6))          # manchas escuras de mofo/sujeira
    # telha colonial: variação de cor por peça (fileiras de 34 cm, canais de 22 cm)
    tid = N.combine(N.math("FLOOR", N.math("DIVIDE", u, 0.22)), N.math("FLOOR", N.math("DIVIDE", v, 0.34)), N.math("MULTIPLY", seed, 97.0))
    tile_rand = N.new("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    N.link(tid, tile_rand.inputs["Vector"])
    base_tile = N.ramp(tone, [(0.0, srgb("#5f3a2d")), (0.2, srgb("#7a4532")), (0.45, srgb("#8f5238")), (0.7, srgb("#a05f42")), (0.88, srgb("#a8705a")), (1.0, srgb("#8a6a5c"))])
    tile_var = N.math("ADD", 0.8, N.math("MULTIPLY", tile_rand.outputs["Value"], 0.32))
    age = N.noise(pos, 0.35, 3.0, 0.6)
    tile_c = N.scale_color(N.scale_color(base_tile, tile_var), N.math("ADD", 0.74, N.math("MULTIPLY", age, 0.4)))
    old_roof = N.math("MULTIPLY", N.smooth(0.45, 1.0, seed), 0.6)       # telhados velhos escurecem e acinzentam
    tile_c = N.mix(old_roof, tile_c, srgb("#55473d"))
    tile_c = N.mix(N.math("MULTIPLY", mold, 0.55), tile_c, srgb("#35302a"))
    # fibrocimento ondulado, com escorridos e líquen
    streak = N.noise(N.combine(N.math("MULTIPLY", u, 1.3), N.math("MULTIPLY", v, 0.12), seed), 1.0, 2.0)
    fc_c = N.scale_color(N.ramp(tone, [(0.0, srgb("#666967")), (0.5, srgb("#858885")), (1.0, srgb("#aeb0ab"))]), N.math("ADD", 0.66, N.math("MULTIPLY", streak, 0.5)))
    fc_c = N.mix(N.math("MULTIPLY", mold, 0.7), fc_c, srgb("#3f413c"))
    # metal: galvanizado (com ferrugem) ou pintado
    rust = N.math("MULTIPLY", N.smooth(0.58, 0.7, N.noise(pos, 0.6, 3.0)), N.smooth(0.35, 0.1, tone))
    painted = N.ramp(tone, [(0.0, srgb("#2f5d86")), (0.3, srgb("#3e6b52")), (0.55, srgb("#8c3a2f")), (0.8, srgb("#c9c9c4"))], interp="CONSTANT")
    galv = N.ramp(tone, [(0.0, srgb("#9a9ea1")), (1.0, srgb("#cfd1d1"))])
    m_c = N.mix(N.math("LESS_THAN", seed, 0.3), galv, painted)
    m_c = N.mix(rust, m_c, srgb("#7b4a2c"))
    # laje: concreto manchado; algumas impermeabilizadas (vermelho ou branco)
    stain = N.noise(pos, 0.5, 3.0, 0.65)
    slab_base = N.mix(N.smooth(0.82, 0.86, tone), srgb("#9a9791"), srgb("#8a3d2e"))
    slab_base = N.mix(N.smooth(0.16, 0.12, tone), slab_base, srgb("#d9d8d2"))
    slab_c = N.scale_color(slab_base, N.math("ADD", 0.6, N.math("MULTIPLY", stain, 0.5)))
    slab_c = N.mix(N.math("MULTIPLY", mold, 0.5), slab_c, srgb("#4c4a45"))
    # escolhe pelo tipo
    w1 = N.math("COMPARE", kind, 1.0, 0.5)
    w2 = N.math("COMPARE", kind, 2.0, 0.5)
    w3 = N.math("COMPARE", kind, 3.0, 0.5)
    c = N.mix(w1, tile_c, fc_c)
    c = N.mix(w2, c, m_c)
    c = N.mix(w3, c, slab_c)
    rough = N.mix(w2, N.mix(w3, 0.8, 0.92, kind="FLOAT"), N.math("ADD", 0.34, N.math("MULTIPLY", rust, 0.5)), kind="FLOAT")
    return N.principled(c, rough, N.math("MULTIPLY", w2, N.math("SUBTRACT", 0.4, rust)))


def mat_wall(N):
    uv = N.separate(N.new("ShaderNodeUVMap", uv_map="UVMap").outputs["UV"])
    u, v = uv[0], uv[1]
    base = N.new("ShaderNodeCombineColor")
    for i, ch in enumerate("rgb"):
        N.link(N.attr(ch).outputs["Fac"], base.inputs[i])
    lin = N.new("ShaderNodeGamma")
    N.link(base.outputs[0], lin.inputs["Color"])
    lin.inputs["Gamma"].default_value = 2.2
    seed = N.attr("seed").outputs["Fac"]
    floors = N.attr("floors").outputs["Fac"]
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    plaster = N.math("ADD", 0.9, N.math("MULTIPLY", N.noise(pos, 1.6, 3.0, 0.55), 0.2))
    grime = N.math("SUBTRACT", 1.0, N.math("MULTIPLY", N.smooth(0.9, 0.0, v), 0.32))
    streak = N.math("ADD", 0.86, N.math("MULTIPLY", N.noise(N.combine(N.math("MULTIPLY", u, 2.5), N.math("MULTIPLY", v, 0.15), seed), 1.0), 0.2))
    wall_c = N.scale_color(N.scale_color(N.scale_color(lin.outputs[0], plaster), grime), streak)
    # janelas: uma a cada 2,6–4,2 m, por andar
    spacing = N.math("ADD", 2.6, N.math("MULTIPLY", seed, 1.6))
    wx = N.math("FRACT", N.math("ADD", N.math("DIVIDE", u, spacing), N.math("MULTIPLY", seed, 7.0)))
    fl = N.math("FLOOR", N.math("DIVIDE", v, 3.0))
    vf = N.math("SUBTRACT", v, N.math("MULTIPLY", fl, 3.0))
    has_floor = N.math("LESS_THAN", fl, floors)
    win = N.math("MULTIPLY", N.math("MULTIPLY", N.math("MULTIPLY", N.math("GREATER_THAN", wx, 0.32), N.math("LESS_THAN", wx, 0.6)),
                                       N.math("MULTIPLY", N.math("GREATER_THAN", vf, 1.05), N.math("LESS_THAN", vf, 2.1))), has_floor)
    frame = N.math("MULTIPLY", N.math("MULTIPLY", N.math("MULTIPLY", N.math("GREATER_THAN", wx, 0.3), N.math("LESS_THAN", wx, 0.62)),
                                         N.math("MULTIPLY", N.math("GREATER_THAN", vf, 1.0), N.math("LESS_THAN", vf, 2.15))), has_floor)
    c = N.mix(N.math("SUBTRACT", frame, win), wall_c, srgb("#e9e7e1"))
    c = N.mix(win, c, srgb("#14191d"))
    rough = N.mix(win, 0.88, 0.08, kind="FLOAT")
    return N.principled(c, rough, 0.0)


def mat_asphalt(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    big = N.noise(pos, 0.035, 2.0)
    mid = N.noise(pos, 0.45, 3.0, 0.6)
    fine = N.noise(pos, 7.0, 2.0)
    dust = N.smooth(0.45, 0.75, N.noise(pos, 0.08, 3.0, 0.6))
    c = N.scale_color(srgb("#4d4b49"), N.math("ADD", 0.74, N.math("MULTIPLY", big, 0.5)))
    c = N.mix(N.math("MULTIPLY", N.smooth(0.62, 0.66, mid), 0.7), c, srgb("#2c2c2d"))     # remendos
    c = N.mix(N.math("MULTIPLY", dust, 0.35), c, srgb("#7a6253"))
    c = N.scale_color(c, N.math("ADD", 0.9, N.math("MULTIPLY", fine, 0.18)))
    return N.principled(c, 0.88, 0.0)


def mat_dirt(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    n1 = N.noise(pos, 0.12, 3.0, 0.6)
    n2 = N.noise(pos, 2.5, 3.0, 0.6)
    c = N.ramp(n1, [(0.0, srgb("#8d4d33")), (0.5, srgb("#a3613f")), (1.0, srgb("#b98260"))])
    c = N.scale_color(c, N.math("ADD", 0.85, N.math("MULTIPLY", n2, 0.25)))
    return N.principled(c, 0.97, 0.0)


def mat_sidewalk(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    brick = N.new("ShaderNodeTexBrick", offset=0.0)
    N.link(pos, brick.inputs["Vector"])
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 1.0
    brick.inputs["Color1"].default_value = srgb("#b9b2a6")
    brick.inputs["Color2"].default_value = srgb("#aaa397")
    brick.inputs["Mortar"].default_value = srgb("#7d776d")
    dirt = N.noise(pos, 0.6, 3.0, 0.6)
    c = N.scale_color(brick.outputs["Color"], N.math("ADD", 0.72, N.math("MULTIPLY", dirt, 0.42)))
    return N.principled(c, 0.9, 0.0)


def mat_concrete(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    c = N.scale_color(srgb("#c6c1b6"), N.math("ADD", 0.78, N.math("MULTIPLY", N.noise(pos, 1.2, 3.0), 0.3)))
    return N.principled(c, 0.85)


def mat_marks(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    wear = N.smooth(0.42, 0.62, N.noise(pos, 1.4, 3.0, 0.6))
    c = N.mix(N.math("MULTIPLY", wear, 0.7), srgb("#e8e5dc"), srgb("#3b3b3d"))
    return N.principled(c, 0.55)


def mat_water(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    ripple = N.noise(N.vmath("MULTIPLY", pos, (1.0, 1.0, 0.0)), 0.8, 3.0, 0.55)
    return N.principled(srgb("#1b3b33"), 0.04, 0.0, N.bump(ripple, 0.06, 0.05))


def mat_ground(img_path, detail):
    def build(N):
        tex = N.new("ShaderNodeTexImage", interpolation="Cubic")
        tex.image = bpy.data.images.load(str(img_path))
        c = tex.outputs["Color"]
        hs = N.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = 0.8
        hs.inputs["Value"].default_value = 0.95
        N.link(c, hs.inputs["Color"])
        sat = hs.outputs["Color"]
        if not detail:
            return N.principled(sat, 1.0)
        pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
        rgb = N.new("ShaderNodeSeparateColor")
        N.link(tex.outputs["Color"], rgb.inputs["Color"])
        green = N.math("SUBTRACT", rgb.outputs["Green"], rgb.outputs["Red"])
        n_patch = N.noise(pos, 0.11, 3.0, 0.6)
        n_fine = N.noise(pos, 1.3, 4.0, 0.6)
        grass_w = N.smooth(-0.06, 0.03, N.math("ADD", green, N.math("MULTIPLY", N.math("SUBTRACT", n_patch, 0.5), 0.12)))
        patio_w = N.math("MULTIPLY", N.smooth(0.52, 0.58, N.noise(pos, 0.06, 2.0)), N.math("SUBTRACT", 1.0, grass_w))
        grass_c = N.ramp(N.noise(pos, 0.3, 3.0), [(0.0, srgb("#5a6e2e")), (0.5, srgb("#6f7f38")), (1.0, srgb("#8d8a4a"))])
        soil_c = N.ramp(n_patch, [(0.0, srgb("#83604a")), (0.5, srgb("#957258")), (1.0, srgb("#a58b70"))])
        local = N.mix(grass_w, soil_c, grass_c)
        local = N.mix(patio_w, local, srgb("#b3aea4"))
        # o detalhe local some perto da borda do plano, para emendar sem degrau com o chão regional
        xyz = N.separate(pos)
        edge = N.math("MAXIMUM", N.math("ABSOLUTE", xyz[0]), N.math("ABSOLUTE", xyz[1]))
        c = N.mix(N.math("MULTIPLY", 0.5, N.smooth(5600.0, 3800.0, edge)), sat, local)
        c = N.scale_color(c, N.math("ADD", 0.84, N.math("MULTIPLY", n_fine, 0.3)))
        # borda do plano da cidade se dissolve no chão regional (texturas de resoluções diferentes)
        fade = N.new("ShaderNodeMixShader")
        N.link(N.smooth(6100.0, 5200.0, edge), fade.inputs["Fac"])
        N.link(N.new("ShaderNodeBsdfTransparent").outputs[0], fade.inputs[1])
        N.link(N.principled(c, 0.96, 0.0), fade.inputs[2])
        return fade.outputs[0]
    return build


def mat_grass(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    uv = N.separate(N.new("ShaderNodeUVMap", uv_map="UVMap").outputs["UV"])
    u, v = uv[0], uv[1]
    pitch = N.attr("seed").outputs["Fac"]          # 1 = campo de futebol (UV em metros alinhada ao campo)
    L = N.attr("plen").outputs["Fac"]
    W = N.attr("pwid").outputs["Fac"]
    n1 = N.noise(pos, 0.15, 3.0, 0.6)
    n2 = N.noise(pos, 2.0, 3.0, 0.6)
    park = N.ramp(n1, [(0.0, srgb("#4a6526")), (0.45, srgb("#5d7a2f")), (0.75, srgb("#73843a")), (1.0, srgb("#93874c"))])
    park = N.scale_color(park, N.math("ADD", 0.85, N.math("MULTIPLY", n2, 0.28)))
    # campo: verde cuidado, com faixas de corte ao longo do comprimento e desgaste leve
    band = N.math("GREATER_THAN", N.math("FRACT", N.math("DIVIDE", u, N.math("DIVIDE", L, 14.0))), 0.5)
    field = N.scale_color(srgb("#4b7a2a"), N.math("ADD", 0.9, N.math("MULTIPLY", band, 0.16)))
    field = N.scale_color(field, N.math("ADD", 0.88, N.math("MULTIPLY", n1, 0.22)))
    # marcações (linhas de 30 cm; áreas e círculo proporcionais ao tamanho do campo)
    hw = 0.15
    k = N.math("MINIMUM", 1.0, N.math("DIVIDE", L, 105.0))
    um = N.math("MINIMUM", u, N.math("SUBTRACT", L, u))
    vc = N.math("ABSOLUTE", N.math("SUBTRACT", v, N.math("MULTIPLY", W, 0.5)))
    border = N.math("LESS_THAN", N.math("MINIMUM", um, N.math("MINIMUM", v, N.math("SUBTRACT", W, v))), 2 * hw)
    half = N.math("LESS_THAN", N.math("ABSOLUTE", N.math("SUBTRACT", u, N.math("MULTIPLY", L, 0.5))), hw)
    rc = N.vmath("LENGTH", N.combine(N.math("SUBTRACT", u, N.math("MULTIPLY", L, 0.5)), N.math("SUBTRACT", v, N.math("MULTIPLY", W, 0.5)), 0.0))
    circle = N.math("LESS_THAN", N.math("ABSOLUTE", N.math("SUBTRACT", rc, N.math("MULTIPLY", k, 9.15))), hw)

    def box(depth, half_width):
        d = N.math("MULTIPLY", k, depth)
        w = N.math("MULTIPLY", k, half_width)
        front = N.math("MULTIPLY", N.math("LESS_THAN", N.math("ABSOLUTE", N.math("SUBTRACT", um, d)), hw), N.math("LESS_THAN", vc, N.math("ADD", w, hw)))
        side = N.math("MULTIPLY", N.math("LESS_THAN", N.math("ABSOLUTE", N.math("SUBTRACT", vc, w)), hw), N.math("LESS_THAN", um, d))
        return N.math("MAXIMUM", front, side)
    lines = N.math("MAXIMUM", N.math("MAXIMUM", border, half), N.math("MAXIMUM", circle, N.math("MAXIMUM", box(16.5, 20.16), box(5.5, 9.16))))
    c = N.mix(pitch, park, field)
    c = N.mix(N.math("MULTIPLY", lines, pitch), c, srgb("#e6eae2"))
    return N.principled(c, 0.92, 0.0)


def mat_stands(N):
    """Arquibancada de concreto: faixas suaves de degraus (v = metros a partir da beira) e paredes lisas."""
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    v = N.separate(N.new("ShaderNodeUVMap", uv_map="UVMap").outputs["UV"])[1]
    wall = N.attr("seed").outputs["Fac"]
    rows = N.smooth(0.25, 0.5, N.math("FRACT", N.math("DIVIDE", v, 1.6)))
    c = N.mix(rows, srgb("#9d9a93"), srgb("#c3c0b8"))
    c = N.mix(wall, c, srgb("#d6d4cd"))
    c = N.scale_color(c, N.math("ADD", 0.84, N.math("MULTIPLY", N.noise(pos, 0.4, 3.0, 0.6), 0.3)))
    return N.principled(c, 0.9, 0.0)


def mat_track(N):
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    n1 = N.noise(pos, 0.3, 3.0, 0.6)
    c = N.ramp(n1, [(0.0, srgb("#a8917a")), (0.5, srgb("#b9a48c")), (1.0, srgb("#c4b39d"))])
    return N.principled(c, 0.95, 0.0)


def mat_leaves(N):
    seed = N.attr("tseed", "INSTANCER").outputs["Fac"]
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    vor = N.new("ShaderNodeTexVoronoi")
    N.link(pos, vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = 2.2
    base = N.ramp(seed, [(0.0, srgb("#2a4519")), (0.3, srgb("#36561f")), (0.6, srgb("#426327")), (0.85, srgb("#4d6b2c")), (1.0, srgb("#5a7234"))])
    clump = N.math("ADD", 0.6, N.math("MULTIPLY", vor.outputs["Distance"], 0.9))
    c = N.scale_color(base, clump)
    leaf = N.principled(c, 0.78, 0.0, N.bump(vor.outputs["Distance"], 0.6, 0.15))
    trans = N.new("ShaderNodeBsdfTranslucent")
    N.link(c, trans.inputs["Color"])
    mixs = N.new("ShaderNodeMixShader")
    mixs.inputs["Fac"].default_value = 0.22
    N.link(leaf, mixs.inputs[1])
    N.link(trans.outputs[0], mixs.inputs[2])
    return mixs.outputs[0]


def mat_simple(color, rough=0.8, metallic=0.0, coat=0.0):
    return lambda N: N.principled(srgb(color), rough, metallic, coat=coat)


def mat_instance_color(attr, rough, metallic=0.0, coat=0.0):
    def build(N):
        a = N.attr(attr, "INSTANCER")
        return N.principled(a.outputs["Color"], rough, metallic, coat=coat)
    return build


def mat_panel(N):
    uv = N.new("ShaderNodeUVMap", uv_map="UVMap").outputs["UV"]
    brick = N.new("ShaderNodeTexBrick", offset=0.0)
    N.link(uv, brick.inputs["Vector"])
    brick.inputs["Scale"].default_value = 6.0
    brick.inputs["Mortar Size"].default_value = 0.03
    brick.inputs["Color1"].default_value = srgb("#16243d")
    brick.inputs["Color2"].default_value = srgb("#1a2a45")
    brick.inputs["Mortar"].default_value = srgb("#b9bec4")
    return N.principled(brick.outputs["Color"], 0.12, 0.3)


# ------------------------------------------------------------------ malhas
def mesh_from_npz(name, prefix, mat, z_offset=0.0):
    if prefix + "__verts" not in G:
        return None
    V = G[prefix + "__verts"].astype(np.float32)
    if z_offset:
        V = V + np.array([0, 0, z_offset], np.float32)
    sizes = G[prefix + "__sizes"].astype(np.int32)
    n = len(V)
    me = bpy.data.meshes.new(name)
    me.vertices.add(n)
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(n)
    me.loops.foreach_set("vertex_index", np.arange(n, dtype=np.int32))
    me.polygons.add(len(sizes))
    me.polygons.foreach_set("loop_start", (np.cumsum(sizes) - sizes).astype(np.int32))
    me.polygons.foreach_set("loop_total", sizes)
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", G[prefix + "__uvs"].astype(np.float32).ravel())
    for key in G.files:
        if key.startswith(prefix + "__attr_"):
            a = me.attributes.new(key.split("__attr_")[1], "FLOAT", "FACE")
            a.data.foreach_set("value", G[key].astype(np.float32))
    me.update()
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def plane(name, size, z, mat):
    me = bpy.data.meshes.new(name)
    h = size / 2
    me.from_pydata([(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def join_meshes(name, parts):
    """parts: lista de (verts Nx3, faces lista, material_index)."""
    verts, faces, mids = [], [], []
    off = 0
    for V, F, mi in parts:
        verts.extend(map(tuple, V))
        faces.extend([tuple(i + off for i in f) for f in F])
        mids.extend([mi] * len(F))
        off += len(V)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("material_index", np.asarray(mids, np.int32))
    me.update()
    return me


def box(cx, cy, cz, sx, sy, sz):
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2
    V = np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return V, F


def cylinder(cx, cy, z0, r, h, n=12):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    bottom = np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, z0)])
    top = bottom + [0, 0, h]
    V = np.vstack([bottom, top])
    F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)] + [tuple(range(n, 2 * n)), tuple(range(n - 1, -1, -1))]
    return V, F


def ico_cluster(rng, n, rx, rz, cz, sphere_r):
    """Copa de árvore: aglomerado de esferas deformadas por ruído (silhueta orgânica)."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
    ico = bpy.context.active_object
    base = np.array([v.co[:] for v in ico.data.vertices])
    faces = [tuple(p.vertices) for p in ico.data.polygons]
    bpy.data.objects.remove(ico, do_unlink=True)
    parts = []
    for i in range(n):
        ang = rng.uniform(0, 2 * np.pi)
        rad = rng.uniform(0, rx * 0.55) if i else 0.0
        c = np.array([np.cos(ang) * rad, np.sin(ang) * rad, cz + rng.uniform(-rz * 0.25, rz * 0.3)])
        s = sphere_r * rng.uniform(0.75, 1.15)
        V = base * s
        # deformação suave (soma de senoides) para quebrar a esfera
        k = rng.uniform(1.5, 3.0, 3)
        V = V * (1 + 0.16 * np.sin(k[0] * V[:, :1] + k[1] * V[:, 1:2] * 0.7 + k[2] * V[:, 2:3]))
        parts.append((V + c, faces, 0))
    return parts


def frond(origin, ang, length, width, droop, tilt):
    """Folha de palmeira: tira curva com 8 segmentos."""
    pts = []
    d = np.array([np.cos(ang), np.sin(ang), 0.0])
    side = np.array([-np.sin(ang), np.cos(ang), 0.0])
    for i in range(9):
        t = i / 8
        p = origin + d * length * t + np.array([0, 0, length * (tilt * t - droop * t * t)])
        w = width * np.sin(np.pi * min(1.0, t * 1.15)) + 0.02
        pts += [p - side * w / 2, p + side * w / 2]
    V = np.array(pts)
    F = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(8)]
    return V, F


def arena_sign():
    """Letreiro verde "ARENA DO MUNICÍPIO VERDE" em cima da cobertura do pórtico, virado para a avenida."""
    if "arena_sign" not in G:
        return
    x, y, z, ang = (float(v) for v in G["arena_sign"])
    cu = bpy.data.curves.new("letreiro", "FONT")
    cu.body = "ARENA DO MUNICÍPIO VERDE"
    cu.size = 1.5
    cu.extrude = 0.08
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new("letreiro", cu)
    ob.location = (x, y, z + 0.05)
    ob.rotation_euler = (math.pi / 2, 0.0, ang)
    sc.collection.objects.link(ob)
    cu.materials.append(material("letreiro", mat_simple("#1f8a3c", 0.45)))


def make_tree_variants():
    coll = bpy.data.collections.new("tree_variants")
    rng = np.random.default_rng(3)
    leaves = material("folhas", mat_leaves)
    bark = material("tronco", mat_simple("#4f4033", 0.9))
    specs = []
    # 0 mangueira (copa larga e densa), 1 copa média, 2 arvoreta
    for i, (n, rx, rz, cz, sr, trunk_h, trunk_r) in enumerate([(11, 5.5, 4.2, 6.2, 2.6, 3.4, 0.35), (7, 3.6, 3.0, 4.6, 2.0, 2.6, 0.22), (5, 2.2, 2.0, 2.9, 1.4, 1.6, 0.13)]):
        parts = ico_cluster(rng, n, rx, rz, cz, sr)
        tv, tf = cylinder(0, 0, 0, trunk_r, trunk_h + 0.6, 8)
        parts.append((tv, tf, 1))
        specs.append((f"tree_{i}", parts))
    # 3 coqueiro
    parts = []
    tv, tf = cylinder(0, 0, 0, 0.17, 10.0, 8)
    parts.append((tv, tf, 1))
    for k in range(11):
        V, F = frond(np.array([0, 0, 9.9]), k * 2 * np.pi / 11 + rng.uniform(-0.2, 0.2), rng.uniform(3.8, 4.8), 0.9, 1.1, 0.55)
        parts.append((V, F, 0))
    specs.append(("tree_3", parts))
    # 4 touceira de açaí
    parts = []
    for k in range(4):
        ox, oy = rng.uniform(-0.8, 0.8, 2)
        hh = rng.uniform(8.0, 11.5)
        tv, tf = cylinder(ox, oy, 0, 0.08, hh, 6)
        parts.append((tv, tf, 1))
        for j in range(7):
            V, F = frond(np.array([ox, oy, hh]), j * 2 * np.pi / 7 + rng.uniform(-0.3, 0.3), rng.uniform(2.2, 2.9), 0.55, 1.0, 0.45)
            parts.append((V, F, 0))
    specs.append(("tree_4", parts))
    for name, parts in specs:
        me = join_meshes(name, parts)
        me.materials.append(leaves)
        me.materials.append(bark)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
    return coll


def make_car_variants():
    coll = bpy.data.collections.new("car_variants")
    paint = material("pintura", mat_instance_color("ccol", 0.28, 0.45, coat=0.8))
    glass = material("vidro", mat_simple("#0b0e12", 0.05))
    tire = material("pneu", mat_simple("#111111", 0.9))
    # (comprimento, largura, altura da carroceria, cabine: comprimento, altura, deslocamento, caçamba)
    for i, (L, W, bh, cl, ch, co, bed) in enumerate([(3.9, 1.72, 0.72, 2.1, 0.55, -0.15, False), (4.5, 1.76, 0.7, 2.2, 0.52, -0.1, False),
                                                   (4.4, 1.85, 0.95, 2.6, 0.62, -0.2, False), (5.2, 1.86, 0.9, 1.6, 0.66, 0.85, True)]):
        parts = []
        V, F = box(0, 0, 0.3 + bh / 2, L, W, bh)
        parts.append((V, F, 0))
        V, F = box(co, 0, 0.3 + bh + ch / 2, cl, W * 0.88, ch)
        parts.append((V, F, 1))
        V, F = box(co, 0, 0.3 + bh + ch + 0.03, cl * 0.82, W * 0.8, 0.06)
        parts.append((V, F, 0))
        if bed:
            V, F = box(-L * 0.24, 0, 0.3 + bh + 0.02, L * 0.42, W * 0.84, 0.05)
            parts.append((V, F, 2))
        for sx in (-1, 1):
            for sy in (-1, 1):
                V, F = cylinder(sx * L * 0.32, sy * W * 0.43, 0.0, 0.32, 0.22, 10)
                # roda deitada -> girar para ficar em pé (eixo y)
                V = V - [sx * L * 0.32, sy * W * 0.43, 0.11]
                V = V @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
                V = V + [sx * L * 0.32, sy * W * 0.43, 0.32]
                parts.append((V, F, 2))
        me = join_meshes(f"car_{i}", parts)
        for m in (paint, glass, tire):
            me.materials.append(m)
        ob = bpy.data.objects.new(f"car_{i}", me)
        coll.objects.link(ob)
    return coll


def make_tank():
    coll = bpy.data.collections.new("tank_variants")
    mat = material("caixa_dagua", mat_instance_color("tcol", 0.45))
    V, F = cylinder(0, 0, 0, 0.68, 0.92, 16)
    V2, F2 = cylinder(0, 0, 0.92, 0.6, 0.12, 16)
    me = join_meshes("tank_0", [(V, F, 0), (V2, F2, 0)])
    me.materials.append(mat)
    ob = bpy.data.objects.new("tank_0", me)
    coll.objects.link(ob)
    return coll


def instancer(name, data, coll, attrs, scale_col=None):
    """Nuvem de pontos + Geometry Nodes 'Instance on Points' (instâncias vêm da coleção, índice = coluna 'kind')."""
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(data["pos"]))
    me.vertices.foreach_set("co", data["pos"].astype(np.float32).ravel())
    for k, (typ, arr) in attrs.items():
        a = me.attributes.new(k, typ, "POINT")
        a.data.foreach_set("vector" if typ == "FLOAT_VECTOR" else "color" if typ == "FLOAT_COLOR" else "value", np.asarray(arr, np.float32).ravel())
    me.update()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + "_gn", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n = ng.nodes
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    ci = n.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = coll
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop = n.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    ng.links.new(gi.outputs[0], iop.inputs["Points"])
    ng.links.new(ci.outputs[0], iop.inputs["Instance"])

    def named(nm, typ):
        a = n.new("GeometryNodeInputNamedAttribute")
        a.data_type = typ
        a.inputs["Name"].default_value = nm
        return a.outputs["Attribute"]
    ng.links.new(named("kind", "FLOAT"), iop.inputs["Instance Index"])
    ng.links.new(named("iscale", "FLOAT"), iop.inputs["Scale"])
    rot = n.new("ShaderNodeCombineXYZ")
    ng.links.new(named("irot", "FLOAT"), rot.inputs["Z"])
    ng.links.new(rot.outputs[0], iop.inputs["Rotation"])
    geo = iop.outputs["Instances"]
    # repassa atributos para o domínio de instância (lidos no shader com 'INSTANCER')
    for k, (typ, _) in attrs.items():
        if k in ("kind", "iscale", "irot"):
            continue
        st = n.new("GeometryNodeStoreNamedAttribute")
        st.data_type = "FLOAT_COLOR" if typ == "FLOAT_COLOR" else "FLOAT"
        st.domain = "INSTANCE"
        st.inputs["Name"].default_value = k
        ng.links.new(geo, st.inputs["Geometry"])
        ng.links.new(named(k, "FLOAT_COLOR" if typ == "FLOAT_COLOR" else "FLOAT"), st.inputs["Value"])
        geo = st.outputs["Geometry"]
    ng.links.new(geo, go.inputs[0])
    mod = ob.modifiers.new("instancias", "NODES")
    mod.node_group = ng
    return ob


# ------------------------------------------------------------------ elementos animados (rota, pin, anéis)
def route_ribbon():
    pts3 = np.asarray(SCENE["route"]["points"], np.float64)
    pts = np.column_stack([pts3[:, 0], -pts3[:, 1]])        # three (x, z) -> blender (x, y)
    along = np.asarray(SCENE["route"]["along"], np.float64)
    n = len(pts)
    V, nrm, side, al = [], [], [], []
    for i in range(n):
        a, b = pts[max(0, i - 3)], pts[min(n - 1, i + 3)]
        d = (b - a) / (np.linalg.norm(b - a) or 1)
        for s in (-1.0, 1.0):
            V.append((pts[i][0], pts[i][1], 0.0))
            nrm.append((-d[1], d[0], 0.0))
            side.append(s)
            al.append(along[i])
    F = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(n - 1)]
    objs = {}
    for name, z in (("rota", 0.75), ("rota_brilho", 0.55)):
        me = bpy.data.meshes.new(name)
        me.from_pydata(V, [], F)
        for k, typ, arr in (("nrm", "FLOAT_VECTOR", nrm), ("side", "FLOAT", side), ("along", "FLOAT", al)):
            a = me.attributes.new(k, typ, "POINT")
            a.data.foreach_set("vector" if typ == "FLOAT_VECTOR" else "value", np.asarray(arr, np.float32).ravel())
        me.update()
        ob = bpy.data.objects.new(name, me)
        sc.collection.objects.link(ob)
        ng = bpy.data.node_groups.new(name + "_largura", "GeometryNodeTree")
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        nn = ng.nodes
        gi, go = nn.new("NodeGroupInput"), nn.new("NodeGroupOutput")
        # meia largura animada por um nó Value (o Blender 5 não expõe as entradas do modificador como ID properties)
        width = nn.new("ShaderNodeValue")
        width.name = "meia_largura"
        width.outputs[0].default_value = 5.0
        a_n = nn.new("GeometryNodeInputNamedAttribute"); a_n.data_type = "FLOAT_VECTOR"; a_n.inputs["Name"].default_value = "nrm"
        a_s = nn.new("GeometryNodeInputNamedAttribute"); a_s.data_type = "FLOAT"; a_s.inputs["Name"].default_value = "side"
        mul = nn.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        ng.links.new(a_s.outputs["Attribute"], mul.inputs[0])
        ng.links.new(width.outputs[0], mul.inputs[1])
        vsc = nn.new("ShaderNodeVectorMath"); vsc.operation = "SCALE"
        ng.links.new(a_n.outputs["Attribute"], vsc.inputs[0])
        ng.links.new(mul.outputs[0], vsc.inputs["Scale"])
        add = nn.new("ShaderNodeVectorMath"); add.operation = "ADD"
        ng.links.new(vsc.outputs[0], add.inputs[0])
        add.inputs[1].default_value = (0, 0, z)
        sp = nn.new("GeometryNodeSetPosition")
        ng.links.new(gi.outputs[0], sp.inputs["Geometry"])
        ng.links.new(add.outputs[0], sp.inputs["Offset"])
        ng.links.new(sp.outputs[0], go.inputs[0])
        mod = ob.modifiers.new("largura", "NODES")
        mod.node_group = ng
        objs[name] = (ob, width)
    length = float(SCENE["route"]["length"])
    values = {}

    def ribbon_mat(glow):
        def build(N):
            prog = N.new("ShaderNodeValue", name="progresso")
            values.setdefault("prog", []).append(prog)
            al_ = N.attr("along").outputs["Fac"]
            sd = N.math("ABSOLUTE", N.attr("side").outputs["Fac"])
            vis = N.math("LESS_THAN", al_, prog.outputs[0])
            col = N.mix(N.math("DIVIDE", al_, length), srgb("#2f7dff"), srgb("#19d3ff"))
            emis = N.new("ShaderNodeEmission")
            transp = N.new("ShaderNodeBsdfTransparent")
            if glow:
                a = N.math("MULTIPLY", N.math("MULTIPLY", N.math("POWER", N.math("SUBTRACT", 1.0, sd), 2.0), 0.6), vis)
                N.link(N.mix(0.25, col, (1, 1, 1, 1)), emis.inputs["Color"])
                N.link(N.math("MULTIPLY", a, 1.5), emis.inputs["Strength"])
                add = N.new("ShaderNodeAddShader")
                N.link(transp.outputs[0], add.inputs[0])
                N.link(emis.outputs[0], add.inputs[1])
                return add.outputs[0]
            core = N.smooth(0.42, 0.0, sd)
            head = N.smooth(-60.0, 0.0, N.math("SUBTRACT", al_, prog.outputs[0]))
            c = N.mix(N.math("ADD", N.math("MULTIPLY", core, 0.55), N.math("MULTIPLY", head, 0.35)), col, (1, 1, 1, 1))
            N.link(c, emis.inputs["Color"])
            emis.inputs["Strength"].default_value = 3.6
            a = N.math("MULTIPLY", vis, N.smooth(1.0, 0.82, sd))
            mx = N.new("ShaderNodeMixShader")
            N.link(a, mx.inputs["Fac"])
            N.link(transp.outputs[0], mx.inputs[1])
            N.link(emis.outputs[0], mx.inputs[2])
            return mx.outputs[0]
        return build
    objs["rota"][0].data.materials.append(material("rota", ribbon_mat(False)))
    objs["rota_brilho"][0].data.materials.append(material("rota_brilho", ribbon_mat(True)))
    return objs, values


def glow_plane(name, color, kind):
    """Plano com brilho radial (ponta da rota) ou anéis pulsando (praça e loja)."""
    vals = {}

    def build(N):
        uv = N.new("ShaderNodeTexCoord").outputs["UV"]
        r = N.math("MULTIPLY", N.vmath("LENGTH", N.vmath("SUBTRACT", uv, (0.5, 0.5, 0.0))), 2.0)
        op = N.new("ShaderNodeValue", name="opacidade")
        vals["opacity"] = op
        if kind == "head":
            halo = N.math("POWER", N.math("MAXIMUM", N.math("SUBTRACT", 1.0, r), 0.0), 2.2)
            core = N.smooth(0.24, 0.12, r)
            a = N.math("ADD", N.math("MULTIPLY", halo, 0.8), core)
            col = N.mix(core, srgb(color), (1, 1, 1, 1))
            strength = 6.0
        else:
            ph = N.new("ShaderNodeValue", name="fase")
            vals["phase"] = ph
            a = N.math("MULTIPLY", N.smooth(0.22, 0.0, r), 0.6)
            for i in range(3):
                p = N.math("FRACT", N.math("ADD", ph.outputs[0], i / 3))
                ring = N.math("MULTIPLY", N.smooth(0.06, 0.0, N.math("ABSOLUTE", N.math("SUBTRACT", r, p))), N.math("SUBTRACT", 1.0, p))
                a = N.math("ADD", a, ring)
            col = srgb(color)
            strength = 4.0
        emis = N.new("ShaderNodeEmission")
        N._in(emis.inputs["Color"], col)
        N.link(N.math("MULTIPLY", N.math("MULTIPLY", a, op.outputs[0]), strength), emis.inputs["Strength"])
        add = N.new("ShaderNodeAddShader")
        N.link(N.new("ShaderNodeBsdfTransparent").outputs[0], add.inputs[0])
        N.link(emis.outputs[0], add.inputs[1])
        return add.outputs[0]
    ob = plane(name, 1.0, 0.0, material(name, build))
    return ob, vals


def make_pin():
    R = 0.36
    hc = 1 - R
    alpha = math.asin(R / hc)
    tl = math.sqrt(hc * hc - R * R)
    tx, ty = tl * math.sin(alpha), tl * math.cos(alpha)
    prof = [(0.0, 0.0)] + [(tx * i / 8, ty * i / 8) for i in range(1, 9)]
    phi0 = math.atan2(ty - hc, tx)
    prof += [(max(0.0, R * math.cos(phi0 + (math.pi / 2 - phi0) * i / 24)), hc + R * math.sin(phi0 + (math.pi / 2 - phi0) * i / 24)) for i in range(1, 25)]
    seg = 48
    V, F = [], []
    for j in range(seg):
        a = 2 * math.pi * j / seg
        for (r, z) in prof:
            V.append((r * math.cos(a), r * math.sin(a) * 0.62, z))
    m = len(prof)
    for j in range(seg):
        for i in range(m - 1):
            a0, a1 = j * m + i, ((j + 1) % seg) * m + i
            F.append((a0, a1, a1 + 1, a0 + 1))
    hv, hf = cylinder(0, 0, -(2 * R * 0.62 + 0.02) / 2, 0.15, 2 * R * 0.62 + 0.02, 24)
    hv = hv @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]]) + [0, 0, hc]  # eixo do furo ao longo de y
    me = join_meshes("pin", [(np.array(V), F, 0), (hv, hf, 1)])
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(material("pin", lambda N: N.principled(srgb("#ff2d55"), 0.22, 0.0, coat=0.6, emission=srgb("#ff2d55"), estrength=0.25)))
    me.materials.append(material("pin_furo", lambda N: N.principled((1, 1, 1, 1), 0.4, emission=(1, 1, 1, 1), estrength=0.6)))
    ob = bpy.data.objects.new("pin", me)
    sc.collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------ montagem
def build():
    print("malhas…", flush=True)
    m_roof = material("telhado", mat_roof)
    m_wall = material("parede", mat_wall)
    mesh_from_npz("paredes", "walls", m_wall)
    mesh_from_npz("oitoes", "gables", m_wall)
    mesh_from_npz("muros", "muros", m_wall)
    mesh_from_npz("telhados", "roofs", m_roof)
    mesh_from_npz("placas_solares", "panels", material("placa_solar", mat_panel))
    m_asphalt = material("asfalto", mat_asphalt)
    mesh_from_npz("asfalto", "asphalt", m_asphalt)
    mesh_from_npz("patio_arena", "plaza", m_asphalt)
    mesh_from_npz("arquibancada", "stands", material("arquibancada", mat_stands))
    mesh_from_npz("portico_arena", "portico", m_wall)
    arena_sign()
    mesh_from_npz("terra", "dirt", material("terra", mat_dirt))
    mesh_from_npz("calcada", "sidewalk", material("calcada", mat_sidewalk))
    mesh_from_npz("meio_fio", "curb", material("meio_fio", mat_concrete))
    mesh_from_npz("faixas", "marks", material("faixa", mat_marks))
    mesh_from_npz("agua", "water", material("agua", mat_water))
    mesh_from_npz("grama", "grass", material("grama", mat_grass))
    mesh_from_npz("pista", "track", material("pista", mat_track))
    plane("chao_regiao", 49152, -0.4, material("chao_regiao", mat_ground(SCENE_DIR / "sat_region.jpg", False)))
    plane("chao_cidade", 12288, -0.15, material("chao_cidade", mat_ground(SCENE_DIR / "sat_city.jpg", True)))

    print("instâncias…", flush=True)
    trees = G["trees"]
    instancer("arvores", {"pos": np.column_stack([trees[:, 0], trees[:, 1], np.zeros(len(trees))])}, make_tree_variants(), {
        "kind": ("FLOAT", trees[:, 2]), "iscale": ("FLOAT", trees[:, 3]), "irot": ("FLOAT", trees[:, 4]), "tseed": ("FLOAT", trees[:, 5])})
    cars = G["cars"]
    instancer("carros", {"pos": np.column_stack([cars[:, 0], cars[:, 1], np.full(len(cars), 0.03)])}, make_car_variants(), {
        "kind": ("FLOAT", cars[:, 3]), "iscale": ("FLOAT", np.ones(len(cars))), "irot": ("FLOAT", cars[:, 2]),
        "ccol": ("FLOAT_COLOR", np.column_stack([cars[:, 4:7] ** 2.2, np.ones(len(cars))]))})
    tanks = G["tanks"]
    blue = np.array([0.03, 0.14, 0.42])
    grey = np.array([0.55, 0.56, 0.55])
    tcol = np.where(tanks[:, 3:4] < 0.72, blue, grey)
    instancer("caixas_dagua", {"pos": tanks[:, :3]}, make_tank(), {
        "kind": ("FLOAT", np.zeros(len(tanks))), "iscale": ("FLOAT", np.ones(len(tanks))), "irot": ("FLOAT", tanks[:, 4]),
        "tcol": ("FLOAT_COLOR", np.column_stack([tcol, np.ones(len(tanks))]))})

    print("rota, pin e anéis…", flush=True)
    ribbons, rvals = route_ribbon()
    head, hvals = glow_plane("brilho_ponta", "#19d3ff", "head")
    ring_store, svals = glow_plane("anel_loja", "#ff3b6b", "ring")
    ring_start, pvals = glow_plane("anel_praca", "#2f7dff", "ring")
    store = SCENE["pois"]["store"]
    praca = SCENE["pois"]["praca"]
    ring_store.location = (store[0], -store[1], 0.9)
    ring_store.scale = (70, 70, 1)
    ring_start.location = (praca[0], -praca[1], 0.9)
    ring_start.scale = (150, 150, 1)
    pin = make_pin()
    pin.visible_shadow = False   # elemento gráfico: a sombra de um pin de 70 m parecia um buraco no chão

    print("luz…", flush=True)
    world = bpy.data.worlds.new("ceu")
    sc.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    wn = world.node_tree.nodes
    sky = wn.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(SUN_EL)
    sky.sun_rotation = math.radians(SUN_AZ)
    bg = wn["Background"]
    bg.inputs["Strength"].default_value = float(sys.argv[1]) if len(sys.argv) > 1 else 0.035
    world.node_tree.links.new(sky.outputs["Color"], bg.inputs["Color"])
    sun = bpy.data.lights.new("sol", "SUN")
    sun.energy = float(sys.argv[2]) if len(sys.argv) > 2 else 4.5
    sun.angle = math.radians(1.2)
    sun.color = (1.0, 0.94, 0.86)
    so = bpy.data.objects.new("sol", sun)
    sc.collection.objects.link(so)
    az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    so.rotation_euler = to_sun.to_track_quat("Z", "Y").to_euler()

    world.mist_settings.start = 0.0
    world.mist_settings.depth = MIST_DEPTH
    world.mist_settings.falloff = "LINEAR"
    sc.view_layers[0].use_pass_mist = True
    haze_range = setup_compositor()

    print("câmera e animações…", flush=True)
    cam = bpy.data.cameras.new("drone")
    co = bpy.data.objects.new("drone", cam)
    sc.collection.objects.link(co)
    sc.camera = co
    cam.sensor_fit = "VERTICAL"
    cam.sensor_height = 24.0
    co.rotation_mode = "QUATERNION"
    C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    prev_q = None
    store_xy = Vector((store[0], -store[1]))
    for fr in FRAMES:
        f = fr["f"] + 1
        M = C @ Matrix([fr["cam"]["matrixWorld"][i::4] for i in range(4)])
        loc, q, _ = M.decompose()
        if prev_q is not None and prev_q.dot(q) < 0:
            q = -q
        prev_q = q
        co.location = loc
        co.rotation_quaternion = q
        co.keyframe_insert("location", frame=f)
        co.keyframe_insert("rotation_quaternion", frame=f)
        cam.lens = 12.0 / math.tan(math.radians(fr["cam"]["fov"]) / 2)
        cam.clip_start = fr["cam"]["near"]
        cam.clip_end = fr["cam"]["far"]
        for prop in ("lens", "clip_start", "clip_end"):
            cam.keyframe_insert(prop, frame=f)
        haze_range.inputs["From Min"].default_value = fr["cam"]["dist"] * 0.5 / MIST_DEPTH
        haze_range.inputs["From Max"].default_value = fr["cam"]["dist"] * 5.5 / MIST_DEPTH
        haze_range.inputs["From Min"].keyframe_insert("default_value", frame=f)
        haze_range.inputs["From Max"].keyframe_insert("default_value", frame=f)
        # rota: progresso e largura
        for v in rvals["prog"]:
            v.outputs[0].default_value = fr["routeProgress"]
            v.outputs[0].keyframe_insert("default_value", frame=f)
        for name, mult in (("rota", 1.0), ("rota_brilho", 2.8)):
            width = ribbons[name][1].outputs[0]
            width.default_value = fr["ribbonHalfWidth"] * mult
            width.keyframe_insert("default_value", frame=f)
        # brilho da ponta
        hg = fr["headGlow"]
        head.location = (hg["x"], -hg["z"], 1.0)
        head.scale = (hg["size"], hg["size"], 1)
        head.keyframe_insert("location", frame=f)
        head.keyframe_insert("scale", frame=f)
        hvals["opacity"].outputs[0].default_value = hg["opacity"]
        hvals["opacity"].outputs[0].keyframe_insert("default_value", frame=f)
        for vals, key in ((svals, "storeRing"), (pvals, "startRing")):
            vals["opacity"].outputs[0].default_value = fr[key]["opacity"]
            vals["opacity"].outputs[0].keyframe_insert("default_value", frame=f)
            vals["phase"].outputs[0].default_value = fr[key]["phase"]
            vals["phase"].outputs[0].keyframe_insert("default_value", frame=f)
        # pin: de frente para a câmera
        d = Vector((loc.x, loc.y)) - store_xy
        pin.location = (store_xy.x, store_xy.y, fr["pin"]["y"])
        pin.rotation_euler = (0, 0, math.atan2(d.x, -d.y))
        s = max(fr["pin"]["scale"], 1e-4)
        pin.scale = (s, s, s)
        pin.hide_render = fr["pin"]["scale"] < 0.01
        for prop in ("location", "rotation_euler", "scale", "hide_render"):
            pin.keyframe_insert(prop, frame=f)
    # interpolação linear entre os frames (o desfoque de movimento amostra entre eles)
    for ad in [o.animation_data for o in bpy.data.objects if o.animation_data] + [cam.animation_data, world.animation_data] + \
              [m.node_tree.animation_data for m in bpy.data.materials if m.node_tree and m.node_tree.animation_data] + \
              [g.animation_data for g in bpy.data.node_groups if g.animation_data]:
        if ad and ad.action:
            for fc in action_fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"

    print("render…", flush=True)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = RES
    r.resolution_percentage = 100
    r.fps = 30
    sc.frame_start = 1
    sc.frame_end = len(FRAMES)
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = 5
    cy.adaptive_threshold = 0.05
    cy.use_denoising = True
    cy.denoising_prefilter = "FAST"
    cy.denoising_quality = "BALANCED"
    cy.use_fast_gi = True
    cy.max_bounces = 4
    cy.diffuse_bounces = 1
    cy.glossy_bounces = 1
    cy.transmission_bounces = 2
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    r.use_persistent_data = True
    r.use_motion_blur = False      # o desfoque de movimento custava ~20% a mais por frame
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception as e:
        print("color management:", e)
    sc.view_settings.exposure = 0.0
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_overwrite = False
    r.use_placeholder = True
    r.filepath = str(ROOT / "out/cycles/frame_")
    bpy.ops.wm.save_as_mainfile(filepath=str(CACHE / "cidade.blend"), compress=True)
    print("salvo em", CACHE / "cidade.blend")


def action_fcurves(action):
    """F-curves de uma action (Blender 5 usa camadas/slots; versões antigas, action.fcurves)."""
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def setup_compositor():
    """Névoa atmosférica pela passagem Mist + brilho (fog glow) só nos pontos bem fortes (rota, pin)."""
    tree = bpy.data.node_groups.new("composicao", "CompositorNodeTree")
    sc.compositing_node_group = tree
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    n = tree.nodes
    rl = n.new("CompositorNodeRLayers")
    mix = n.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    socks = {s.identifier: s for s in mix.inputs}
    rng = n.new("ShaderNodeMapRange")
    rng.clamp = True
    tree.links.new(rl.outputs["Mist"], rng.inputs["Value"])
    haze = n.new("ShaderNodeMath")
    haze.operation = "MULTIPLY"
    tree.links.new(rng.outputs["Result"], haze.inputs[0])
    haze.inputs[1].default_value = HAZE_AMOUNT
    tree.links.new(haze.outputs[0], socks["Factor_Float"])
    tree.links.new(rl.outputs["Image"], socks["A_Color"])
    socks["B_Color"].default_value = HAZE_COLOR
    glare = n.new("CompositorNodeGlare")
    gin = {s.name: s for s in glare.inputs}
    for name in ("Fog Glow", "FOG_GLOW"):
        try:
            gin["Type"].default_value = name
            break
        except Exception:
            pass
    gin["Threshold"].default_value = 2.5
    gin["Strength"].default_value = 0.6
    gin["Size"].default_value = 0.6
    res = {s.identifier: s for s in mix.outputs}["Result_Color"]
    tree.links.new(res, glare.inputs["Image"])
    go = n.new("NodeGroupOutput")
    tree.links.new(glare.outputs["Image"], go.inputs[0])
    return rng


if __name__ == "__main__":
    build()
