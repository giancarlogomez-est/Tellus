# =============================================================================
# CONVERTIDOR DE EJE DE VÍA — AutoCAD DWG / DXF  →  GeoJSON
# =============================================================================
# Extrae la polilínea del eje desde un archivo .dwg o .dxf de AutoCAD y la
# exporta como GeoJSON con el sistema de proyección que el usuario defina.
#
# Uso:
#   python convertir_eje_dwg.py                      (modo interactivo)
#   python convertir_eje_dwg.py eje.dwg --epsg 32618 (modo directo)
#   python convertir_eje_dwg.py eje.dxf --epsg 4326 --salida eje.geojson
#
# Métodos de conversión DWG → DXF (en orden de prioridad):
#   1. accoreconsole.exe  — viene con AutoCAD / Civil 3D (recomendado)
#   2. ODA File Converter — gratuito, https://www.opendesign.com/guestfiles
#   3. Conversión manual  — instrucciones para exportar desde Civil 3D
# =============================================================================

import os
import sys
import json
import argparse
import subprocess
import tempfile
import glob

# ---------------------------------------------------------------------------
# Instalación automática de dependencias
# ---------------------------------------------------------------------------
def instalar_si_falta(paquete, importar_como=None):
    nombre = importar_como or paquete
    try:
        __import__(nombre)
    except ImportError:
        print(f"  Instalando {paquete}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", paquete, "-q"])

instalar_si_falta("ezdxf")
instalar_si_falta("pyproj")

import ezdxf
from pyproj import CRS, Transformer

# ---------------------------------------------------------------------------
# Rutas típicas de accoreconsole.exe y ODA File Converter en Windows
# ---------------------------------------------------------------------------
RUTAS_ACCORECONSOLE = [
    r"C:\Program Files\Autodesk\AutoCAD 2024\accoreconsole.exe",
    r"C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe",
    r"C:\Program Files\Autodesk\AutoCAD 2023\accoreconsole.exe",
    r"C:\Program Files\Autodesk\Civil 3D 2024\accoreconsole.exe",
    r"C:\Program Files\Autodesk\Civil 3D 2025\accoreconsole.exe",
    r"C:\Program Files\Autodesk\Civil 3D 2023\accoreconsole.exe",
]
RUTAS_ODA = [
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 25.9.0\ODAFileConverter.exe",
]

# ---------------------------------------------------------------------------
# Búsqueda de ejecutables
# ---------------------------------------------------------------------------
def encontrar_ejecutable(rutas_conocidas, nombre_busqueda):
    """Busca un ejecutable en rutas conocidas y luego en Program Files."""
    for ruta in rutas_conocidas:
        if os.path.exists(ruta):
            return ruta
    # Búsqueda dinámica
    for base in [r"C:\Program Files\Autodesk", r"C:\Program Files (x86)\Autodesk"]:
        if os.path.exists(base):
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.lower() == nombre_busqueda.lower():
                        return os.path.join(root, f)
    return None


# ---------------------------------------------------------------------------
# Método 1: conversión con accoreconsole.exe
# ---------------------------------------------------------------------------
SCRIPT_LISP_DWG2DXF = """(defun c:exportdxf ()
  (command "_.DXFOUT" (getvar "DWGNAME") "16" "")
  (quit)
)
(c:exportdxf)
"""

def convertir_con_accoreconsole(dwg_path, dxf_salida):
    acc = encontrar_ejecutable(RUTAS_ACCORECONSOLE, "accoreconsole.exe")
    if not acc:
        return False, "accoreconsole.exe no encontrado"

    # Crear script LISP temporal
    lisp_path = dwg_path.replace(".dwg", "_conv.scr").replace(".DWG", "_conv.scr")
    dxf_esperado = dwg_path.replace(".dwg", ".dxf").replace(".DWG", ".dxf")

    with open(lisp_path, "w") as f:
        f.write(f'DXFOUT\n"{dxf_esperado}"\n16\n\nQUIT\n')

    try:
        result = subprocess.run(
            [acc, "/i", dwg_path, "/s", lisp_path],
            capture_output=True, text=True, timeout=60
        )
        if os.path.exists(dxf_esperado):
            import shutil
            shutil.copy(dxf_esperado, dxf_salida)
            return True, f"Convertido con accoreconsole → {dxf_salida}"
        return False, f"accoreconsole no generó el DXF. stderr: {result.stderr[:200]}"
    except Exception as e:
        return False, str(e)
    finally:
        if os.path.exists(lisp_path):
            os.remove(lisp_path)


# ---------------------------------------------------------------------------
# Método 2: ODA File Converter
# ---------------------------------------------------------------------------
def convertir_con_oda(dwg_path, dxf_salida):
    oda = encontrar_ejecutable(RUTAS_ODA, "ODAFileConverter.exe")
    if not oda:
        return False, ("ODA File Converter no encontrado. "
                       "Descárgalo gratis en: https://www.opendesign.com/guestfiles")

    dir_entrada = os.path.dirname(dwg_path)
    dir_salida  = os.path.dirname(dxf_salida)
    nombre_base = os.path.splitext(os.path.basename(dwg_path))[0]

    try:
        result = subprocess.run(
            [oda, dir_entrada, dir_salida, "ACAD2018", "DXF", "0", "1",
             f"*.{os.path.splitext(dwg_path)[1].lstrip('.')}"],
            capture_output=True, text=True, timeout=120
        )
        dxf_gen = os.path.join(dir_salida, nombre_base + ".dxf")
        if os.path.exists(dxf_gen):
            return True, f"Convertido con ODA File Converter → {dxf_gen}"
        return False, f"ODA no generó el DXF. stderr: {result.stderr[:200]}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Método 3: instrucciones manuales
# ---------------------------------------------------------------------------
def instrucciones_manuales(dwg_path):
    print("""
╔══════════════════════════════════════════════════════════╗
║  CONVERSIÓN MANUAL  DWG → DXF  desde Civil 3D            ║
╠══════════════════════════════════════════════════════════╣
║  1. Abre el archivo en Civil 3D                          ║
║  2. Escribe en la línea de comandos:  SAVEAS             ║
║  3. En "Tipo de archivo" selecciona:  AutoCAD 2018 DXF   ║
║  4. Guarda con el mismo nombre       (eje_via.dxf)       ║
║  5. Vuelve a correr este script con el .dxf              ║
╚══════════════════════════════════════════════════════════╝
""")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Conversión DWG → DXF (orquestador)
# ---------------------------------------------------------------------------
def dwg_a_dxf(dwg_path):
    """Intenta convertir DWG a DXF usando los métodos disponibles."""
    dxf_path = os.path.splitext(dwg_path)[0] + ".dxf"

    print(f"\n[1/4] Convirtiendo DWG → DXF...")
    ok, msg = convertir_con_accoreconsole(dwg_path, dxf_path)
    if ok:
        print(f"  ✓  {msg}")
        return dxf_path

    print(f"  ✗  accoreconsole: {msg}")
    ok, msg = convertir_con_oda(dwg_path, dxf_path)
    if ok:
        print(f"  ✓  {msg}")
        return dxf_path

    print(f"  ✗  ODA Converter: {msg}")
    instrucciones_manuales(dwg_path)


# ---------------------------------------------------------------------------
# Extracción de polilíneas desde DXF
# ---------------------------------------------------------------------------
def listar_polilineas(dxf_path):
    """Devuelve lista de (índice, capa, tipo, num_vértices) de todas las polilíneas."""
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    polilineas = []
    idx = 0
    for entity in msp:
        if entity.dxftype() in ("LWPOLYLINE", "POLYLINE", "SPLINE"):
            capa = entity.dxf.layer
            tipo = entity.dxftype()
            if entity.dxftype() == "LWPOLYLINE":
                n_pts = len(entity)
            elif entity.dxftype() == "POLYLINE":
                n_pts = sum(1 for v in entity.vertices)
            else:
                n_pts = len(entity.control_points)
            polilineas.append((idx, capa, tipo, n_pts, entity))
            idx += 1
    return polilineas


def extraer_coordenadas(entity):
    """Extrae lista de (x, y) de una entidad polilínea."""
    tipo = entity.dxftype()
    if tipo == "LWPOLYLINE":
        return [(pt[0], pt[1]) for pt in entity.get_points()]
    elif tipo == "POLYLINE":
        return [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
    elif tipo == "SPLINE":
        # Interpolar la spline en puntos
        pts = list(entity.flattening(0.01))
        return [(p.x, p.y) for p in pts]
    return []


def seleccionar_polilinea(polilineas, modo_auto=False):
    """Permite al usuario seleccionar qué polilínea usar como eje."""
    if not polilineas:
        print("ERROR: No se encontraron polilíneas en el archivo DXF.")
        sys.exit(1)

    if len(polilineas) == 1 or modo_auto:
        sel = polilineas[0]
        print(f"  Polilínea seleccionada: capa='{sel[1]}', tipo={sel[2]}, vértices={sel[3]}")
        return sel[4]

    print(f"\nSe encontraron {len(polilineas)} polilíneas en el archivo:")
    print(f"  {'#':<4} {'Capa':<25} {'Tipo':<14} {'Vértices':>8}")
    print("  " + "-" * 55)
    for idx, capa, tipo, n_pts, _ in polilineas:
        print(f"  {idx:<4} {capa:<25} {tipo:<14} {n_pts:>8}")

    while True:
        try:
            sel_idx = int(input(f"\nSelecciona el número del eje de la vía [0]: ") or "0")
            if 0 <= sel_idx < len(polilineas):
                return polilineas[sel_idx][4]
            print(f"  Ingresa un número entre 0 y {len(polilineas)-1}")
        except ValueError:
            print("  Ingresa un número válido.")


# ---------------------------------------------------------------------------
# Selección de EPSG
# ---------------------------------------------------------------------------
EPSG_COLOMBIA = [
    (4326,  "WGS 84 — Geográfico (lat/lon)"),
    (4686,  "MAGNA-SIRGAS — Geográfico"),
    (3116,  "MAGNA-SIRGAS / Colombia Bogota zone"),
    (3117,  "MAGNA-SIRGAS / Colombia East zone"),
    (3114,  "MAGNA-SIRGAS / Colombia Far West zone"),
    (3115,  "MAGNA-SIRGAS / Colombia West zone"),
    (3118,  "MAGNA-SIRGAS / Colombia East of East zone"),
    (9377,  "MAGNA-SIRGAS / Origen-Nacional (recomendado Colombia)"),
    (32617, "WGS 84 / UTM zona 17N"),
    (32618, "WGS 84 / UTM zona 18N"),
    (32619, "WGS 84 / UTM zona 19N"),
    (21817, "Bogota / UTM zona 17N"),
    (21818, "Bogota / UTM zona 18N"),
]

def seleccionar_epsg(titulo="Selecciona el sistema de proyección"):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")
    print(f"  {'#':<5} {'EPSG':<8} Descripción")
    print("  " + "-" * 55)
    for i, (epsg, desc) in enumerate(EPSG_COLOMBIA):
        print(f"  {i:<5} {epsg:<8} {desc}")
    print(f"\n  O escribe directamente el código EPSG (ej: 32618)")

    while True:
        entrada = input("\n  Selección [8 = MAGNA Origen-Nacional]: ").strip() or "8"
        try:
            num = int(entrada)
            # Si es un índice de la lista
            if 0 <= num < len(EPSG_COLOMBIA):
                epsg, desc = EPSG_COLOMBIA[num]
                print(f"  ✓  EPSG:{epsg} — {desc}")
                return epsg
            # Si es un código EPSG directo
            if num > 100:
                try:
                    crs = CRS.from_epsg(num)
                    print(f"  ✓  EPSG:{num} — {crs.name}")
                    return num
                except Exception:
                    print(f"  ✗  EPSG:{num} no reconocido. Intenta otro código.")
        except ValueError:
            # Búsqueda por texto
            resultados = [(e, d) for e, d in EPSG_COLOMBIA if entrada.lower() in d.lower()]
            if resultados:
                print(f"  Resultados para '{entrada}':")
                for e, d in resultados:
                    print(f"    EPSG:{e} — {d}")
            else:
                print(f"  No se encontró '{entrada}'. Escribe el código EPSG directamente.")


# ---------------------------------------------------------------------------
# Reproyección y exportación GeoJSON
# ---------------------------------------------------------------------------
def reproyectar_coordenadas(coords, epsg_entrada, epsg_salida=4326):
    """Reproyecta lista de (x, y) de epsg_entrada a epsg_salida."""
    if epsg_entrada == epsg_salida:
        return coords
    try:
        transformer = Transformer.from_crs(
            CRS.from_epsg(epsg_entrada),
            CRS.from_epsg(epsg_salida),
            always_xy=True
        )
        return [transformer.transform(x, y) for x, y in coords]
    except Exception as e:
        print(f"  ADVERTENCIA: No se pudo reproyectar ({e}). Se usarán coords originales.")
        return coords


def exportar_geojson(coords, epsg_proyecto, ruta_salida):
    """Exporta las coordenadas como GeoJSON LineString."""
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[round(x, 6), round(y, 6)] for x, y in coords]
            },
            "properties": {
                "nombre": "Eje de vía",
                "epsg_original": epsg_proyecto,
                "vertices": len(coords),
            }
        }],
        "crs": {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:EPSG::{epsg_proyecto}"}
        }
    }
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓  GeoJSON guardado: {ruta_salida}")
    print(f"     Vértices exportados : {len(coords)}")
    print(f"     Sistema de proyección: EPSG:{epsg_proyecto}")
    crs = CRS.from_epsg(epsg_proyecto)
    print(f"     Nombre CRS           : {crs.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Convierte el eje de vía de AutoCAD (.dwg/.dxf) a GeoJSON"
    )
    parser.add_argument("archivo", nargs="?", help="Ruta al archivo .dwg o .dxf")
    parser.add_argument("--epsg", type=int, help="Código EPSG del sistema de proyección del DWG")
    parser.add_argument("--salida", type=str, help="Ruta del GeoJSON de salida")
    parser.add_argument("--auto", action="store_true",
                        help="Selecciona automáticamente la primera polilínea encontrada")
    args = parser.parse_args()

    print("=" * 60)
    print("  Convertidor de eje DWG/DXF → GeoJSON")
    print("=" * 60)

    # 1. Archivo de entrada
    archivo = args.archivo
    if not archivo:
        archivo = input("\n  Ruta al archivo .dwg o .dxf: ").strip().strip('"')
    if not os.path.exists(archivo):
        print(f"ERROR: Archivo no encontrado: {archivo}")
        sys.exit(1)

    # 2. Convertir DWG → DXF si es necesario
    ext = os.path.splitext(archivo)[1].lower()
    if ext == ".dwg":
        dxf_path = dwg_a_dxf(archivo)
    elif ext == ".dxf":
        dxf_path = archivo
        print(f"  Archivo DXF detectado, omitiendo conversión.")
    else:
        print(f"ERROR: Formato no soportado: {ext}. Usa .dwg o .dxf")
        sys.exit(1)

    # 3. Selección de EPSG
    epsg_dwg = args.epsg
    if not epsg_dwg:
        epsg_dwg = seleccionar_epsg("¿En qué sistema de proyección está el DWG?")

    # 4. Leer polilíneas del DXF
    print(f"\n[2/4] Leyendo polilíneas del DXF...")
    try:
        polilineas = listar_polilineas(dxf_path)
        print(f"  Polilíneas encontradas: {len(polilineas)}")
    except Exception as e:
        print(f"ERROR al leer DXF: {e}")
        sys.exit(1)

    # 5. Seleccionar polilínea del eje
    print(f"\n[3/4] Selección del eje...")
    entidad = seleccionar_polilinea(polilineas, modo_auto=args.auto)
    coords  = extraer_coordenadas(entidad)

    if not coords:
        print("ERROR: No se pudieron extraer coordenadas de la polilínea.")
        sys.exit(1)
    print(f"  Vértices extraídos: {len(coords)}")
    print(f"  Primer punto: ({coords[0][0]:.3f}, {coords[0][1]:.3f})")
    print(f"  Último punto: ({coords[-1][0]:.3f}, {coords[-1][1]:.3f})")

    # 6. Exportar GeoJSON
    print(f"\n[4/4] Exportando GeoJSON...")
    salida = args.salida
    if not salida:
        base = os.path.splitext(archivo)[0]
        salida = base + "_eje.geojson"

    exportar_geojson(coords, epsg_dwg, salida)

    print(f"""
╔══════════════════════════════════════════════════════════╗
║  SIGUIENTE PASO                                          ║
║                                                          ║
║  Copia el archivo generado a:                            ║
║    baseline/eje_via.geojson                              ║
║                                                          ║
║  Asegúrate de que el EPSG en proyecto_config.json        ║
║  coincide con EPSG:{epsg_dwg:<6}                              ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
