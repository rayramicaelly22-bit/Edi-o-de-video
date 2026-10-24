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
# Hospital São Paulo (nº 737): prédio do lado nordeste, de frente para a R. Caravelas (Google Maps, conferido pela
# dona da loja). O ponto do Overture places ficava ~300 m antes e do outro lado da avenida.
HOSPITAL_SAO_PAULO = (-47.348602, -2.980975)
LAGO_VERDE = (-47.346493, -2.998372)            # Overture places: "Lago Verde"

# Posição do nº 885 ao longo da avenida (metros desde a ponta sudeste do traçado do Overture). O cadastro de endereços
# do Pará (Overture addresses, fonte br/pa/statewide) tem dois pontos com o nº 885, a 1218 e 1227 m; a dona da loja
# confirmou o prédio num mapa de conferência. A numeração não é métrica a partir dessa ponta (o nº 737, do hospital,
# fica a ~1090 m).
STORE_NUMBER = 885
STORE_ALONG_M = 1226.5
# Lado da loja, pela dona: o mesmo da Arena do Município Verde e do Hospital São Paulo (nordeste, à direita de quem
# vem da Vinícius de Moraes); a Júnior Bike fica em frente, no lado do posto da esquina. Positivo = sudoeste.
STORE_SIDE_OFFSET_M = -14.0
VILA_PET_ALONG_M = 1240.0   # prédio vizinho no sentido da R. Joaquim Aguiar (noroeste), confirmado pela dona
ARENA_NAME = "Arena do Município Verde"   # nome no Overture (land_use); no vídeo, "Arena Verde"

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
