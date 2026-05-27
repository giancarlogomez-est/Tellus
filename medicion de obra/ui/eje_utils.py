"""Carga del eje de la vía y muestreo de DEMs a lo largo del mismo."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np


def _cargar_eje_dxf(path: str):
    """Igual que en pipeline.cargar_eje_dxf, replicado para evitar
    importar pipeline.py (que tiene side-effects)."""
    import ezdxf
    from shapely.geometry import LineString
    from shapely.ops import linemerge, unary_union

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    segs = []

    for ent in msp:
        tipo = ent.dxftype()
        if tipo == "LINE":
            p1 = (ent.dxf.start.x, ent.dxf.start.y)
            p2 = (ent.dxf.end.x,   ent.dxf.end.y)
            segs.append(LineString([p1, p2]))
        elif tipo == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in ent.get_points()]
            if len(pts) >= 2: segs.append(LineString(pts))
        elif tipo == "POLYLINE":
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in ent.vertices]
            if len(pts) >= 2: segs.append(LineString(pts))
        elif tipo == "SPLINE":
            try:
                pts = [(p.x, p.y) for p in ent.flattening(0.01)]
            except Exception:
                pts = [(p[0], p[1]) for p in ent.control_points]
            if len(pts) >= 2: segs.append(LineString(pts))
        elif tipo == "ARC":
            cx, cy = ent.dxf.center.x, ent.dxf.center.y
            r = ent.dxf.radius
            a1 = math.radians(ent.dxf.start_angle)
            a2 = math.radians(ent.dxf.end_angle)
            if a2 < a1: a2 += 2 * math.pi
            n = max(32, int((a2 - a1) / math.radians(2)))
            angs = np.linspace(a1, a2, n)
            pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angs]
            segs.append(LineString(pts))

    if not segs:
        raise ValueError(f"No hay polilíneas en {path}")
    if len(segs) == 1:
        return segs[0]

    merged = linemerge(unary_union(segs))
    if merged.geom_type == "MultiLineString":
        return max(merged.geoms, key=lambda g: g.length)
    return merged


def cargar_eje(path: str, crs_ref=None):
    """Carga el eje desde .dxf, .geojson, .shp o cualquier formato vectorial.
    Devuelve un shapely LineString."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".dxf":
        return _cargar_eje_dxf(str(p))
    # GeoJSON/SHP — usar geopandas y reproyectar al CRS del raster si es posible
    import geopandas as gpd
    gdf = gpd.read_file(str(p))
    if crs_ref is not None and gdf.crs and gdf.crs != crs_ref:
        gdf = gdf.to_crs(crs_ref)
    g = gdf.geometry.iloc[0]
    if g.geom_type == "MultiLineString":
        from shapely.ops import linemerge
        g = linemerge(g)
        if g.geom_type == "MultiLineString":
            g = max(g.geoms, key=lambda x: x.length)
    return g


def puntos_a_lo_largo(eje, espaciado_m: float, prog_inicio_m: float = 0.0):
    """Genera puntos uniformemente espaciados sobre el eje.

    Devuelve un dict con arrays paralelos:
        prog : progresivas (m)  — eje X del perfil
        xs   : coordenada Este
        ys   : coordenada Norte
    """
    L = eje.length
    dists = np.arange(0, L + 1e-6, espaciado_m)
    xs = np.zeros_like(dists, dtype="float64")
    ys = np.zeros_like(dists, dtype="float64")
    for i, d in enumerate(dists):
        p = eje.interpolate(min(d, L))
        xs[i] = p.x
        ys[i] = p.y
    return {
        "prog": prog_inicio_m + dists,
        "xs":   xs,
        "ys":   ys,
    }


def muestrear_array(arr: np.ndarray, transform, xs, ys) -> np.ndarray:
    """Lee las cotas de un raster (array 2D + transform afín) en los puntos
    (xs, ys) dados en coordenadas mundo. Devuelve NaN fuera del raster."""
    import rasterio.transform as rtf
    nrows, ncols = arr.shape
    out = np.full(len(xs), np.nan, dtype="float64")
    for i, (x, y) in enumerate(zip(xs, ys)):
        try:
            row, col = rtf.rowcol(transform, float(x), float(y), op=int)
        except Exception:
            continue
        if 0 <= row < nrows and 0 <= col < ncols:
            v = arr[row, col]
            if np.isfinite(v):
                out[i] = v
    # Suavizado mínimo: rellenar NaN aislados por interpolación lineal
    if np.any(np.isnan(out)) and np.any(np.isfinite(out)):
        idx = np.arange(len(out))
        ok = np.isfinite(out)
        if ok.sum() >= 2:
            out[~ok] = np.interp(idx[~ok], idx[ok], out[ok])
    return out


@lru_cache(maxsize=8)
def cargar_eje_cached(path: str, crs_wkt: str | None):
    """Caché del eje + sus puntos no, pero del LineString sí (DXF es lento)."""
    from rasterio.crs import CRS
    crs = CRS.from_wkt(crs_wkt) if crs_wkt else None
    return cargar_eje(path, crs)
