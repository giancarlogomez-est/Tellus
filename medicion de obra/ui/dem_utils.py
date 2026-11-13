"""Utilidades para leer DEMs y alinear DSMs al grid del baseline.

Espejo mínimo de las funciones del pipeline para evitar importar
pipeline.py (que tiene side-effects al cargarlo)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import warnings

import numpy as np

warnings.filterwarnings("ignore")


MAX_LADO_UI = 3000   # la interfaz nunca carga más de ~9 M de píxeles por DEM


def cargar_dem(path: str, nodata: float = -9999.0, max_lado: int = MAX_LADO_UI):
    """Lee un DEM para visualización. Si es muy grande (vuelos reales de varios
    GB) lo lee decimado y devuelve el transform ajustado a esa resolución."""
    import rasterio
    from rasterio.enums import Resampling
    with rasterio.open(path) as src:
        f = max(1.0, max(src.width, src.height) / max_lado)
        h, w = max(1, int(src.height / f)), max(1, int(src.width / f))
        arr = src.read(1, out_shape=(h, w),
                       resampling=Resampling.average if f > 1 else Resampling.nearest
                       ).astype("float32")
        nd = src.nodata if src.nodata is not None else nodata
        arr[(arr == nd) | (arr <= -9000) | ~np.isfinite(arr)] = np.nan
        tf = src.transform * src.transform.scale(src.width / w, src.height / h)
        meta = src.meta.copy()
        meta.update(width=w, height=h, transform=tf)
        return arr, tf, src.crs, meta


def alinear_dem(path: str, ref_tf, ref_crs, ref_shape,
                nodata: float = -9999.0) -> np.ndarray:
    import rasterio
    from rasterio.warp import reproject, Resampling
    arr = np.full(ref_shape, np.nan, dtype="float32")
    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, 1), destination=arr,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=ref_tf, dst_crs=ref_crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata if src.nodata is not None else nodata,
            dst_nodata=np.nan,
        )
    return arr


# ── caché simple para no releer disco en cada repintado ──────────────────
@lru_cache(maxsize=16)
def cargar_dem_cached(path: str):
    return cargar_dem(path)


@lru_cache(maxsize=64)
def alinear_dem_cached(path: str, ref_path: str):
    arr_ref, tf, crs, _ = cargar_dem_cached(ref_path)
    return alinear_dem(path, tf, crs, arr_ref.shape)


def malla_xy(arr_shape, transform):
    """Devuelve mallas X, Y (coordenadas mundo) para usar con plot_surface."""
    nrows, ncols = arr_shape
    # transform: a, b, c (x0), d, e, f (y0)
    cols = np.arange(ncols)
    rows = np.arange(nrows)
    x0, dx = transform.c, transform.a
    y0, dy = transform.f, transform.e  # dy es negativo normalmente
    xs = x0 + (cols + 0.5) * dx
    ys = y0 + (rows + 0.5) * dy
    X, Y = np.meshgrid(xs, ys)
    return X, Y
