"""Calcula volúmenes de corte/relleno por frente de obra.

Lee:
  baseline/dem_baseline.tif  — DEM inicial (terreno natural)
  baseline/dem_final.tif     — DEM final (superficie de diseño)
  baseline/eje_via.dxf       — Eje de la vía
  proyecto_config.json       — frentes, prog_inicio_m, ancho_corredor

Escribe:
  baseline/frentes_resultado.json

Lógica de signo:
  dz = dem_final - dem_ini
  dz < 0  →  terreno sobre la cota de diseño  →  CORTE
  dz > 0  →  terreno bajo la cota de diseño   →  RELLENO
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent   # medicion de obra/


def _km_str(m: float) -> str:
    m_int = int(m)
    return f"K{m_int // 1000}+{m_int % 1000:03d}"


def main() -> None:
    # ── Configuración ────────────────────────────────────────────────────
    cfg_path = BASE / "proyecto_config.json"
    if not cfg_path.exists():
        print("ERROR: proyecto_config.json no encontrado.", flush=True)
        sys.exit(1)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    frentes = cfg.get("frentes", [])
    if not frentes:
        print("ERROR: No hay frentes de obra definidos en la configuración.", flush=True)
        sys.exit(1)

    prog_inicio = float(cfg.get("prog_inicio_m", 0.0))
    ancho       = float(cfg.get("ancho_corredor", 20.0))

    # ── Rutas ────────────────────────────────────────────────────────────
    dem_ini_path = BASE / "baseline" / "dem_baseline.tif"
    dem_fin_path = BASE / "baseline" / "dem_final.tif"
    eje_path     = BASE / "baseline" / "eje_via.dxf"

    for p in (dem_ini_path, dem_fin_path, eje_path):
        if not p.exists():
            print(f"ERROR: No se encontró {p.name}", flush=True)
            sys.exit(1)

    # ── DEM inicial ──────────────────────────────────────────────────────
    print("Cargando DEM inicial …", flush=True)
    import rasterio

    with rasterio.open(str(dem_ini_path)) as src:
        arr_ini = src.read(1).astype("float64")
        nd = src.nodata
        if nd is not None:
            arr_ini[arr_ini == nd] = np.nan
        transform = src.transform
        crs       = src.crs
        nrows, ncols = arr_ini.shape

    pixel_w  = abs(transform.a)
    pixel_h  = abs(transform.e)
    pixel_m2 = pixel_w * pixel_h

    # ── DEM final (alineado al grid del DEM ini) ─────────────────────────
    print("Cargando DEM final y alineando al grid del DEM inicial …", flush=True)
    arr_fin = np.full((nrows, ncols), np.nan, dtype="float64")
    from rasterio.warp import reproject, Resampling
    with rasterio.open(str(dem_fin_path)) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=arr_fin,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata if src.nodata is not None else -9999.0,
            dst_nodata=np.nan,
        )

    # ── Eje de la vía ────────────────────────────────────────────────────
    print("Cargando eje de la vía …", flush=True)
    sys.path.insert(0, str(BASE))
    from ui.eje_utils import cargar_eje
    eje = cargar_eje(str(eje_path))

    # ── Raster de abscisas (distancia a lo largo del eje) ───────────────
    print("Generando raster de abscisas …", flush=True)
    from scipy.spatial import cKDTree

    L         = eje.length
    n_samples = max(int(L) + 2, 3)
    sample_ds = np.linspace(0.0, L, n_samples)
    eje_pts   = np.array(
        [(eje.interpolate(d).x, eje.interpolate(d).y) for d in sample_ds]
    )
    eje_abs   = prog_inicio + sample_ds

    # Centros de pixel
    cols_1d = np.arange(ncols, dtype="float64")
    rows_1d = np.arange(nrows, dtype="float64")
    xs_1d   = transform.c + (cols_1d + 0.5) * transform.a
    ys_1d   = transform.f + (rows_1d + 0.5) * transform.e
    xs_2d, ys_2d = np.meshgrid(xs_1d, ys_1d)

    tree    = cKDTree(eje_pts)
    coords  = np.column_stack([xs_2d.ravel(), ys_2d.ravel()])
    raw_d, nn_idx = tree.query(coords, workers=-1)

    abs_raster  = eje_abs[nn_idx].reshape(nrows, ncols)
    dist_raster = raw_d.reshape(nrows, ncols)

    # Máscara de corredor
    in_corridor = dist_raster <= (ancho / 2.0)

    # ── ΔZ y máscara de datos válidos ────────────────────────────────────
    dz    = arr_fin - arr_ini          # + relleno | − corte
    valid = np.isfinite(dz) & in_corridor

    # ── Calcular por frente ──────────────────────────────────────────────
    resultados: list[dict] = []
    t_corte = t_relleno = 0.0

    for i, fr in enumerate(frentes):
        nombre     = str(fr.get("nombre", f"Frente {i + 1}"))
        abs_ini_fr = float(fr["abs_ini"])
        abs_fin_fr = float(fr["abs_fin"])

        print(
            f"Calculando {nombre}  "
            f"({_km_str(abs_ini_fr)} → {_km_str(abs_fin_fr)}) …",
            flush=True,
        )

        mask   = valid & (abs_raster >= abs_ini_fr) & (abs_raster <= abs_fin_fr)
        dz_fr  = dz[mask]
        n_px   = int(mask.sum())

        corte_m3   = float(np.sum(np.abs(dz_fr[dz_fr < 0])) * pixel_m2)
        relleno_m3 = float(np.sum(dz_fr[dz_fr > 0]) * pixel_m2)
        balance_m3 = relleno_m3 - corte_m3
        area_m2    = n_px * pixel_m2

        t_corte   += corte_m3
        t_relleno += relleno_m3

        print(
            f"  → Área: {area_m2:,.0f} m²  |  "
            f"Corte: {corte_m3:,.1f} m³  |  "
            f"Relleno: {relleno_m3:,.1f} m³  |  "
            f"Balance: {balance_m3:+,.1f} m³",
            flush=True,
        )

        resultados.append({
            "nombre":     nombre,
            "abs_ini":    abs_ini_fr,
            "abs_fin":    abs_fin_fr,
            "area_m2":    round(area_m2, 1),
            "corte_m3":   round(corte_m3, 1),
            "relleno_m3": round(relleno_m3, 1),
            "balance_m3": round(balance_m3, 1),
        })

    # Fila de totales
    t_balance = t_relleno - t_corte
    resultados.append({
        "nombre":     "TOTAL",
        "abs_ini":    None,
        "abs_fin":    None,
        "area_m2":    None,
        "corte_m3":   round(t_corte, 1),
        "relleno_m3": round(t_relleno, 1),
        "balance_m3": round(t_balance, 1),
    })

    print(
        f"\nTOTAL  →  Corte: {t_corte:,.1f} m³  |  "
        f"Relleno: {t_relleno:,.1f} m³  |  Balance: {t_balance:+,.1f} m³",
        flush=True,
    )

    # ── Guardar resultado ────────────────────────────────────────────────
    out_path = BASE / "baseline" / "frentes_resultado.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(resultados, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nResultados guardados en {out_path.name}", flush=True)


if __name__ == "__main__":
    main()
