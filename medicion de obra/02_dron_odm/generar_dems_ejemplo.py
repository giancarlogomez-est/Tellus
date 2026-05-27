# =============================================================================
# GENERADOR DE DEMs SINTÉTICOS — para probar calculo_volumen_odm.py
# =============================================================================
# Genera: dem_pre.tif, dem_post.tif, eje_via.geojson
# Requiere: rasterio, numpy, shapely
# =============================================================================

import numpy as np
import os
import json

try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
except ImportError:
    print("Instala rasterio: pip install rasterio")
    raise

SEMILLA      = 42
RESOLUCION   = 0.25     # metros por píxel (similar a ODM con dron a 60 m)
ANCHO_ZONA   = 60.0     # metros
LARGO_ZONA   = 300.0    # metros (K5+300 → K5+600)
COTA_BASE    = 1450.0   # metros s.n.m.
EPSG         = 32618    # UTM zona 18N (ajusta a tu zona)

np.random.seed(SEMILLA)

def generar_dem(n_cols, n_rows, cota_base, variacion, ruido, corte_zona=None, relleno_zona=None):
    """
    Genera un DEM sintético como array numpy.
    corte_zona / relleno_zona : tuplas (fila_ini, fila_fin, col_ini, col_fin, delta_z)
    """
    dem = np.full((n_rows, n_cols), cota_base, dtype=np.float32)
    # Pendiente longitudinal
    for r in range(n_rows):
        dem[r, :] += r / n_rows * variacion
    # Ondulaciones transversales
    for c in range(n_cols):
        dem[:, c] += 0.5 * np.sin(c / n_cols * 4 * np.pi)
    # Ruido aleatorio
    dem += np.random.normal(0, ruido, dem.shape).astype(np.float32)
    # Zonas de corte y relleno artificiales
    if corte_zona:
        ri, rf, ci, cf, dz = corte_zona
        dem[ri:rf, ci:cf] += dz
    if relleno_zona:
        ri, rf, ci, cf, dz = relleno_zona
        dem[ri:rf, ci:cf] += dz
    return dem


def guardar_tif(dem, ruta, transform, epsg):
    perfil = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": dem.shape[1],
        "height": dem.shape[0],
        "count": 1,
        "crs": CRS.from_epsg(epsg),
        "transform": transform,
        "nodata": -9999.0,
    }
    with rasterio.open(ruta, "w", **perfil) as dst:
        dst.write(dem, 1)
    print(f"  Guardado: {ruta}  ({dem.shape[1]}×{dem.shape[0]} px)")


def generar_eje(ruta, x_ini, y_ini, largo, angulo_deg=5.0):
    """Genera un GeoJSON con el eje de la vía (línea recta con pequeña curvatura)."""
    n_pts = 20
    angulo = np.radians(angulo_deg)
    coords = []
    for i in range(n_pts + 1):
        t = i / n_pts
        x = x_ini + largo * t * np.cos(angulo + 0.1 * np.sin(t * np.pi))
        y = y_ini + largo * t * np.sin(angulo + 0.1 * np.sin(t * np.pi))
        coords.append([round(x, 3), round(y, 3)])

    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"nombre": "Eje vía ejemplo"}
        }],
        "crs": {"type": "name", "properties": {"name": f"urn:ogc:def:crs:EPSG::{EPSG}"}}
    }
    with open(ruta, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"  Guardado: {ruta}  ({len(coords)} puntos)")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    n_cols = int(ANCHO_ZONA / RESOLUCION)
    n_rows = int(LARGO_ZONA / RESOLUCION)

    # Coordenadas de origen (esquina superior izquierda)
    x_ori = 800000.0
    y_ori = 1300600.0  # nota: transform.e es negativo

    transform = rasterio.transform.from_origin(x_ori, y_ori, RESOLUCION, RESOLUCION)

    print("Generando DEMs sintéticos...")

    # DEM pre-obra: terreno natural
    dem_pre = generar_dem(n_cols, n_rows, COTA_BASE, variacion=3.0, ruido=0.08)

    # DEM post-obra: con zonas de corte y relleno
    corte_zona   = (200, 600, 10, 50, -2.5)   # zona de corte de 2.5 m
    relleno_zona = (700, 1000, 15, 45, +1.8)  # zona de relleno de 1.8 m
    dem_post = generar_dem(n_cols, n_rows, COTA_BASE, variacion=3.0, ruido=0.04,
                           corte_zona=corte_zona, relleno_zona=relleno_zona)

    ruta_pre  = os.path.join(script_dir, "dem_pre.tif")
    ruta_post = os.path.join(script_dir, "dem_post.tif")
    ruta_eje  = os.path.join(script_dir, "eje_via.geojson")

    guardar_tif(dem_pre,  ruta_pre,  transform, EPSG)
    guardar_tif(dem_post, ruta_post, transform, EPSG)
    generar_eje(ruta_eje, x_ori + ANCHO_ZONA / 2, y_ori - LARGO_ZONA, LARGO_ZONA)

    print("\nDEMs sintéticos listos. Ahora corre:")
    print("  python calculo_volumen_odm.py")


if __name__ == "__main__":
    main()
