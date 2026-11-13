"""Núcleo de cálculo de TELLUS — compartido por el pipeline, el cálculo por
frentes y la interfaz.

Ideas clave:
  * Solo se lee el corredor (eje ± ancho) y a una resolución de trabajo, así
    que los GeoTIFF de varios GB de un vuelo real no se cargan enteros.
  * Cada píxel se asigna a UNA sola abscisa (la del punto más cercano del eje),
    de modo que no hay doble conteo entre secciones en las curvas.
  * |ΔZ| por debajo de un umbral se trata como ruido y no suma volumen.
  * Los archivos de entrada se validan: una ortofoto (RGB) o un .ecw no
    contienen cotas y se rechazan con un mensaje claro.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MAX_PIXELES_MALLA = 40_000_000     # tope de la malla de trabajo (~160 MB en float32)
EXT_ELEVACION = (".tif", ".tiff")


class EntradaInvalida(Exception):
    """Un insumo no sirve para el cálculo (mensaje listo para el usuario)."""


# ══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN DE RÁSTERS DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
def inspeccionar_raster(path) -> dict:
    """Clasifica un ráster: 'elevacion' (sirve), 'ortofoto', 'ecw' o 'ilegible'.

    Devuelve un dict con: ok, tipo, mensaje, avisos y metadatos básicos.
    """
    p = Path(path)
    info: dict = {"ruta": str(p), "ok": False, "tipo": "ilegible",
                  "mensaje": "", "avisos": []}

    if p.suffix.lower() == ".ecw":
        info.update(tipo="ecw", mensaje=(
            "Los .ecw son ortofotos comprimidas (imagen de color): no contienen "
            "cotas, así que no sirven para medir volúmenes. Pide el modelo de "
            "elevación del mismo vuelo (DSM/MDS o MDT) en GeoTIFF."))
        return info

    import rasterio
    try:
        src = rasterio.open(str(p))
    except Exception as e:
        info["mensaje"] = f"No se pudo abrir el archivo como ráster: {e}"
        return info

    with src:
        dtype = src.dtypes[0]
        interp = [ci.name for ci in src.colorinterp]
        info.update(
            bandas=src.count, dtype=dtype, ancho=src.width, alto=src.height,
            resolucion=abs(src.transform.a),
            crs=(src.crs.to_string() if src.crs else None),
            tam_mb=round(p.stat().st_size / 1e6, 1),
        )
        es_color = (src.count >= 3 or "red" in interp or "palette" in interp)
        if es_color or dtype == "uint8":
            info.update(tipo="ortofoto", mensaje=(
                f"Este archivo es una imagen ({src.count} banda(s), {dtype}): es una "
                "ortofoto, no un modelo de elevación. Una ortofoto no contiene cotas "
                "y no permite medir volúmenes. Pide el DSM/MDS (o MDT) del mismo "
                "vuelo en GeoTIFF: 1 banda, valores decimales con la cota en metros."))
            return info

        if src.crs is None:
            info["avisos"].append(
                "El archivo no trae sistema de coordenadas; se asumirá el EPSG del proyecto.")
        elif src.crs.is_geographic:
            info.update(tipo="elevacion", mensaje=(
                "El modelo está en coordenadas geográficas (grados). Pídelo en un "
                "sistema proyectado en metros (p. ej. EPSG:9377 Origen Nacional)."))
            return info

        # Muestra reducida para comprobar que hay cotas plausibles
        paso = max(1, max(src.width, src.height) // 512)
        muestra = src.read(1, out_shape=(max(1, src.height // paso),
                                         max(1, src.width // paso)),
                           masked=True).astype("float64")
        vals = muestra.compressed()
        vals = vals[np.isfinite(vals) & (vals > -9000)]
        if vals.size == 0:
            info.update(tipo="elevacion",
                        mensaje="El ráster no contiene datos válidos (todo es nodata).")
            return info
        info.update(z_min=float(vals.min()), z_max=float(vals.max()))
        if info["resolucion"] > 1.0:
            info["avisos"].append(
                f"Resolución gruesa ({info['resolucion']:.2f} m/píxel): la precisión "
                "del volumen será limitada.")

    info.update(ok=True, tipo="elevacion", mensaje=(
        f"Modelo de elevación válido: {info['ancho']}×{info['alto']} px, "
        f"{info['resolucion']:.3f} m/px, cotas {info['z_min']:.1f}–{info['z_max']:.1f} m."))
    return info


def exigir_elevacion(path, etiqueta: str = "El archivo") -> dict:
    info = inspeccionar_raster(path)
    if not info["ok"]:
        raise EntradaInvalida(f"{etiqueta} ({Path(path).name}) no sirve: {info['mensaje']}")
    return info


# ══════════════════════════════════════════════════════════════════════════════
# EJE
# ══════════════════════════════════════════════════════════════════════════════
def _eje_en_crs(eje, bounds_raster, crs_raster, epsg_proyecto):
    """Si el eje no cae sobre el ráster, intenta reproyectarlo desde el EPSG
    del proyecto al CRS del ráster. Lanza EntradaInvalida si tampoco coincide."""
    from shapely.geometry import box
    caja = box(*bounds_raster)
    if eje.intersects(caja):
        return eje
    if epsg_proyecto and crs_raster is not None:
        try:
            from pyproj import Transformer
            from shapely.ops import transform as shp_transform
            tr = Transformer.from_crs(int(epsg_proyecto), crs_raster.to_wkt(),
                                      always_xy=True)
            eje2 = shp_transform(tr.transform, eje)
            if eje2.intersects(caja):
                print(f"  Eje reproyectado de EPSG:{epsg_proyecto} al sistema del DEM.")
                return eje2
        except Exception:
            pass
    raise EntradaInvalida(
        "El eje de la vía no cae sobre el DEM de referencia. Revisa que el eje y "
        "el DEM estén en el mismo sistema de coordenadas (EPSG del proyecto en "
        "Configuración).")


# ══════════════════════════════════════════════════════════════════════════════
# MALLA DE TRABAJO SOBRE EL CORREDOR
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Corredor:
    eje: object                  # shapely LineString en el CRS de la malla
    transform: object            # affine de la malla
    crs: object
    shape: tuple
    res: float
    abscisa: np.ndarray          # float32, NaN fuera del corredor
    prog_inicio: float
    ancho: float

    @property
    def pixel_area(self) -> float:
        return self.res * self.res

    @property
    def n_pix_corredor(self) -> int:
        return int(np.isfinite(self.abscisa).sum())

    def meta(self) -> dict:
        return dict(driver="GTiff", dtype="float32", nodata=-9999.0, count=1,
                    width=self.shape[1], height=self.shape[0], crs=self.crs,
                    transform=self.transform, compress="deflate", tiled=True)


def construir_corredor(eje, dem_ref_path, ancho: float, prog_inicio: float = 0.0,
                       res_trabajo: float | None = None,
                       epsg_proyecto: int | None = None) -> Corredor:
    """Crea la malla de trabajo (recortada al eje ± ancho) y el ráster de abscisas.

    `ancho` es la distancia desde el eje hacia CADA lado.
    """
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
    from rasterio.features import geometry_mask
    from scipy.spatial import cKDTree
    import shapely

    with rasterio.open(str(dem_ref_path)) as src:
        crs = src.crs or (CRS.from_epsg(int(epsg_proyecto)) if epsg_proyecto else None)
        res_nativa = abs(src.transform.a)
        bounds = tuple(src.bounds)

    eje = _eje_en_crs(eje, bounds, crs, epsg_proyecto)

    res = float(res_trabajo) if res_trabajo and res_trabajo > 0 else res_nativa
    res = max(res, res_nativa)          # nunca más fino que el dato original
    zona = eje.buffer(ancho, cap_style="flat")
    minx, miny, maxx, maxy = zona.bounds
    while ((maxx - minx) / res) * ((maxy - miny) / res) > MAX_PIXELES_MALLA:
        res *= 1.5
    if res_trabajo and res > float(res_trabajo) * 1.01 and res > res_nativa * 1.01:
        print(f"  [!] Corredor muy extenso: resolución de trabajo ajustada a {res:.2f} m.")

    minx = math.floor(minx / res) * res - res
    maxy = math.ceil(maxy / res) * res + res
    ncols = int(math.ceil((maxx - minx) / res)) + 1
    nrows = int(math.ceil((maxy - miny) / res)) + 1
    tf = from_origin(minx, maxy, res, res)

    dentro = geometry_mask([zona], out_shape=(nrows, ncols), transform=tf, invert=True)
    rows, cols = np.nonzero(dentro)
    xs = tf.c + (cols + 0.5) * tf.a
    ys = tf.f + (rows + 0.5) * tf.e

    paso = min(res, 0.5)
    ds = np.linspace(0.0, eje.length, max(int(eje.length / paso) + 1, 2))
    pts = shapely.get_coordinates(shapely.line_interpolate_point(eje, ds))
    _, idx = cKDTree(pts).query(np.column_stack([xs, ys]), workers=-1)

    abscisa = np.full((nrows, ncols), np.nan, dtype="float32")
    abscisa[rows, cols] = (prog_inicio + ds[idx]).astype("float32")

    return Corredor(eje=eje, transform=tf, crs=crs, shape=(nrows, ncols), res=res,
                    abscisa=abscisa, prog_inicio=float(prog_inicio), ancho=float(ancho))


def leer_en_corredor(path, cor: Corredor, epsg_defecto: int | None = None) -> np.ndarray:
    """Lee un modelo de elevación remuestreado a la malla del corredor.
    Devuelve float32 con NaN donde no hay dato o fuera del corredor."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import reproject, Resampling

    arr = np.full(cor.shape, np.nan, dtype="float32")
    with rasterio.open(str(path)) as src:
        src_crs = src.crs or cor.crs or (CRS.from_epsg(int(epsg_defecto)) if epsg_defecto else None)
        metodo = (Resampling.average if cor.res > 1.5 * abs(src.transform.a)
                  else Resampling.bilinear)
        reproject(source=rasterio.band(src, 1), destination=arr,
                  src_transform=src.transform, src_crs=src_crs,
                  dst_transform=cor.transform, dst_crs=cor.crs or src_crs,
                  src_nodata=src.nodata, dst_nodata=np.nan,
                  resampling=metodo, num_threads=4)
    arr[~np.isfinite(arr) | (arr <= -9000) | (arr >= 1e20)] = np.nan
    arr[~np.isfinite(cor.abscisa)] = np.nan
    return arr


def cobertura(arr: np.ndarray, cor: Corredor) -> float:
    """Porcentaje del corredor que tiene dato en `arr`."""
    n = cor.n_pix_corredor
    return 100.0 * float(np.isfinite(arr).sum()) / n if n else 0.0


# ══════════════════════════════════════════════════════════════════════════════
# VOLÚMENES
# ══════════════════════════════════════════════════════════════════════════════
def km_str(m: float) -> str:
    m = int(round(m))
    return f"K{m // 1000}+{m % 1000:03d}"


def filtrar_ruido(dz: np.ndarray, umbral: float) -> np.ndarray:
    """Pone a 0 los |ΔZ| menores que el umbral (ruido del levantamiento)."""
    if not umbral or umbral <= 0:
        return dz
    out = dz.copy()
    out[np.abs(out) < umbral] = 0.0
    return out


def volumenes_por_seccion(dz: np.ndarray, cor: Corredor, espaciado: float,
                          umbral: float = 0.0):
    """Corte/relleno por tramo de `espaciado` metros a lo largo del eje.

    dz < 0 → corte ; dz > 0 → relleno.  Devuelve un DataFrame con columnas
    progresiva, abs_ini, vol_corte, vol_relleno, area_m2.
    """
    import pandas as pd

    n = max(int(math.ceil(cor.eje.length / espaciado)), 1)
    ok = np.isfinite(dz) & np.isfinite(cor.abscisa)
    d = dz[ok].astype("float64")
    if umbral and umbral > 0:
        d[np.abs(d) < umbral] = 0.0
    idx = np.clip(((cor.abscisa[ok] - cor.prog_inicio) // espaciado).astype(int), 0, n - 1)
    pa = cor.pixel_area
    corte = np.bincount(idx, weights=np.where(d < 0, -d, 0.0), minlength=n) * pa
    relleno = np.bincount(idx, weights=np.where(d > 0, d, 0.0), minlength=n) * pa
    area = np.bincount(idx, minlength=n) * pa
    abs_ini = cor.prog_inicio + np.arange(n) * espaciado
    return pd.DataFrame({
        "progresiva": [km_str(a) for a in abs_ini],
        "abs_ini": abs_ini,
        "vol_corte": np.round(corte, 3),
        "vol_relleno": np.round(relleno, 3),
        "area_m2": np.round(area, 1),
    })


def volumen_en_tramo(dz: np.ndarray, cor: Corredor, abs_ini: float, abs_fin: float,
                     umbral: float = 0.0) -> dict:
    """Corte/relleno/área entre dos abscisas."""
    m = np.isfinite(dz) & (cor.abscisa >= abs_ini) & (cor.abscisa <= abs_fin)
    d = dz[m].astype("float64")
    if umbral and umbral > 0:
        d[np.abs(d) < umbral] = 0.0
    pa = cor.pixel_area
    return {"corte_m3": float(-d[d < 0].sum() * pa),
            "relleno_m3": float(d[d > 0].sum() * pa),
            "area_m2": float(m.sum() * pa)}


def guardar_raster(arr: np.ndarray, cor: Corredor, path) -> None:
    import rasterio
    out = np.where(np.isfinite(arr), arr, -9999.0).astype("float32")
    with rasterio.open(str(path), "w", **cor.meta()) as dst:
        dst.write(out, 1)


# ══════════════════════════════════════════════════════════════════════════════
# CONTEXTO DE PROYECTO
# ══════════════════════════════════════════════════════════════════════════════
def ruta_eje(base: Path, cfg: dict) -> Path:
    """Ruta del eje: la de la configuración o el primer eje_via.* de baseline/."""
    p = base / cfg.get("eje_via", "baseline/eje_via.dxf")
    if p.exists():
        return p
    for ext in ("dxf", "geojson", "shp"):
        q = base / "baseline" / f"eje_via.{ext}"
        if q.exists():
            return q
    raise EntradaInvalida(
        f"No se encontró el eje de la vía ({p.name}). Cárgalo en DXF o GeoJSON "
        "(un .dwg debe exportarse antes a DXF).")


def corredor_del_proyecto(base: Path, cfg: dict) -> Corredor:
    """Valida el baseline, carga el eje y construye la malla del corredor."""
    import sys
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    from ui.eje_utils import cargar_eje

    baseline = base / cfg["dem_baseline"]
    if not baseline.exists():
        raise EntradaInvalida(f"No se encontró el DEM de referencia: {baseline}")
    exigir_elevacion(baseline, "El DEM de referencia")
    eje = cargar_eje(str(ruta_eje(base, cfg)))
    return construir_corredor(
        eje, baseline,
        ancho=float(cfg.get("ancho_corredor", 20.0)),
        prog_inicio=float(cfg.get("prog_inicio_m", 0.0)),
        res_trabajo=float(cfg.get("resolucion_trabajo", 0.5) or 0),
        epsg_proyecto=cfg.get("epsg_proyecto"),
    )


def ruta_dem_final(base: Path):
    for ext in ("tif", "tiff"):
        p = base / "baseline" / f"dem_final.{ext}"
        if p.exists():
            return p
    return None


def volumen_objetivo(base: Path, cfg: dict, cor: Corredor | None = None):
    """(corte, relleno) de diseño = dem_final − dem_baseline dentro del corredor.
    Devuelve None si no hay dem_final."""
    final = ruta_dem_final(base)
    if final is None:
        return None
    exigir_elevacion(final, "El DEM final")
    cor = cor or corredor_del_proyecto(base, cfg)
    epsg = cfg.get("epsg_proyecto")
    dz = (leer_en_corredor(final, cor, epsg)
          - leer_en_corredor(base / cfg.get("dem_baseline", "baseline/dem_baseline.tif"), cor, epsg))
    v = dz[np.isfinite(dz)].astype("float64")
    pa = cor.pixel_area
    return round(float(-v[v < 0].sum() * pa), 2), round(float(v[v > 0].sum() * pa), 2)


if __name__ == "__main__":      # python nucleo.py archivo.tif  → diagnóstico rápido
    import json, sys
    for a in sys.argv[1:]:
        print(json.dumps(inspeccionar_raster(a), indent=2, ensure_ascii=False))
