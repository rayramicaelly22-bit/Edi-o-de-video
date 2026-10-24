"""Configuração compartilhada pelos scripts de preparação da cena."""
from pathlib import Path

from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"          # downloads brutos (Overture, Sentinel-2) — não versionado
PUBLIC = ROOT / "public" / "scene"  # assets usados pela Remotion

# Release do Overture Maps usado (S3 público: s3://overturemaps-us-west-2)
OVERTURE_RELEASE = "2026-10-21.0"

# Recorte de Paragominas (lon/lat) para ruas, prédios e pontos comerciais
CITY_BBOX = (-47.45, -3.08, -47.28, -2.92)

# Sistema métrico: WGS 84 / UTM 23S (o mesmo das cenas Sentinel-2 do tile 23MKS)
CRS_UTM = "EPSG:32723"
to_utm = Transformer.from_crs("EPSG:4326", CRS_UTM, always_xy=True).transform
to_ll = Transformer.from_crs(CRS_UTM, "EPSG:4326", always_xy=True).transform

# Origem da cena 3D: centro da rota (praça -> loja). Eixo x = leste, z = -norte, y = altura.
ORIGIN_LL = (-47.3503, -2.9888)
ORIGIN_E, ORIGIN_N = to_utm(*ORIGIN_LL)

# Pontos de interesse (lon, lat)
PRACA_CELIO_MIRANDA = (-47.354900, -2.995580)   # Overture places: "Praça Celio Miranda"
HOSPITAL_SAO_PAULO = (-47.347148, -2.983429)    # Overture places: "Hospital São Paulo", nº 737
LAGO_VERDE = (-47.346493, -2.998372)            # Overture places: "Lago Verde"

# A Av. Barão de Araruna tem numeração métrica (nº ≈ metros desde o início, a sudeste),
# com ímpares no lado sudoeste. O nº 885 fica a ~925 m do início da avenida.
STORE_NUMBER = 885
STORE_ALONG_M = 925.0
STORE_SIDE_OFFSET_M = 14.0  # recuo da pin para o lado sudoeste (lado dos ímpares)

# Cenas Sentinel-2 L2A (Earth Search / Element 84) sem nuvem sobre a cidade, em ordem de prioridade
S2_BASE = "https://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/sentinel-2-c1-l2a/23/M/KS"
S2_SCENES = [
    "2026/8/S2C_T23MKS_20260819T133142_L2A",
    "2026/10/S2B_T23MKS_20261003T133253_L2A",
    "2026/8/S2A_T23MKS_20260831T133237_L2A",
    "2026/9/S2C_T23MKS_20260918T133145_L2A",
]


def local_xz(e, n):
    """UTM -> coordenadas locais da cena (x = leste, z = -norte), em metros."""
    return e - ORIGIN_E, -(n - ORIGIN_N)
