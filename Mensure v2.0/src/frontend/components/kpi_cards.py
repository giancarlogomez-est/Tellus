"""KPI cards estilizadas (con icono + delta vs. periodo anterior)."""
from __future__ import annotations
import streamlit as st


def kpi_card(
    icon: str,
    color: str,
    label: str,
    value: str,
    delta: str | None = None,
    delta_up: bool = True,
    delta_suffix: str = "vs ayer",
) -> None:
    """
    Renderiza una tarjeta KPI según el estilo del mockup.

    Args:
        icon: Emoji o caracter a mostrar en el chip izquierdo.
        color: Paleta del chip ('orange','green','dark','purple','blue','indigo').
        label: Texto descriptivo arriba del valor.
        value: Valor principal (ya formateado: "128,450 m³").
        delta: Variación opcional ("+12.5%").
        delta_up: True para verde / flecha arriba, False para rojo / abajo.
        delta_suffix: Texto en gris a la derecha del delta.
    """
    delta_html = ""
    if delta:
        arrow_class = "up" if delta_up else "down"
        delta_html = (
            f'<div class="kpi-delta {arrow_class}">{delta}'
            f' <span class="muted">{delta_suffix}</span></div>'
        )

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-icon {color}">{icon}</div>
            <div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                {delta_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
