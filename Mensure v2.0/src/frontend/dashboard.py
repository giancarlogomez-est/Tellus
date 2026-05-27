"""
Mensure v2.0 — Dashboard principal (vista "Resumen general del proyecto").

Reproduce fielmente el mockup de diseño:
    - Sidebar de navegación con logo, items, proyecto y usuario.
    - Encabezado con título + filtros de periodo y frente.
    - 6 KPI cards (Excavación, Terraplén, Neto, Área, Pavimento, Avance).
    - Visor 3D placeholder + radio de superficies.
    - Tabla de Vuelos, gráfico de Volúmenes por Periodo, donut de Distribución.
    - Tabla de Equipos Activos, tabla de Rendimientos y Avance por Frente.

Los datos están "cableados" a valores demo que coinciden con la imagen;
en producción provendrán del backend (raster_processor, machinery).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st

from src.frontend.styles import inject_css
from src.frontend.components.sidebar import render_sidebar
from src.frontend.components.kpi_cards import kpi_card
from src.frontend.components.tables import (
    render_equipos_table,
    render_flights_table,
    render_progress_bars,
    render_rendimientos_table,
)
from src.frontend.components.charts import volumes_by_period, volumes_donut


# ---------------------------------------------------------------------------
# Config de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mensure v2.0 — Dashboard",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
active_page = render_sidebar(active="dashboard")


# ---------------------------------------------------------------------------
# Header de página: título + filtros
# ---------------------------------------------------------------------------
h_left, h_spacer, h_f1, h_f2 = st.columns([4, 4, 1.3, 1.3])
with h_left:
    st.markdown(
        """
        <div class="page-header">
            <h1>Dashboard</h1>
            <div class="subtitle">Resumen general del proyecto</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h_f1:
    st.selectbox(
        "Periodo",
        ["20 - 26 Mayo, 2024", "13 - 19 Mayo, 2024", "Mes actual"],
        label_visibility="collapsed",
    )
with h_f2:
    st.selectbox(
        "Frente",
        ["Todos los frentes", "Frente A", "Frente B", "Frente C", "Frente D"],
        label_visibility="collapsed",
    )

st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Fila 1: 3 KPIs + Visor 3D (que se extiende hasta fila 2)
# ---------------------------------------------------------------------------
top_left, top_right = st.columns([2, 1.2], gap="medium")

with top_left:
    # 3 KPIs arriba
    k1, k2, k3 = st.columns(3, gap="small")
    with k1:
        kpi_card("⛏️", "orange",
                 "Volumen Excavación", "128,450 m³",
                 "↑ 12.5%", delta_up=True)
    with k2:
        kpi_card("⛰️", "green",
                 "Volumen Terraplén", "96,320 m³",
                 "↑ 8.3%", delta_up=True)
    with k3:
        kpi_card("⚖️", "dark",
                 "Volumen Neto", "32,130 m³",
                 "↑ 4.2%", delta_up=True)

    st.markdown("<div style='height:0.9rem'></div>", unsafe_allow_html=True)

    # 3 KPIs abajo
    k4, k5, k6 = st.columns(3, gap="small")
    with k4:
        kpi_card("📐", "purple",
                 "Área Topografiada", "45.6 ha",
                 "↑ 5.1 ha", delta_up=True)
    with k5:
        kpi_card("🛣️", "blue",
                 "Longitud Pavimento", "2.45 km",
                 "↑ 0.18 km", delta_up=True)
    with k6:
        kpi_card("📊", "indigo",
                 "Avance General", "62.7%",
                 "↑ 3.6%", delta_up=True,
                 delta_suffix="vs semana pasada")

with top_right:
    # Card del visor 3D
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-title">Vista 3D - Comparación de Superficies</div>',
        unsafe_allow_html=True,
    )

    # Placeholder de la imagen 3D
    st.markdown(
        """
        <div style="background: linear-gradient(135deg,#dbeafe 0%,#fef3c7 50%,#fecaca 100%);
                    height: 220px; border-radius: 8px;
                    display: flex; align-items: center; justify-content: center;
                    position: relative; overflow: hidden;">
            <div style="font-size: 3rem; opacity:.6">🏔️</div>
            <div style="position:absolute; bottom: 8px; left: 8px;
                        background: rgba(255,255,255,0.85);
                        border-radius:4px; padding: 4px 8px;
                        font-size: 0.7rem; color: #374151;">
                Cotas (m) &nbsp; <span style="color:#3b82f6">100</span>
                <span style="color:#10b981">120</span>
                <span style="color:#f59e0b">140</span>
                <span style="color:#ef4444">160</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Radio de superficies
    surface = st.radio(
        "Superficie a visualizar",
        [
            "Superficie actual — 26 Mayo, 2024",
            "Superficie anterior — 25 Mayo, 2024",
            "Diseño — Superficie de proyecto",
        ],
        label_visibility="collapsed",
    )

    st.button("Abrir visor 3D", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Fila 2: Vuelos | Volúmenes por Periodo | Distribución (donut)
# ---------------------------------------------------------------------------
r2c1, r2c2, r2c3 = st.columns([1.2, 1.7, 1.1], gap="medium")

with r2c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    head_a, head_b = st.columns([1, 1])
    with head_a:
        st.markdown('<div class="card-title">Vuelos y Modelos</div>',
                    unsafe_allow_html=True)
    with head_b:
        st.markdown(
            '<div style="text-align:right;"><a class="link-action">+ Nuevo vuelo</a></div>',
            unsafe_allow_html=True,
        )

    render_flights_table([
        {"fecha": "26 Mayo, 2024", "area": "45.6 ha", "gsd": "2.3 cm"},
        {"fecha": "25 Mayo, 2024", "area": "45.1 ha", "gsd": "2.3 cm"},
        {"fecha": "24 Mayo, 2024", "area": "44.8 ha", "gsd": "2.4 cm"},
        {"fecha": "23 Mayo, 2024", "area": "44.2 ha", "gsd": "2.4 cm"},
        {"fecha": "22 Mayo, 2024", "area": "43.6 ha", "gsd": "2.5 cm"},
    ])
    st.markdown(
        '<div style="margin-top:0.6rem;text-align:center;">'
        '<a class="link-action">Ver todos los vuelos</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with r2c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    th1, th2 = st.columns([2, 1])
    with th1:
        st.markdown('<div class="card-title">Volúmenes por Periodo</div>',
                    unsafe_allow_html=True)
    with th2:
        st.markdown(
            """
            <div style="text-align:right;">
                <div class="segmented">
                    <span class="seg active">Diario</span>
                    <span class="seg">Semanal</span>
                    <span class="seg">Mensual</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    labels = ["20 May", "21 May", "22 May", "23 May", "24 May", "25 May", "26 May"]
    fig = volumes_by_period(
        labels=labels,
        excavacion=[80000, 110000, 90000, 100000, 95000, 105000, 128450],
        terraplen=[55000, 78000, 65000, 70000, 70000, 80000, 96320],
        neto=[25000, 32000, 25000, 30000, 25000, 25000, 32130],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with r2c3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Distribución de Volúmenes</div>',
                unsafe_allow_html=True)
    fig = volumes_donut(excavacion=128450, terraplen=96320, neto=32130)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        """
        <div style="font-size:0.85rem; color:#374151;">
            <div style="display:flex;justify-content:space-between;margin:0.3rem 0;">
                <span>🟠 Excavación</span>
                <span><b>128,450 m²</b> <span style="color:#9ca3af">(57.1%)</span></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin:0.3rem 0;">
                <span>🟢 Terraplén</span>
                <span><b>96,320 m²</b> <span style="color:#9ca3af">(42.9%)</span></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin:0.3rem 0;">
                <span>🔵 Neto</span>
                <span><b>32,130 m³</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Fila 3: Equipos Activos | Rendimientos | Avance por Frente
# ---------------------------------------------------------------------------
r3c1, r3c2, r3c3 = st.columns([1.5, 1.5, 1.2], gap="medium")

with r3c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    he1, he2 = st.columns([1, 1])
    with he1:
        st.markdown('<div class="card-title">Equipos Activos</div>',
                    unsafe_allow_html=True)
    with he2:
        st.markdown(
            '<div style="text-align:right;"><a class="link-action">+ Registrar equipo</a></div>',
            unsafe_allow_html=True,
        )

    render_equipos_table([
        {"equipo": "CAT 336",  "tipo": "Excavadora",     "frente": "Frente A", "horas": "8.2"},
        {"equipo": "CAT D8T",  "tipo": "Bulldozer",      "frente": "Frente A", "horas": "7.5"},
        {"equipo": "CAT 740B", "tipo": "Volqueta",       "frente": "Frente A", "horas": "9.1"},
        {"equipo": "CAT 320",  "tipo": "Excavadora",     "frente": "Frente B", "horas": "8.0"},
        {"equipo": "CAT 140K", "tipo": "Motoniveladora", "frente": "Frente B", "horas": "6.7"},
    ])
    st.markdown(
        '<div style="margin-top:0.6rem;text-align:center;">'
        '<a class="link-action">Ver todos los equipos</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with r3c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Rendimiento de Equipos (Hoy)</div>',
                unsafe_allow_html=True)

    render_rendimientos_table([
        {"equipo": "CAT 336",  "tipo": "Excavadora",
         "produccion": "2,850 m³", "rendimiento": "347 m³/h", "trend": "up"},
        {"equipo": "CAT D8T",  "tipo": "Bulldozer",
         "produccion": "4,200 m³", "rendimiento": "560 m³/h", "trend": "up"},
        {"equipo": "CAT 740B", "tipo": "Volqueta",
         "produccion": "28 viajes", "rendimiento": "186 m³/h", "trend": "up"},
        {"equipo": "CAT 320",  "tipo": "Excavadora",
         "produccion": "2,150 m³", "rendimiento": "269 m³/h", "trend": "down"},
        {"equipo": "CAT 140K", "tipo": "Motoniveladora",
         "produccion": "1.8 ha",   "rendimiento": "0.27 ha/h", "trend": "up"},
    ])
    st.markdown(
        '<div style="margin-top:0.6rem;text-align:center;">'
        '<a class="link-action">Ver detalle de rendimientos</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with r3c3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Avance por Frente</div>',
                unsafe_allow_html=True)
    render_progress_bars([
        ("Frente A - Movimiento de Tierras", 68.3),
        ("Frente B - Movimiento de Tierras", 54.7),
        ("Frente C - Pavimentos",            38.9),
        ("Frente D - Obras Complementarias", 72.1),
    ])
    st.markdown(
        '<div style="margin-top:0.6rem;text-align:center;">'
        '<a class="link-action">Ver todos los frentes</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
