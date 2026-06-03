"""Estado compartido de la app: rutas, configuración, registro."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd


def _utf8_env() -> dict:
    """Fuerza UTF-8 en stdout de los subprocesos Python (evita
    UnicodeEncodeError al imprimir caracteres como → o ° en Windows)."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


class ProjectState:
    def __init__(self, base: Path):
        self.base: Path = base
        self.config_path: Path = base / "proyecto_config.json"
        self.registro_path: Path = base / "registro.csv"
        self.registro_sec_path: Path = base / "registro_secciones.csv"
        self.baseline_dir: Path = base / "baseline"
        self.vuelos_dir: Path = base / "vuelos"
        self.reportes_dir: Path = base / "reportes"
        self.pipeline_script: Path = base / "03_pipeline_diario" / "pipeline.py"
        self.odm_script: Path = base / "02_dron_odm" / "calculo_volumen_odm.py"
        self.equipos_path: Path = base / "equipos.json"
        self.registros_equipos_path: Path = base / "registros_equipos.csv"
        self.calcular_frentes_script: Path = base / "calcular_volumen_frentes.py"
        self.frentes_resultado_path_file: Path = base / "baseline" / "frentes_resultado.json"
        self.perfil_objetivo_path_file: Path = base / "baseline" / "perfil_objetivo.json"
        self.perfil_avance_path_file: Path = base / "baseline" / "perfil_avance.json"

    # ── Configuración ────────────────────────────────────────────────────
    def load_config(self) -> Optional[dict]:
        if not self.config_path.exists():
            return None
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def save_config(self, cfg: dict) -> None:
        self.config_path.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def project_configured(self) -> bool:
        return self.config_path.exists()

    def baseline_ready(self) -> tuple[bool, list[str]]:
        """Devuelve (ok, lista_faltantes)."""
        falt = []
        if not (self.baseline_dir / "dem_baseline.tif").exists():
            falt.append("dem_baseline.tif")
        if not any((self.baseline_dir / f"eje_via.{ext}").exists()
                   for ext in ("dxf", "dwg", "geojson")):
            falt.append("eje_via.(dxf|dwg|geojson)")
        if not (self.baseline_dir / "dem_final.tif").exists():
            falt.append("dem_final.tif")
        return (not falt), falt

    # ── Registro de vuelos ───────────────────────────────────────────────
    def load_registro(self) -> pd.DataFrame:
        if not self.registro_path.exists():
            return pd.DataFrame()
        df = pd.read_csv(self.registro_path)
        df["fecha"] = pd.to_datetime(df["fecha"], format="mixed", errors="coerce")
        df = df.dropna(subset=["fecha"])
        return df.sort_values("fecha").reset_index(drop=True)

    def vuelos_disponibles(self) -> list[str]:
        if not self.vuelos_dir.exists():
            return []
        return sorted(
            d.name for d in self.vuelos_dir.iterdir()
            if d.is_dir() and (d / "dsm.tif").exists()
        )

    def vuelos_procesados(self) -> set[str]:
        df = self.load_registro()
        if df.empty:
            return set()
        return {d.strftime("%Y-%m-%d") for d in df["fecha"]}

    # ── Subprocesos ──────────────────────────────────────────────────────
    def python_exe(self) -> str:
        return sys.executable

    def run_pipeline(self, fecha: str, semanal: bool = False,
                     mensual: bool = False) -> subprocess.Popen:
        cmd = [self.python_exe(), str(self.pipeline_script), "--fecha", fecha]
        if semanal: cmd.append("--semanal")
        if mensual: cmd.append("--mensual")
        return subprocess.Popen(
            cmd, cwd=str(self.base), env=_utf8_env(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def run_odm(self) -> subprocess.Popen:
        return subprocess.Popen(
            [self.python_exe(), str(self.odm_script)],
            cwd=str(self.odm_script.parent), env=_utf8_env(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    # ── Reportes ─────────────────────────────────────────────────────────
    def listar_reportes(self, tipo: str) -> list[Path]:
        d = self.reportes_dir / tipo
        if not d.exists():
            return []
        return sorted(d.glob("reporte_*.xlsx"), reverse=True)

    def heatmap_para_fecha(self, fecha: str) -> Optional[Path]:
        p = self.reportes_dir / "diarios" / f"heatmap_{fecha}.png"
        return p if p.exists() else None

    def borrar_entrada_registro(self, fecha: str) -> None:
        """Elimina una fecha del registro.csv y registro_secciones.csv."""
        target = date.fromisoformat(fecha)
        if self.registro_path.exists():
            df = pd.read_csv(self.registro_path, parse_dates=["fecha"])
            df = df[df["fecha"].dt.date != target]
            df.to_csv(self.registro_path, index=False, date_format="%Y-%m-%d")
        if self.registro_sec_path.exists():
            df_sec = pd.read_csv(self.registro_sec_path)
            if not df_sec.empty and "fecha" in df_sec.columns:
                df_sec["fecha"] = pd.to_datetime(df_sec["fecha"], errors="coerce")
                df_sec = df_sec[df_sec["fecha"].dt.date != target]
                df_sec.to_csv(self.registro_sec_path, index=False,
                              date_format="%Y-%m-%d")

    # ── Rásters para el basemap del dashboard ────────────────────────────
    def dem_baseline_path(self) -> Optional[Path]:
        for ext in ("tif", "tiff"):
            p = self.baseline_dir / f"dem_baseline.{ext}"
            if p.exists():
                return p
        return None

    def dem_final_path(self) -> Optional[Path]:
        for ext in ("tif", "tiff"):
            p = self.baseline_dir / f"dem_final.{ext}"
            if p.exists():
                return p
        return None

    # ── Frentes de obra ──────────────────────────────────────────────────
    def load_frentes(self) -> list[dict]:
        cfg = self.load_config() or {}
        return list(cfg.get("frentes", []))

    def save_frentes(self, frentes: list[dict]) -> None:
        cfg = self.load_config() or {}
        cfg["frentes"] = frentes
        self.save_config(cfg)

    def frentes_resultado_path(self) -> Optional[Path]:
        p = self.frentes_resultado_path_file
        return p if p.exists() else None

    def load_frentes_resultado(self) -> tuple[list[dict], str | None, str]:
        """Devuelve (lista_frentes, fecha_str_o_None, modo_label)."""
        p = self.frentes_resultado_path()
        if p is None:
            return [], None, ""
        raw = json.loads(p.read_text(encoding="utf-8"))
        # Formato nuevo: {"fecha": ..., "modo": ..., "frentes": [...]}
        if isinstance(raw, dict) and "frentes" in raw:
            return raw["frentes"], raw.get("fecha"), raw.get("modo", "")
        # Formato legado: lista plana
        return raw, None, ""

    def load_perfil_objetivo(self) -> list[dict]:
        p = self.perfil_objetivo_path_file
        if not p.exists():
            return []
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw.get("perfil", [])

    def load_perfil_avance(self) -> tuple[list[dict], str | None]:
        p = self.perfil_avance_path_file
        if not p.exists():
            return [], None
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw.get("perfil", []), raw.get("fecha")

    def run_volumen_frentes(self, fecha: str | None = None) -> subprocess.Popen:
        cmd = [self.python_exe(), str(self.calcular_frentes_script)]
        if fecha:
            cmd += ["--fecha", fecha]
        return subprocess.Popen(
            cmd, cwd=str(self.base), env=_utf8_env(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def calcular_volumen_objetivo(self) -> tuple[float, float]:
        """Calcula vol_corte/relleno objetivo desde dem_final − dem_baseline.

        Persiste los valores en proyecto_config.json y retorna (vol_corte, vol_relleno).
        Lanza FileNotFoundError si alguno de los DEMs no existe.
        """
        import numpy as np
        import rasterio
        from rasterio.warp import reproject, Resampling

        baseline_path = self.baseline_dir / "dem_baseline.tif"
        final_path    = self.baseline_dir / "dem_final.tif"

        if not baseline_path.exists() or not final_path.exists():
            raise FileNotFoundError(
                "Faltan dem_baseline.tif o dem_final.tif en baseline/")

        with rasterio.open(str(baseline_path)) as src:
            arr_base   = src.read(1).astype("float64")
            nd         = src.nodata
            if nd is not None:
                arr_base[arr_base == nd] = np.nan
            tf_ref     = src.transform
            crs_ref    = src.crs
            pixel_area = abs(tf_ref.a * tf_ref.e)
            shape      = arr_base.shape

        arr_final = np.full(shape, np.nan, dtype="float64")
        with rasterio.open(str(final_path)) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=arr_final,
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=tf_ref,        dst_crs=crs_ref,
                resampling=Resampling.bilinear,
                src_nodata=src.nodata, dst_nodata=np.nan,
            )

        dz    = arr_final - arr_base
        valid = dz[np.isfinite(dz)]

        vol_corte   = round(float(abs(valid[valid < 0].sum()) * pixel_area), 2)
        vol_relleno = round(float(valid[valid >= 0].sum()    * pixel_area), 2)

        if self.config_path.exists():
            cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
            cfg["vol_corte_objetivo"]   = vol_corte
            cfg["vol_relleno_objetivo"] = vol_relleno
            self.config_path.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        return vol_corte, vol_relleno

    def import_dem(self, src_path: str, fecha: str) -> None:
        """Copia un .tif como vuelos/<fecha>/dsm.tif."""
        import shutil
        dest_dir = self.vuelos_dir / fecha
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_dir / "dsm.tif")

    def dz_dia_path(self, fecha: str) -> Optional[Path]:
        """Raster ΔZ del día para un vuelo (carpeta vuelos/<fecha>)."""
        p = self.vuelos_dir / fecha / "dz_dia.tif"
        return p if p.exists() else None

    # ── Equipos y flotas ────────────────────────────────────────────────
    def load_equipos_data(self) -> dict:
        if not self.equipos_path.exists():
            return {"equipos": [], "flotas": []}
        return json.loads(self.equipos_path.read_text(encoding="utf-8"))

    def save_equipos_data(self, data: dict) -> None:
        self.equipos_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_registros_equipos(self) -> pd.DataFrame:
        if not self.registros_equipos_path.exists():
            return pd.DataFrame()
        df = pd.read_csv(self.registros_equipos_path)
        if df.empty:
            return df
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        return df.sort_values("fecha").reset_index(drop=True)

    def save_registro_equipo(self, registro: dict) -> None:
        df = self.load_registros_equipos()
        if not df.empty and "fecha" in df.columns and "equipo_id" in df.columns:
            try:
                target = date.fromisoformat(str(registro["fecha"]))
                mask = ~(
                    (df["fecha"].dt.date == target)
                    & (df["equipo_id"] == registro["equipo_id"])
                )
                df = df[mask]
            except Exception:
                pass
        new_row = pd.DataFrame([registro])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(self.registros_equipos_path, index=False, encoding="utf-8")

    def ultimo_dz_dia(self) -> Optional[Path]:
        """ΔZ del vuelo más reciente que tenga dz_dia (fallback demo)."""
        if not self.vuelos_dir.exists():
            return None
        for d in sorted(self.vuelos_dir.iterdir(), reverse=True):
            p = d / "dz_dia.tif"
            if d.is_dir() and p.exists():
                return p
        return None
