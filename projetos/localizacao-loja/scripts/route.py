"""Calcula a rota de carro da Praça Célio Miranda até a loja (Av. Barão de Araruna, 885) no grafo viário do Overture.

- Respeita mão única (access_restrictions "denied" no sentido "backward").
- Prefere vias principais, como um GPS: o peso de cada trecho é o comprimento vezes um fator por classe.
- A loja vira um nó no meio do trecho da avenida que contém o ponto a STORE_ALONG_M do início dela.

Saída: .cache/route.geojson (LineString lon/lat + passos com nome da via e comprimento).
"""
import json
import math

import networkx as nx
import numpy as np
import pyarrow.parquet as pq
import shapely
from shapely import from_wkb, ops

from config import CACHE, CRS_UTM, PRACA_CELIO_MIRANDA, STORE_ALONG_M, to_ll, to_utm

FACTOR = {"trunk": 0.7, "primary": 0.7, "secondary": 0.8, "tertiary": 0.85, "unclassified": 1.0,
          "residential": 1.15, "living_street": 1.4, "service": 2.0, "unknown": 1.5}


def utm(g):
    return shapely.transform(g, lambda c: np.column_stack(to_utm(c[:, 0], c[:, 1])))


def lonlat(g):
    return shapely.transform(g, lambda c: np.column_stack(to_ll(c[:, 0], c[:, 1])))


def main():
    rows = pq.read_table(CACHE / "overture/segments.parquet").to_pylist()
    G = nx.DiGraph()
    geoms = {}
    for r in rows:
        if r["subtype"] != "road" or r["class"] not in FACTOR:
            continue
        oneway = any(a["access_type"] == "denied" and a["when"] and a["when"].get("heading") == "backward"
                     and not a.get("between") for a in (r["access_restrictions"] or []))
        g = utm(from_wkb(r["geometry"]))
        name = (r["names"] or {}).get("primary") or ""
        cons = sorted(r["connectors"] or [], key=lambda c: c["at"])
        for a, b in zip(cons, cons[1:]):
            sub = ops.substring(g, a["at"], b["at"], normalized=True)
            if sub.length < 0.5:
                continue
            u, v = a["connector_id"], b["connector_id"]
            w = sub.length * FACTOR[r["class"]]
            pairs = [(u, v, sub)] + ([] if oneway else [(v, u, shapely.LineString(sub.coords[::-1]))])
            for x, y, gg in pairs:
                if not G.has_edge(x, y) or G[x][y]["w"] > w:
                    G.add_edge(x, y, w=w, len=gg.length, name=name)
                    geoms[(x, y)] = gg
                G.nodes[x]["p"] = gg.coords[0]
                G.nodes[y]["p"] = gg.coords[-1]

    # avenida Barão de Araruna, orientada do sudeste (números baixos) para o noroeste
    av = shapely.line_merge(shapely.MultiLineString(
        [list(utm(from_wkb(r["geometry"])).coords) for r in rows if "Araruna" in ((r["names"] or {}).get("primary") or "")]))
    if av.geom_type != "LineString":
        av = max(av.geoms, key=lambda a: a.length)
    if av.coords[0][1] > av.coords[-1][1]:
        av = shapely.LineString(list(av.coords)[::-1])
    store = av.interpolate(STORE_ALONG_M)

    (u, v), _ = min(((k, gg.distance(store)) for k, gg in geoms.items() if "Araruna" in G.edges[k]["name"]), key=lambda t: t[1])
    S = "LOJA"
    G.add_node(S, p=(store.x, store.y))
    for a, b in [(u, v), (v, u)]:
        if not G.has_edge(a, b):
            continue
        e = geoms[(a, b)]
        d = e.project(store)
        for x, y, gg in [(a, S, ops.substring(e, 0, d)), (S, b, ops.substring(e, d, e.length))]:
            G.add_edge(x, y, w=gg.length * 0.85, len=gg.length, name=G.edges[a, b]["name"])
            geoms[(x, y)] = gg

    px, py = to_utm(*PRACA_CELIO_MIRANDA)
    start = min((n for n in G.nodes if n != S and G.out_degree(n) > 0), key=lambda n: math.dist(G.nodes[n]["p"], (px, py)))
    path = nx.shortest_path(G, start, S, weight="w")
    coords = [geoms[(path[0], path[1])].coords[0]]
    steps = []
    for a, b in zip(path, path[1:]):
        coords += list(geoms[(a, b)].coords)[1:]
        n = G.edges[a, b]["name"] or "(sem nome)"
        if steps and steps[-1][0] == n:
            steps[-1][1] += G.edges[a, b]["len"]
        else:
            steps.append([n, G.edges[a, b]["len"]])
    route = shapely.LineString(coords)
    ll = lonlat(route)
    for n, length in steps:
        print(f"  {n:35} {length:6.0f} m")
    print(f"rota: {route.length:.0f} m ({CRS_UTM})")
    json.dump({"type": "Feature", "properties": {"length_m": route.length, "steps": steps},
               "geometry": {"type": "LineString", "coordinates": [[round(x, 7), round(y, 7)] for x, y in ll.coords]}},
              open(CACHE / "route.geojson", "w"))


if __name__ == "__main__":
    main()
