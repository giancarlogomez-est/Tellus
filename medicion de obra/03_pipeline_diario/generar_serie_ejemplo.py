"""
Generador de serie de DEMs sintéticos — 7 días de avance simulado
==================================================================
Crea el baseline y 7 DSMs diarios que simulan el avance progresivo
de la obra. Úsalos para probar el pipeline completo.

Escribe los archivos en la carpeta raíz del proyecto (medicion de obra/):
    baseline/dem_baseline.tif
    baseline/eje_via.dxf
    vuelos/YYYY-MM-DD/dsm.tif  (7 días)

Uso (desde la carpeta 03_pipeline_diario/):
    python generar_serie_ejemplo.py
"""

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
import ezdxf
from pathlib import Path
from datetime import date, timedelta
import json

# BASE apunta a la raíz del proyecto (carpeta padre de 03_pipeline_diario)
BASE = Path(__file__).parent.parent

RES  = 0.25
X0   = 820_000.0
Y0   = 700_070.0
COLS = 1_400
ROWS =   320
CRS_ = CRS.from_epsg(32618)
tf   = from_origin(X0, Y0, RES, RES)

meta = dict(driver="GTiff", dtype="float32", nodata=-9999.0,
            width=COLS, height=ROWS, count=1, crs=CRS_, transform=tf)

# ── Coordenadas ──────────────────────────────────────────────────────────────
E, N = np.meshgrid(X0 + np.arange(COLS)*RES,
                   Y0 - np.arange(ROWS)*RES)
x_rel = E - X0

# ── Eje de la vía ─────────────────────────────────────────────────────────────
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

print("Calculando distancias transversales …")
D = dist_cross(E, N, cx, cy)
corredor = np.abs(D) > 30

np.random.seed(42)

# ── Superficie de terreno natural (baseline) ──────────────────────────────────
z_base = (1247.0 + 0.020*x_rel
          + 2.5*np.sin(2*np.pi*x_rel/280)
          + 0.12*D
          + 0.30*np.sin(2*np.pi*x_rel/45)
          + np.random.normal(0, 0.04, E.shape))

# ── Subrasante objetivo (estado final) ────────────────────────────────────────
z_final = (1248.0 + 0.020*x_rel
           + 0.04*D
           + np.random.normal(0, 0.008, E.shape))

# ── Guardar baseline ──────────────────────────────────────────────────────────
dir_bl = BASE / "baseline"
dir_bl.mkdir(exist_ok=True)

z_out = np.where(corredor, -9999.0, z_base).astype("float32")
with rasterio.open(str(dir_bl / "dem_baseline.tif"), "w", **meta) as dst:
    dst.write(z_out, 1)
print("  baseline/dem_baseline.tif  creado")

# ── Eje de la vía como DXF ────────────────────────────────────────────────────
doc = ezdxf.new("R2010")
doc.units = ezdxf.units.M
msp = doc.modelspace()

puntos_eje = [(float(cx[i]), float(cy[i])) for i in range(len(cx))]
msp.add_lwpolyline(puntos_eje, dxfattribs={"layer": "EJE_VIA", "color": 1})

doc.saveas(str(dir_bl / "eje_via.dxf"))
print("  baseline/eje_via.dxf       creado")

# ── Generar DSMs diarios (7 días, avance progresivo por zonas) ────────────────
FECHA_INICIO = date(2025, 5, 1)
N_DIAS       = 7

def factor_avance_x(x_rel_, dia, n_dias):
    """Factor de avance (0-1) por pixel según posición x y día."""
    progreso_total = dia / n_dias
    zona_a = x_rel_ < 150
    zona_b = x_rel_ >= 150
    fac = np.zeros_like(x_rel_, dtype=float)
    fac_a = np.clip(progreso_total * 1.4, 0, 1)
    fac_b = np.clip((progreso_total - 0.3) * 1.4, 0, 1)
    fac[zona_a] = fac_a
    fac[zona_b] = fac_b
    return fac

print("\nGenerando serie de vuelos diarios:")
for dia in range(1, N_DIAS+1):
    fecha = FECHA_INICIO + timedelta(days=dia-1)
    fac   = factor_avance_x(x_rel, dia, N_DIAS)

    z_dia = z_base + fac*(z_final - z_base) + np.random.normal(0, 0.008, E.shape)
    z_out = np.where(corredor, -9999.0, z_dia).astype("float32")

    dir_vuelo = BASE / "vuelos" / fecha.isoformat()
    dir_vuelo.mkdir(parents=True, exist_ok=True)
    with rasterio.open(str(dir_vuelo / "dsm.tif"), "w", **meta) as dst:
        dst.write(z_out, 1)

    dz = (z_dia - z_base)[~corredor]
    vc = abs(dz[dz < 0].sum()) * RES**2
    vr = dz[dz > 0].sum() * RES**2
    print(f"  vuelos/{fecha.isoformat()}/dsm.tif  "
          f"(acum: corte {vc:,.0f} m³ | relleno {vr:,.0f} m³)")

# ── Actualizar config ─────────────────────────────────────────────────────────
cfg_path = BASE / "proyecto_config.json"
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["eje_via"] = "baseline/eje_via.dxf"
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n  proyecto_config.json actualizado → eje_via: baseline/eje_via.dxf")

print(f"""
Listo. Para probar el pipeline completo (desde 03_pipeline_diario/):

  python pipeline.py --fecha 2025-05-01
  python pipeline.py --fecha 2025-05-02
  python pipeline.py --fecha 2025-05-03
  python pipeline.py --fecha 2025-05-04
  python pipeline.py --fecha 2025-05-05
  python pipeline.py --fecha 2025-05-06
  python pipeline.py --fecha 2025-05-07 --semanal --mensual
""")
