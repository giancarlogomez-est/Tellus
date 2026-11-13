"""Calcula volúmenes de corte/relleno de DISEÑO por frente de obra.

Lee:
  baseline/dem_baseline.tif  — DEM inicial (terreno natural)
  baseline/dem_final.tif     — DEM final (superficie de diseño)
  eje de la vía              — el configurado (DXF / GeoJSON)
  proyecto_config.json       — frentes, prog_inicio_m, ancho_corredor

Escribe:
  baseline/frentes_resultado.json

Lógica de signo:
  dz = dem_final - dem_ini
  dz < 0  →  terreno sobre la cota de diseño  →  CORTE
  dz > 0  →  terreno bajo la cota de diseño   →  RELLENO

Usa el mismo núcleo que el pipeline (nucleo.py): mismo corredor (ancho a cada
lado del eje), misma malla y misma asignación de abscisas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).parent   # medicion de obra/
sys.path.insert(0, str(BASE))
import nucleo  # noqa: E402


def main() -> None:
    cfg_path = BASE / "proyecto_config.json"
    if not cfg_path.exists():
        sys.exit("ERROR: proyecto_config.json no encontrado.")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("dem_baseline", "baseline/dem_baseline.tif")

    dem_fin_path = None
    for ext in ("tif", "tiff"):
        p = BASE / "baseline" / f"dem_final.{ext}"
        if p.exists():
            dem_fin_path = p
    if dem_fin_path is None:
        sys.exit("ERROR: No se encontró baseline/dem_final.tif (superficie de diseño).")

    print("Preparando corredor y abscisas …", flush=True)
    nucleo.exigir_elevacion(dem_fin_path, "El DEM final")
    cor = nucleo.corredor_del_proyecto(BASE, cfg)
    epsg = cfg.get("epsg_proyecto")
    print(f"  Malla: {cor.shape[1]}×{cor.shape[0]} px a {cor.res:.2f} m  |  "
          f"eje {cor.eje.length:,.0f} m  |  ancho {cor.ancho:.0f} m a cada lado", flush=True)

    print("Leyendo DEM inicial y DEM final …", flush=True)
    arr_ini = nucleo.leer_en_corredor(BASE / cfg["dem_baseline"], cor, epsg)
    arr_fin = nucleo.leer_en_corredor(dem_fin_path, cor, epsg)
    dz = arr_fin - arr_ini          # + relleno | − corte
    if nucleo.cobertura(dz, cor) < 1:
        raise nucleo.EntradaInvalida(
            "El DEM final no se superpone con el corredor: revisa el sistema de coordenadas.")

    frentes = cfg.get("frentes") or []
    if not frentes:
        fin = cor.prog_inicio + cor.eje.length
        frentes = [{"nombre": "Todo el tramo", "abs_ini": cor.prog_inicio, "abs_fin": fin}]
        print("  (No hay frentes definidos: se calcula el tramo completo.)", flush=True)

    resultados: list[dict] = []
    t_corte = t_relleno = 0.0
    for i, fr in enumerate(frentes):
        nombre = str(fr.get("nombre", f"Frente {i + 1}"))
        a_ini, a_fin = float(fr["abs_ini"]), float(fr["abs_fin"])
        v = nucleo.volumen_en_tramo(dz, cor, a_ini, a_fin)
        balance = v["relleno_m3"] - v["corte_m3"]
        t_corte += v["corte_m3"]; t_relleno += v["relleno_m3"]
        print(f"{nombre}  ({nucleo.km_str(a_ini)} → {nucleo.km_str(a_fin)})\n"
              f"  → Área: {v['area_m2']:,.0f} m²  |  Corte: {v['corte_m3']:,.1f} m³  |  "
              f"Relleno: {v['relleno_m3']:,.1f} m³  |  Balance: {balance:+,.1f} m³", flush=True)
        if v["area_m2"] == 0:
            print("  [!] Sin datos en este tramo: revisa las abscisas del frente.", flush=True)
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
    out_path.write_text(json.dumps(resultados, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\nResultados guardados en {out_path.name}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except nucleo.EntradaInvalida as e:
        sys.exit(f"\n[ERROR] {e}")
