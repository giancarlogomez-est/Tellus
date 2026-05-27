"""Gráficos Plotly del dashboard.

- Barras apiladas Excavación / Terraplén + línea de balance Neto.
- Donut de distribución de volúmenes.
"""
from __future__ import annotations

import plotly.graph_objects as go


COLOR_EXC = "#f59e0b"      # naranja
COLOR_TER = "#10b981"      # verde
COLOR_NET = "#3b82f6"      # azul


def volumes_by_period(
    labels: list[str],
    excavacion: list[float],
    terraplen: list[float],
    neto: list[float],
) -> go.Figure:
    """Barras apiladas con la línea de Neto superpuesta (eje secundario)."""
    fig = go.Figure()
    fig.add_bar(
        name="Excavación (m³)", x=labels, y=excavacion,
        marker_color=COLOR_EXC, hovertemplate="%{y:,.0f} m³<extra></extra>",
    )
    fig.add_bar(
        name="Terraplén (m³)", x=labels, y=[-v for v in terraplen],
        marker_color=COLOR_TER, hovertemplate="%{y:,.0f} m³<extra></extra>",
    )
    fig.add_scatter(
        name="Neto (m³)", x=labels, y=neto,
        mode="lines+markers",
        line=dict(color=COLOR_NET, width=2.5),
        marker=dict(size=7, color=COLOR_NET,
                    line=dict(color="white", width=2)),
        hovertemplate="%{y:,.0f} m³<extra></extra>",
    )

    fig.update_layout(
        barmode="relative",
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, font=dict(size=11),
        ),
        xaxis=dict(showgrid=False, tickfont=dict(color="#9ca3af", size=11)),
        yaxis=dict(
            gridcolor="#f3f4f6", zerolinecolor="#e5e7eb",
            tickfont=dict(color="#9ca3af", size=11),
            tickformat=",.0f",
        ),
    )
    return fig


def volumes_donut(excavacion: float, terraplen: float, neto: float) -> go.Figure:
    """Donut con la distribución y el total al centro."""
    total = excavacion + terraplen
    pct_exc = excavacion / total * 100 if total else 0
    pct_ter = terraplen / total * 100 if total else 0

    fig = go.Figure(
        go.Pie(
            labels=["Excavación", "Terraplén"],
            values=[excavacion, terraplen],
            hole=0.7,
            marker=dict(colors=[COLOR_EXC, COLOR_TER]),
            textinfo="none",
            hovertemplate="%{label}: %{value:,.0f} m³<extra></extra>",
            sort=False,
        )
    )
    fig.update_layout(
        height=290,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        annotations=[
            dict(
                text=(
                    f"<span style='color:#6b7280;font-size:12px'>Volumen Total</span><br>"
                    f"<span style='color:#111827;font-size:22px;font-weight:700'>"
                    f"{int(total + neto):,} m³</span>"
                ),
                x=0.5, y=0.5, showarrow=False,
            )
        ],
    )
    return fig
