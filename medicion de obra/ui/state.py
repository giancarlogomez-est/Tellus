"""Estado compartido de la app: rutas, configuración, registro."""
from __future__ import annotations

import json
import os
import subprocess
import sys
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
        self.gen_serie_script: Path = base / "03_pipeline_diario" / "generar_serie_ejemplo.py"
        self.gen_dems_script: Path = base / "02_dron_odm" / "generar_dems_ejemplo.py"

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

    def run_generar_serie(self) -> subprocess.Popen:
        return subprocess.Popen(
            [self.python_exe(), str(self.gen_serie_script)],
            cwd=str(self.gen_serie_script.parent), env=_utf8_env(),
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

    # ── Rásters para el basemap del dashboard ────────────────────────────
    def dem_baseline_path(self) -> Optional[Path]:
        for ext in ("tif", "tiff"):
            p = self.baseline_dir / f"dem_baseline.{ext}"
            if p.exists():
                return p
        return None

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

    def ultimo_dz_dia(self) -> Optional[Path]:
        """ΔZ del vuelo más reciente que tenga dz_dia (fallback demo)."""
        if not self.vuelos_dir.exists():
            return None
        for d in sorted(self.vuelos_dir.iterdir(), reverse=True):
            p = d / "dz_dia.tif"
            if d.is_dir() and p.exists():
                return p
        return None
