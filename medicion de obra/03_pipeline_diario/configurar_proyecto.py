# =============================================================================
# CONFIGURADOR DE PROYECTO
# =============================================================================
# Corre este script UNA VEZ al inicio del proyecto.
# Genera proyecto_config.json y verifica que baseline/ esté completo.
# =============================================================================

import os
import json

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "proyecto_config.json")
BASELINE    = os.path.join(BASE_DIR, "baseline")


def preguntar(prompt, default=None):
    sufijo = f" [{default}]" if default else ""
    resp = input(f"{prompt}{sufijo}: ").strip()
    return resp if resp else default


EPSG_LISTA = [
    (9377,  "MAGNA-SIRGAS / Origen-Nacional (recomendado Colombia)"),
    (3116,  "MAGNA-SIRGAS / Colombia Bogota zone"),
    (3117,  "MAGNA-SIRGAS / Colombia East zone"),
    (3114,  "MAGNA-SIRGAS / Colombia Far West zone"),
    (3115,  "MAGNA-SIRGAS / Colombia West zone"),
    (3118,  "MAGNA-SIRGAS / Colombia East of East zone"),
    (4686,  "MAGNA-SIRGAS — Geográfico"),
    (4326,  "WGS 84 — Geográfico (lat/lon)"),
    (32617, "WGS 84 / UTM zona 17N"),
    (32618, "WGS 84 / UTM zona 18N"),
    (32619, "WGS 84 / UTM zona 19N"),
]

def seleccionar_epsg():
    print("\n  Sistemas de proyección disponibles:")
    print(f"  {'#':<4} {'EPSG':<8} Descripción")
    print("  " + "-" * 55)
    for i, (epsg, desc) in enumerate(EPSG_LISTA):
        print(f"  {i:<4} {epsg:<8} {desc}")
    print("\n  O escribe directamente el código EPSG (ej: 32618)")

    while True:
        entrada = input("  Selección [0 = MAGNA Origen-Nacional]: ").strip() or "0"
        try:
            num = int(entrada)
            if 0 <= num < len(EPSG_LISTA):
                epsg, desc = EPSG_LISTA[num]
                print(f"  ✓  EPSG:{epsg} — {desc}")
                return epsg
            if num > 100:  # código EPSG directo
                try:
                    from pyproj import CRS
                    crs = CRS.from_epsg(num)
                    print(f"  ✓  EPSG:{num} — {crs.name}")
                    return num
                except Exception:
                    print(f"  ✗  EPSG:{num} no reconocido.")
        except ValueError:
            print("  Escribe el número de la lista o el código EPSG directamente.")


def main():
    print("=" * 60)
    print(" CONFIGURADOR DE PROYECTO — Medición Volumétrica")
    print("=" * 60)

    nombre_proyecto = preguntar("Nombre del proyecto", "Proyecto Vial")
    tramo           = preguntar("Descripción del tramo", "Tramo K0+000 – K0+300")
    contrato        = preguntar("N° de contrato (opcional)", "")
    prog_inicio     = float(preguntar("Progresiva inicial (m, ej. 5300 para K5+300)", "0"))
    espaciado       = float(preguntar("Espaciado entre secciones (m)", "20"))
    ancho_corredor  = float(preguntar("Ancho del corredor desde el eje (m)", "28"))
    fact_esponj     = float(preguntar("Factor de esponjamiento", "1.25"))
    fact_contrac    = float(preguntar("Factor de contracción", "0.90"))

    print("\n--- Sistema de proyección del proyecto ---")
    epsg = seleccionar_epsg()

    paso_landxml   = int(preguntar("Paso de malla LandXML (2=0.5m, 4=1m, 8=2m)", "4"))
    vol_corte_obj  = float(preguntar("Volumen de corte objetivo (m³)", "15000"))
    vol_rell_obj   = float(preguntar("Volumen de relleno objetivo (m³)", "25000"))

    config = {
        "_instrucciones": "Edita los valores con los datos reales del proyecto. Rutas relativas a medicion de obra/.",
        "nombre":                  nombre_proyecto,
        "tramo":                   tramo,
        "contrato":                contrato,
        "dem_baseline":            "baseline/dem_baseline.tif",
        "eje_via":                 "baseline/eje_via.dxf",
        "prog_inicio_m":           prog_inicio,
        "espaciado_secciones":     espaciado,
        "ancho_corredor":          ancho_corredor,
        "factor_esponjamiento":    fact_esponj,
        "factor_contraccion":      fact_contrac,
        "epsg_proyecto":           epsg,
        "paso_muestreo_landxml":   paso_landxml,
        "vol_corte_objetivo":      vol_corte_obj,
        "vol_relleno_objetivo":    vol_rell_obj,
        "dz_min_plot":             -3.0,
        "dz_max_plot":              3.0,
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Configuración guardada en: {CONFIG_FILE}")
    print(json.dumps(config, indent=2, ensure_ascii=False))

    # Verificar baseline
    print("\n--- Verificando carpeta baseline/ ---")
    baseline_dem = os.path.join(BASELINE, "dem_baseline.tif")
    # Aceptar DWG, DXF o GeoJSON como eje
    eje_encontrado = None
    for ext in ("eje_via.dwg", "eje_via.dxf", "eje_via.geojson"):
        candidato = os.path.join(BASELINE, ext)
        if os.path.exists(candidato):
            eje_encontrado = candidato
            break

    ok = True
    if os.path.exists(baseline_dem):
        print(f"  ✓  dem_baseline.tif")
    else:
        print(f"  ✗  dem_baseline.tif  ← FALTA")
        ok = False

    if eje_encontrado:
        print(f"  ✓  {os.path.basename(eje_encontrado)}")
    else:
        print(f"  ✗  eje_via.dwg / .dxf / .geojson  ← FALTA")
        ok = False

    if not ok:
        print(f"""
PASOS PENDIENTES:
  1. Copia el DSM de tu vuelo de referencia (antes de obra) como:
         baseline/dem_baseline.tif

  2. Copia el eje de la vía a baseline/ en cualquiera de estos formatos:
         baseline/eje_via.dwg       ← desde AutoCAD / Civil 3D (recomendado)
         baseline/eje_via.dxf       ← si ya tienes el DXF
         baseline/eje_via.geojson   ← si lo exportaste desde QGIS

     El sistema de proyección configurado es EPSG:{epsg}
     Asegúrate de que el DWG/DXF esté en ese mismo sistema.

     Para convertir manualmente a DXF desde Civil 3D:
       Línea de comandos → SAVEAS → "AutoCAD 2018 DXF"

  3. Luego puedes correr el pipeline:
         python pipeline.py --fecha YYYY-MM-DD
""")
    else:
        print(f"\n✓ Baseline completo. Proyecto listo (EPSG:{epsg}).")
        print("  Flujo de trabajo diario:")
        print("    1. Vuela con el dron y procesa con OpenDroneMap")
        print("    2. Copia dsm.tif a:  vuelos/YYYY-MM-DD/dsm.tif")
        print("    3. Corre:            python pipeline.py --fecha YYYY-MM-DD")
        print("\n  Para convertir el eje DWG a GeoJSON:")
        print("    python ../02_dron_odm/convertir_eje_dwg.py baseline/eje_via.dwg")
        print(f"    (usa --epsg {epsg} para asignar la proyección automáticamente)")


if __name__ == "__main__":
    main()
