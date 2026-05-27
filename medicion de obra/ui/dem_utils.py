"""Utilidades para leer DEMs y alinear DSMs al grid del baseline.

Espejo mínimo de las funciones del pipeline para evitar importar
pipeline.py (que tiene side-effects al cargarlo)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import warnings

import numpy as np

warnings.filterwarnings("ignore")


def cargar_dem(path: str, nodata: float = -9999.0):
    import rasterio
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float64")
        arr[arr == (src.nodata if src.nodata is not None else nodata)] = np.nan
        return arr, src.transform, src.crs, src.meta.copy()


def alinear_dem(path: str, ref_tf, ref_crs, ref_shape,
                nodata: float = -9999.0) -> np.ndarray:
    import rasterio
    from rasterio.warp import reproject, Resampling
    arr = np.full(ref_shape, np.nan, dtype="float64")
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
