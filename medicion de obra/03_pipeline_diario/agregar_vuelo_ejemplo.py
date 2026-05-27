"""
Genera un DSM sintético para una fecha y avance específicos.
============================================================
Úsalo para simular vuelos adicionales después de haber corrido
generar_serie_ejemplo.py.

Uso:
    python agregar_vuelo_ejemplo.py --fecha 2025-05-08 --avance 0.85
    python agregar_vuelo_ejemplo.py --fecha 2025-05-09 --avance 1.0

--avance: fracción de avance respecto al estado final (0.0 = baseline, 1.0 = terminado)
"""

import argparse
import numpy as np
import rasterio
from rasterio.crs import CRS
from pathlib import Path
from datetime import date

BASE = Path(__file__).parent.parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha",  default=date.today().isoformat(),
                        help="Fecha del vuelo (YYYY-MM-DD)")
    parser.add_argument("--avance", type=float, default=0.5,
                        help="Fracción de avance: 0.0 = sin mover, 1.0 = terminado")
    args = parser.parse_args()

    avance = max(0.0, min(1.0, args.avance))
    fecha  = args.fecha

    # Leer baseline para tomar la misma grilla y CRS
    baseline_path = BASE / "baseline" / "dem_baseline.tif"
    if not baseline_path.exists():
        print("[ERROR] No se encontró baseline/dem_baseline.tif")
        print("        Corre primero: python generar_serie_ejemplo.py")
        return

    with rasterio.open(str(baseline_path)) as src:
        meta = src.meta.copy()
        arr_base = src.read(1).astype("float64")
        nodata   = src.nodata if src.nodata else -9999.0
        tf       = src.transform

    COLS = meta["width"]; ROWS = meta["height"]
    X0 = tf.c; Y0 = tf.f; RES = abs(tf.a)

    E, N = np.meshgrid(X0 + np.arange(COLS)*RES,
                       Y0 - np.arange(ROWS)*RES)
    x_rel = E - X0

    # Reproducir la misma superficie final que en generar_serie_ejemplo.py
    np.random.seed(42)
    t  = np.linspace(0, 1, 200)
    cx = X0 + 50 + 300*t
    cy = Y0 - 40 + 8*np.sin(2*np.pi*t)

    def dist_cross(E_, N_, cx_, cy_):
        E_f, N_f = E_.ravel(), N_.ravel()
        D = np.zeros(len(E_f)); best = np.full(len(E_f), np.inf)
        for k in range(len(cx_)-1):
            ax, ay, bx, by = cx_[k], cy_[k], cx_[k+1], cy_[k+1]
            dx, dy = bx-ax, by-ay; sl2 = dx*dx+dy*dy
            if sl2 < 1e-9: continue
            t_ = np.clip(((E_f-ax)*dx + (N_f-ay)*dy)/sl2, 0, 1)
            px, py = ax+t_*dx, ay+t_*dy
            d = np.hypot(E_f-px, N_f-py)
            cross = dx*(N_f-ay) - dy*(E_f-ax)
            new_best = d < best
            D = np.where(new_best, d*np.sign(cross), D)
            best = np.minimum(best, d)
        return D.reshape(E_.shape)

    D = dist_cross(E, N, cx, cy)
    corredor = np.abs(D) > 30

    # Reconstruir baseline y superficie final con la misma semilla
    z_base_full = (1247.0 + 0.020*x_rel
                   + 2.5*np.sin(2*np.pi*x_rel/280)
                   + 0.12*D
                   + 0.30*np.sin(2*np.pi*x_rel/45)
                   + np.random.normal(0, 0.04, E.shape))

    z_final = (1248.0 + 0.020*x_rel
               + 0.04*D
               + np.random.normal(0, 0.008, E.shape))

    # Nuevo vuelo con el nivel de avance pedido
    np.random.seed(None)  # ruido aleatorio para este vuelo
    z_vuelo = z_base_full + avance*(z_final - z_base_full) + np.random.normal(0, 0.008, E.shape)
    z_out   = np.where(corredor, nodata, z_vuelo).astype("float32")

    # Guardar
    dir_vuelo = BASE / "vuelos" / fecha
    dir_vuelo.mkdir(parents=True, exist_ok=True)
    out_path  = dir_vuelo / "dsm.tif"

    meta.update(dtype="float32", nodata=nodata)
    with rasterio.open(str(out_path), "w", **meta) as dst:
        dst.write(z_out, 1)

    # Estadísticas rápidas
    mask = ~corredor
    dz   = (z_vuelo - z_base_full)[mask]
    vc   = abs(dz[dz < 0].sum()) * RES**2
    vr   = dz[dz > 0].sum() * RES**2

    print(f"  vuelos/{fecha}/dsm.tif  creado  (avance={avance*100:.0f}%)")
    print(f"  Corte aprox:   {vc:>10,.0f} m³")
    print(f"  Relleno aprox: {vr:>10,.0f} m³")
    print(f"\nAhora corre:")
    print(f"  python pipeline.py --fecha {fecha}")

if __name__ == "__main__":
    main()
