"""
Configuración inicial del proyecto — ejecutar UNA sola vez
==========================================================
Crea la estructura de carpetas y el archivo de configuración.
Después de correr este script, edita proyecto_config.json
con los datos reales del proyecto.

Uso:
    python configurar_proyecto.py
"""

import json
from pathlib import Path

BASE = Path(__file__).parent

# ── Crear estructura de carpetas ──────────────────────────────────────────
carpetas = [
    BASE / "baseline",
    BASE / "vuelos",
    BASE / "reportes" / "diarios",
    BASE / "reportes" / "semanales",
    BASE / "reportes" / "mensuales",
]
for c in carpetas:
    c.mkdir(parents=True, exist_ok=True)

# ── Escribir config si no existe ─────────────────────────────────────────
config_path = BASE / "proyecto_config.json"
if config_path.exists():
    print(f"[OK] proyecto_config.json ya existe. No se sobreescribe.")
else:
    config = {
        "_instrucciones": "Edita los valores de este archivo con los datos reales del proyecto.",
        "nombre":                "Nombre del proyecto",
        "tramo":                 "Tramo en estudio",
        "contrato":              "",
        "dem_baseline":          "baseline/dem_baseline.tif",
        "eje_via":               "baseline/eje_via.dxf",
        "prog_inicio_m":         5300,
        "espaciado_secciones":   20,
        "ancho_corredor":        28,
        "factor_esponjamiento":  1.25,
        "factor_contraccion":    0.90,
        "paso_muestreo_landxml": 4,
        "vol_corte_objetivo":    15000,
        "vol_relleno_objetivo":  25000,
        "dz_min_plot":           -3.0,
        "dz_max_plot":            3.0
    }
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] proyecto_config.json creado — edítalo con los datos del proyecto.")

print("\nEstructura creada:")
for c in sorted(BASE.rglob("*")):
    if c.is_dir():
        nivel = len(c.relative_to(BASE).parts)
        print(f"  {'  ' * nivel}{c.name}/")

print(f"""
Próximos pasos:
  1. Edita proyecto_config.json con los datos del proyecto.
  2. Copia dem_baseline.tif y eje_via.geojson a la carpeta baseline/.
  3. Después de cada vuelo, copia el dsm.tif de ODM a vuelos/YYYY-MM-DD/dsm.tif
  4. Corre: python pipeline.py
""")
