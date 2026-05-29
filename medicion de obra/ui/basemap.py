"""Genera el basemap del panel Vista 3D del dashboard.

Compone un relieve sombreado (hillshade) del DEM del proyecto y le
superpone el mapa de calor de cortes/llenos (ΔZ) del vuelo seleccionado,
con la convención del proyecto: rojo = corte, verde = relleno.

Devuelve un ``PIL.Image`` listo para mostrar como ``CTkImage`` o
``None`` si no hay datos suficientes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np


def _read_array(path: Path, out_shape=None):
    """Lee la primera banda de un raster como float32 con NaN en nodata."""
    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(path) as ds:
        if out_shape is not None:
            arr = ds.read(1, out_shape=out_shape,
                          resampling=Resampling.bilinear)
        else:
            arr = ds.read(1)
        arr = arr.astype("float32")
        nodata = ds.nodata
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)
    # valores extremos típicos de nodata en DEMs
    arr = np.where(arr < -1e4, np.nan, arr)
    return arr


def _hillshade(dem: np.ndarray, azim: float = 315.0, alt: float = 45.0,
               z_factor: float = 2.0) -> np.ndarray:
    """Relieve sombreado en [0, 1]."""
    filled = np.where(np.isfinite(dem), dem, np.nanmean(dem))
    dy, dx = np.gradient(filled * z_factor)
    slope = np.pi / 2.0 - np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    az_rad = np.radians(360.0 - azim + 90.0)
    alt_rad = np.radians(alt)
    shaded = (np.sin(alt_rad) * np.sin(slope) +
              np.cos(alt_rad) * np.cos(slope) * np.cos(az_rad - aspect))
    return np.clip((shaded + 1.0) / 2.0, 0.0, 1.0)


def build_overlay(dem_path: Optional[Path], dz_path: Optional[Path],
                  dz_clip: float = 3.0, max_alpha: float = 0.80,
                  umbral: float = 0.05):
    """Compone hillshade + heatmap ΔZ y devuelve un ``PIL.Image`` (RGB).

    - ``dem_path``: DEM base para el relieve (puede ser None → fondo plano).
    - ``dz_path``: raster ΔZ del vuelo (rojo=corte<0, verde=relleno>0).
    """
    try:
        from PIL import Image
        from matplotlib.colors import TwoSlopeNorm
        import matplotlib

        if dz_path is None or not Path(dz_path).exists():
            return None

        dz = _read_array(Path(dz_path))
        h, w = dz.shape

        # Basemap: hillshade del DEM (remuestreado a la malla de dz) o gris.
        if dem_path is not None and Path(dem_path).exists():
            dem = _read_array(Path(dem_path), out_shape=(h, w))
            base = _hillshade(dem)
        else:
            base = np.full((h, w), 0.72, dtype="float32")
        base_rgb = np.dstack([base, base, base])

        # Overlay ΔZ con colormap RdYlGn centrado en 0.
        clip = max(dz_clip, 0.1)
        norm = TwoSlopeNorm(vmin=-clip, vcenter=0.0, vmax=clip)
        cmap = matplotlib.colormaps["RdYlGn"]
        rgba = cmap(norm(np.nan_to_num(dz, nan=0.0)))
        rgb = rgba[..., :3]

        alpha = np.clip(np.abs(dz) / clip, 0.0, 1.0) * max_alpha
        alpha[~np.isfinite(dz)] = 0.0
        alpha[np.abs(dz) < umbral] = 0.0
        alpha = alpha[..., None]

        out = base_rgb * (1.0 - alpha) + rgb * alpha
        out = (np.clip(out, 0.0, 1.0) * 255).astype("uint8")
        return Image.fromarray(out, mode="RGB")
    except Exception:
        return None
