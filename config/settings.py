"""Configuración global del proyecto Mensure v2.0."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT_DIR / "reports"
HISTORY_FILE = PROCESSED_DIR / "historico_acumulado.xlsx"

# Tipos de maquinaria disponibles
MACHINERY_TYPES = [
    "Excavadora",
    "Bulldozer / Tractor de oruga",
    "Motoniveladora",
    "Volqueta",
    "Vibrocompactador",
]

# CRS sugeridos (Colombia / proyectos viales)
COMMON_CRS = {
    "MAGNA-SIRGAS / Origen Bogotá (EPSG:3116)": 3116,
    "WGS84 / UTM zona 18N (EPSG:32618)": 32618,
    "WGS84 / UTM zona 17N (EPSG:32617)": 32617,
    "WGS84 / UTM zona 19N (EPSG:32619)": 32619,
    "WGS84 geográfico (EPSG:4326)": 4326,
}

# Capas estructurales de pavimento (espesor teórico en metros)
PAVEMENT_LAYERS_DEFAULT = {
    "Subrasante mejorada": 0.30,
    "Subbase granular": 0.25,
    "Base granular": 0.20,
    "Mezcla asfáltica": 0.10,
}
