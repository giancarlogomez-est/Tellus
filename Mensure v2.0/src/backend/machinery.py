"""
Módulo de control de rendimientos de maquinaria.

Recibe los registros que el operador ingresa en el dashboard (tipo de equipo,
ID, horas operativas) y los cruza con el volumen movido ese día (calculado
por raster_processor) para obtener rendimientos individuales y de flota.
"""
from __future__ import annotations

from typing import List, Dict
import pandas as pd


def build_machinery_dataframe(records: List[Dict]) -> pd.DataFrame:
    """
    Convierte la lista de registros del formulario en un DataFrame limpio.

    Cada registro debe tener: tipo, id_equipo, horas, fecha.
    """
    if not records:
        return pd.DataFrame(
            columns=["fecha", "tipo", "id_equipo", "horas"]
        )
    df = pd.DataFrame(records)
    df["horas"] = pd.to_numeric(df["horas"], errors="coerce").fillna(0.0)
    df = df[df["horas"] > 0].reset_index(drop=True)
    return df


def compute_yields(
    machinery_df: pd.DataFrame,
    volumen_dia_m3: float,
) -> pd.DataFrame:
    """
    Calcula rendimientos individuales y de flota en m³/hora.

    Criterio de reparto:
        - El volumen total del día se prorratea entre los equipos según las
          horas operativas que cada uno reportó.
        - Rendimiento individual = volumen asignado / horas del equipo.
        - Rendimiento de flota   = volumen total / suma de horas.

    Args:
        machinery_df: DataFrame con columnas [fecha, tipo, id_equipo, horas].
        volumen_dia_m3: Volumen total ejecutado en la jornada (m³).

    Returns:
        DataFrame con columnas adicionales:
            volumen_asignado_m3, rendimiento_m3_h, rendimiento_flota_m3_h.
    """
    if machinery_df.empty:
        return machinery_df.assign(
            volumen_asignado_m3=[],
            rendimiento_m3_h=[],
            rendimiento_flota_m3_h=[],
        )

    total_horas = machinery_df["horas"].sum()
    if total_horas == 0:
        machinery_df["volumen_asignado_m3"] = 0.0
        machinery_df["rendimiento_m3_h"] = 0.0
        machinery_df["rendimiento_flota_m3_h"] = 0.0
        return machinery_df

    rendimiento_flota = volumen_dia_m3 / total_horas

    machinery_df = machinery_df.copy()
    machinery_df["volumen_asignado_m3"] = (
        machinery_df["horas"] / total_horas * volumen_dia_m3
    ).round(2)
    machinery_df["rendimiento_m3_h"] = (
        machinery_df["volumen_asignado_m3"] / machinery_df["horas"]
    ).round(2)
    machinery_df["rendimiento_flota_m3_h"] = round(rendimiento_flota, 2)

    return machinery_df


def fleet_summary(yields_df: pd.DataFrame) -> pd.DataFrame:
    """Resumen agregado por tipo de máquina para la pestaña diaria."""
    if yields_df.empty:
        return pd.DataFrame()
    grouped = (
        yields_df.groupby("tipo")
        .agg(
            equipos=("id_equipo", "nunique"),
            horas_totales=("horas", "sum"),
            volumen_m3=("volumen_asignado_m3", "sum"),
        )
        .reset_index()
    )
    grouped["rendimiento_m3_h"] = (
        grouped["volumen_m3"] / grouped["horas_totales"]
    ).round(2)
    return grouped
