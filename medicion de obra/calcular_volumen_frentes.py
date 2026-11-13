"""Calcula volúmenes de corte/relleno por frente de obra.

Modos de operación
------------------
  Sin --fecha  : dz = dem_final − dem_baseline  (volumen objetivo de diseño)
  Con --fecha  : dz = dz_acum del vuelo         (avance real a esa fecha)

El eje DXF se toma siempre con origen K0+000 (prog_inicio = 0); las abscisas
de los frentes deben darse en metros desde ese origen.

Lee:
  baseline/dem_baseline.tif       — DEM inicial (terreno natural)
  baseline/dem_final.tif          — DEM final de diseño  (solo sin --fecha)
  eje de la vía configurado       — inicia en K0+000
  vuelos/FECHA/dz_acum.tif        — ΔZ acumulado del vuelo  (solo con --fecha)
  proyecto_config.json            — frentes, ancho_corredor

Escribe:
  baseline/frentes_resultado.json
  baseline/perfil_objetivo.json | baseline/perfil_avance.json

Usa el mismo núcleo que el pipeline (nucleo.py): misma malla recortada al
corredor y mismo ancho (ancho_corredor = metros a CADA lado del eje).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent   # medicion de obra/
sys.path.insert(0, str(BASE))
import nucleo  # noqa: E402

STEP = 10.0   # separación de estaciones del perfil (m)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula volúmenes de corte/relleno por frente de obra.")
    parser.add_argument(
        "--fecha", default=None, metavar="YYYY-MM-DD",
        help="Fecha del vuelo para calcular avance real. "
             "Si se omite, calcula el volumen objetivo (dem_final − dem_baseline).",
    )
    args = parser.parse_args()

    cfg_path = BASE / "proyecto_config.json"
    if not cfg_path.exists():
        sys.exit("ERROR: proyecto_config.json no encontrado.")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("dem_baseline", "baseline/dem_baseline.tif")

    frentes = cfg.get("frentes", [])
    if not frentes:
        sys.exit("ERROR: No hay frentes de obra definidos en la configuración.")

    # ── Corredor: el eje DXF inicia en K0+000 → prog_inicio = 0 ───────────
    print("Preparando corredor y abscisas (origen K0+000) …", flush=True)
    cor = nucleo.corredor_del_proyecto(BASE, {**cfg, "prog_inicio_m": 0.0})
    epsg = cfg.get("epsg_proyecto")
    umbral = 0.0
    print(f"  Malla: {cor.shape[1]}×{cor.shape[0]} px a {cor.res:.2f} m  |  "
          f"eje {cor.eje.length:,.0f} m  |  ancho {cor.ancho:.0f} m a cada lado", flush=True)

    # ── Raster de diferencia ΔZ ───────────────────────────────────────────
    if args.fecha:
        dz_path = BASE / "vuelos" / args.fecha / "dz_acum.tif"
        if not dz_path.exists():
            sys.exit(f"ERROR: No se encontró dz_acum.tif para la fecha {args.fecha}\n"
                     f"  Ruta esperada: {dz_path}\n"
                     "  Verifica que el pipeline se haya ejecutado para esa fecha.")
        modo_label = f"Avance al {args.fecha}"
        print(f"Modo: volumen de avance real — vuelo {args.fecha}", flush=True)
        dz = nucleo.leer_en_corredor(dz_path, cor, epsg)
        umbral = float(cfg.get("umbral_dz", 0.05) or 0)   # igual que el pipeline
    else:
        dem_fin_path = nucleo.ruta_dem_final(BASE)
        if dem_fin_path is None:
            sys.exit("ERROR: No se encontró dem_final.tif")
        modo_label = "Objetivo (diseño)"
        print("Modo: volumen objetivo (dem_final − dem_baseline)", flush=True)
        nucleo.exigir_elevacion(dem_fin_path, "El DEM final")
        dz = (nucleo.leer_en_corredor(dem_fin_path, cor, epsg)
              - nucleo.leer_en_corredor(BASE / cfg["dem_baseline"], cor, epsg))
        # + relleno (llenar) | − corte (excavar)

    if nucleo.cobertura(dz, cor) < 1:
        raise nucleo.EntradaInvalida(
            "No hay datos dentro del corredor: revisa el sistema de coordenadas "
            "del eje y de los modelos.")

    # ── Calcular por frente ──────────────────────────────────────────────
    resultados: list[dict] = []
    t_corte = t_relleno = 0.0
    for i, fr in enumerate(frentes):
        nombre = str(fr.get("nombre", f"Frente {i + 1}"))
        a_ini, a_fin = float(fr["abs_ini"]), float(fr["abs_fin"])
        v = nucleo.volumen_en_tramo(dz, cor, a_ini, a_fin, umbral)
        balance = v["relleno_m3"] - v["corte_m3"]
        t_corte += v["corte_m3"]; t_relleno += v["relleno_m3"]
        print(f"Calculando {nombre}  ({nucleo.km_str(a_ini)} → {nucleo.km_str(a_fin)}) …\n"
              f"  → Área: {v['area_m2']:,.0f} m²  |  Corte: {v['corte_m3']:,.1f} m³  |  "
              f"Relleno: {v['relleno_m3']:,.1f} m³  |  Balance: {balance:+,.1f} m³", flush=True)
        if v["area_m2"] == 0:
            print("  [!] Sin datos en este tramo: las abscisas del frente se miden "
                  "desde el inicio del eje (K0+000).", flush=True)
        resultados.append({
            "nombre": nombre, "abs_ini": a_ini, "abs_fin": a_fin,
            "area_m2": round(v["area_m2"], 1),
            "corte_m3": round(v["corte_m3"], 1),
            "relleno_m3": round(v["relleno_m3"], 1),
            "balance_m3": round(balance, 1),
        })

    t_balance = t_relleno - t_corte
    resultados.append({
        "nombre": "TOTAL", "abs_ini": None, "abs_fin": None, "area_m2": None,
        "corte_m3": round(t_corte, 1), "relleno_m3": round(t_relleno, 1),
        "balance_m3": round(t_balance, 1),
    })
    print(f"\nTOTAL  →  Corte: {t_corte:,.1f} m³  |  "
          f"Relleno: {t_relleno:,.1f} m³  |  Balance: {t_balance:+,.1f} m³", flush=True)

    out_path = BASE / "baseline" / "frentes_resultado.json"
    out_path.write_text(json.dumps(
        {"fecha": args.fecha, "modo": modo_label, "frentes": resultados},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultados guardados en {out_path.name}", flush=True)

    # ── Perfil por estación (cada 10 m, estación centrada) ───────────────
    print("\nGenerando perfil por estación (cada 10 m) …", flush=True)
    rangos = [(float(fr["abs_ini"]), float(fr["abs_fin"])) for fr in frentes
              if fr.get("abs_ini") is not None]
    a_min = min(r[0] for r in rangos)
    a_max = max(r[1] for r in rangos)
    n = int(np.floor((a_max - a_min) / STEP + 0.5)) + 1

    ok = np.isfinite(dz) & np.isfinite(cor.abscisa)
    d = dz[ok].astype("float64")
    if umbral > 0:
        d[np.abs(d) < umbral] = 0.0
    idx = np.floor((cor.abscisa[ok] - (a_min - STEP / 2.0)) / STEP).astype(int)
    dentro = (idx >= 0) & (idx < n)
    idx, d = idx[dentro], d[dentro]
    pa = cor.pixel_area
    corte = np.bincount(idx, weights=np.where(d < 0, -d, 0.0), minlength=n) * pa
    relleno = np.bincount(idx, weights=np.where(d > 0, d, 0.0), minlength=n) * pa
    cuenta = np.bincount(idx, minlength=n)

    perfil: list[dict] = []
    for k in range(n):
        st = a_min + k * STEP
        if cuenta[k] == 0 or not any(ini <= st <= fin for ini, fin in rangos):
            continue
        perfil.append({"abs": round(float(st), 1),
                       "corte_m3": round(float(corte[k]), 2),
                       "relleno_m3": round(float(relleno[k]), 2)})

    perfil_path = BASE / "baseline" / (
        "perfil_avance.json" if args.fecha else "perfil_objetivo.json")
    perfil_path.write_text(json.dumps(
        {"fecha": args.fecha, "modo": modo_label, "perfil": perfil},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Perfil por estación guardado en {perfil_path.name}  ({len(perfil)} puntos)",
          flush=True)


if __name__ == "__main__":
    try:
        main()
    except nucleo.EntradaInvalida as e:
        sys.exit(f"\n[ERROR] {e}")
