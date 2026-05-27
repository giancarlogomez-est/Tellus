"""Estado compartido de la app: rutas y acceso a datos persistidos."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd


class ProjectState:
    """
    Centraliza el acceso al sistema de archivos del proyecto Mensure v2.0.

    Tres áreas:
        - Configuración (proyecto_config.json en raíz).
        - Histórico de jornadas (data/processed/historico_acumulado.xlsx).
        - Reportes Excel generados (reports/*.xlsx).
    """
    def __init__(self, base: Path):
        self.base: Path = base
        self.config_path: Path = base / "proyecto_config.json"
        self.history_path: Path = base / "data" / "processed" / "historico_acumulado.xlsx"
        self.reports_dir: Path = base / "reports"
        self.raw_dir: Path = base / "data" / "raw"

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

    # ── Histórico ────────────────────────────────────────────────────────
    def load_history(self) -> pd.DataFrame:
        if not self.history_path.exists():
            return pd.DataFrame()
        try:
            df = pd.read_excel(self.history_path)
            if "fecha" in df.columns:
                df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
                df = df.dropna(subset=["fecha"])
            return df
        except Exception:
            return pd.DataFrame()

    # ── Reportes Excel ───────────────────────────────────────────────────
    def list_reports(self) -> list[Path]:
        if not self.reports_dir.exists():
            return []
        return sorted(self.reports_dir.glob("*.xlsx"), reverse=True)
