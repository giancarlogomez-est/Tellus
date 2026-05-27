"""Tablas HTML estilizadas para el dashboard (look del mockup)."""
from __future__ import annotations

from typing import Iterable
import streamlit as st


def _badge_active(active: bool = True) -> str:
    cls = "ok" if active else "warn"
    return f'<span class="status-badge {cls}">● {"Activo" if active else "Inactivo"}</span>'


def _badge_processed() -> str:
    return '<span class="status-badge ok">✓ Procesado</span>'


def render_flights_table(rows: list[dict]) -> None:
    """Tabla 'Vuelos y Modelos' del dashboard."""
    html = ['<table class="data-table">']
    html.append(
        "<thead><tr>"
        "<th>FECHA</th><th>ÁREA</th><th>GSD</th><th>ESTADO</th>"
        "</tr></thead><tbody>"
    )
    for r in rows:
        html.append(
            f"<tr>"
            f"<td>🛸 {r['fecha']}</td>"
            f"<td>{r['area']}</td>"
            f"<td>{r['gsd']}</td>"
            f"<td>{_badge_processed()}</td>"
            f"</tr>"
        )
    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_equipos_table(rows: list[dict]) -> None:
    """Tabla 'Equipos Activos'."""
    html = ['<table class="data-table">']
    html.append(
        "<thead><tr>"
        "<th>EQUIPO</th><th>TIPO</th><th>FRENTE</th>"
        "<th>ESTADO</th><th>HORAS HOY</th>"
        "</tr></thead><tbody>"
    )
    icons = {
        "Excavadora": "🚜",
        "Bulldozer": "🚛",
        "Volqueta": "🚚",
        "Motoniveladora": "🛻",
        "Vibrocompactador": "🛞",
    }
    for r in rows:
        icon = icons.get(r["tipo"], "🚜")
        html.append(
            f"<tr>"
            f"<td>{icon} {r['equipo']}</td>"
            f"<td>{r['tipo']}</td>"
            f"<td>{r['frente']}</td>"
            f"<td>{_badge_active(True)}</td>"
            f"<td>{r['horas']} h</td>"
            f"</tr>"
        )
    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_rendimientos_table(rows: list[dict]) -> None:
    """Tabla 'Rendimiento de Equipos (Hoy)'."""
    html = ['<table class="data-table">']
    html.append(
        "<thead><tr>"
        "<th>EQUIPO</th><th>TIPO</th><th>PRODUCCIÓN</th><th>RENDIMIENTO</th>"
        "</tr></thead><tbody>"
    )
    for r in rows:
        trend = "trend-up" if r["trend"] == "up" else "trend-down"
        arrow = "↗" if r["trend"] == "up" else "↘"
        html.append(
            f"<tr>"
            f"<td>{r['equipo']}</td>"
            f"<td>{r['tipo']}</td>"
            f"<td>{r['produccion']}</td>"
            f"<td class='{trend}'>{r['rendimiento']} {arrow}</td>"
            f"</tr>"
        )
    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_progress_bars(items: Iterable[tuple[str, float]]) -> None:
    """Lista de barras de progreso para 'Avance por Frente'."""
    blocks = []
    for label, pct in items:
        blocks.append(
            f"""
            <div class="progress-row">
                <span>{label}</span>
                <span class="pct">{pct:.1f}%</span>
            </div>
            <div class="progress-bar">
                <div class="fill" style="width: {pct:.1f}%"></div>
            </div>
            """
        )
    st.markdown("".join(blocks), unsafe_allow_html=True)
