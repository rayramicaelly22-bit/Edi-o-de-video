"""Baixa do S3 público do Overture Maps o recorte de Paragominas (ruas, prédios, água, uso do solo, pontos).

Saída: .cache/overture/<tipo>.parquet. Usa pyarrow com filtro pelo bbox (só lê os row groups que cruzam o recorte).
Dados: © colaboradores do OpenStreetMap (ODbL), Overture Maps Foundation, Google Open Buildings, Meta/Foursquare (places).
"""
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import pyarrow.parquet as pq

from config import CACHE, CITY_BBOX, OVERTURE_RELEASE

WIDE_BBOX = (-47.60, -3.20, -47.10, -2.80)
LAYERS = [
    ("places", "place", "places", CITY_BBOX),
    ("transportation", "segment", "segments", CITY_BBOX),
    ("buildings", "building", "buildings", CITY_BBOX),
    ("base", "water", "water", WIDE_BBOX),
    ("base", "land_use", "land_use", CITY_BBOX),
]


def fetch(fs, theme, typ, bbox):
    xmin, ymin, xmax, ymax = bbox
    path = f"overturemaps-us-west-2/release/{OVERTURE_RELEASE}/theme={theme}/type={typ}/"
    dataset = ds.dataset(path, filesystem=fs, format="parquet")
    flt = ((pc.field("bbox", "xmin") < xmax) & (pc.field("bbox", "xmax") > xmin)
           & (pc.field("bbox", "ymin") < ymax) & (pc.field("bbox", "ymax") > ymin))
    batches = [b for b in dataset.to_batches(filter=flt, batch_size=50000) if b.num_rows]
    return pa.Table.from_batches(batches) if batches else dataset.schema.empty_table()


def main():
    # o proxy do ambiente é passado explicitamente: o SDK da AWS no pyarrow não lê HTTPS_PROXY
    import os
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    fs = pafs.S3FileSystem(anonymous=True, region="us-west-2", **({"proxy_options": proxy} if proxy else {}))
    out = CACHE / "overture"
    out.mkdir(parents=True, exist_ok=True)
    for theme, typ, name, bbox in LAYERS:
        t = time.time()
        table = fetch(fs, theme, typ, bbox)
        pq.write_table(table, out / f"{name}.parquet")
        print(f"{theme}/{typ}: {table.num_rows} linhas em {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
