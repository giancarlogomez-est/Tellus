"""CSS global del dashboard Mensure v2.0.

Inyecta una hoja de estilos personalizada que reemplaza la apariencia por
defecto de Streamlit por un look "dashboard SaaS" (cards blancos, sidebar
oscura/clara, tipografías y espaciados consistentes).
"""
import streamlit as st


CSS = """
<style>
/* ===================== Reset / Base ===================== */
.stApp {
    background-color: #f5f7fb;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Ocultar header / footer / menú default de Streamlit */
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
#MainMenu { display: none; }

/* Reducir padding superior */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 100% !important;
}

/* ===================== Sidebar ===================== */
section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
}
section[data-testid="stSidebar"] > div { padding-top: 1rem; }

.sidebar-logo {
    text-align: center;
    padding: 1rem 0 1.5rem 0;
    font-size: 2.2rem;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 1rem;
    margin: 0.15rem 0.75rem;
    border-radius: 8px;
    color: #4b5563;
    font-size: 0.92rem;
    cursor: pointer;
    transition: all 0.15s ease;
}
.nav-item:hover { background-color: #f3f4f6; }
.nav-item.active {
    background-color: #eff6ff;
    color: #2563eb;
    font-weight: 600;
}

.sidebar-project {
    margin: 1rem 0.75rem;
    padding: 0.75rem;
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
}
.sidebar-project .label {
    font-size: 0.72rem;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.sidebar-project .value {
    font-size: 0.92rem;
    color: #111827;
    font-weight: 600;
    margin-top: 0.15rem;
}

.sidebar-user {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0.5rem 0.75rem;
    padding: 0.6rem;
    border-top: 1px solid #e5e7eb;
}
.sidebar-user .avatar {
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg, #60a5fa, #2563eb);
    color: white;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600;
    position: relative;
}
.sidebar-user .avatar::after {
    content: ''; position: absolute;
    bottom: 0; right: 0;
    width: 10px; height: 10px;
    background: #10b981;
    border: 2px solid white;
    border-radius: 50%;
}
.sidebar-user .name { font-weight: 600; color: #111827; font-size: 0.88rem; }
.sidebar-user .role { font-size: 0.75rem; color: #6b7280; }

/* ===================== Header de página ===================== */
.page-header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #111827;
    margin: 0;
}
.page-header .subtitle {
    color: #6b7280;
    font-size: 0.9rem;
    margin-top: 0.1rem;
}

/* ===================== Cards genéricas ===================== */
.card {
    background: #ffffff;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
    border: 1px solid #f3f4f6;
    height: 100%;
}
.card-title {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 1rem;
}

/* ===================== KPI Cards ===================== */
.kpi-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    border: 1px solid #f3f4f6;
    display: flex;
    gap: 0.9rem;
    align-items: flex-start;
}
.kpi-icon {
    width: 44px; height: 44px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
    flex-shrink: 0;
}
.kpi-icon.orange  { background: #fff3e6; color: #f59e0b; }
.kpi-icon.green   { background: #e7f7ee; color: #10b981; }
.kpi-icon.dark    { background: #eef2ff; color: #4338ca; }
.kpi-icon.purple  { background: #f3e8ff; color: #9333ea; }
.kpi-icon.blue    { background: #e0f2fe; color: #0284c7; }
.kpi-icon.indigo  { background: #e0e7ff; color: #4f46e5; }

.kpi-label { font-size: 0.82rem; color: #6b7280; margin-bottom: 0.15rem; }
.kpi-value { font-size: 1.5rem; font-weight: 700; color: #111827; line-height: 1.1; }
.kpi-delta { font-size: 0.78rem; margin-top: 0.35rem; }
.kpi-delta.up   { color: #10b981; }
.kpi-delta.down { color: #ef4444; }
.kpi-delta .muted { color: #9ca3af; margin-left: 0.25rem; }

/* ===================== Tablas estilo dashboard ===================== */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.data-table thead th {
    text-align: left;
    color: #6b7280;
    font-weight: 600;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.6rem 0.5rem;
    border-bottom: 1px solid #f3f4f6;
}
.data-table tbody td {
    padding: 0.7rem 0.5rem;
    border-bottom: 1px solid #f9fafb;
    color: #374151;
}
.data-table tbody tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: #fafafa; }

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
}
.status-badge.ok  { background: #e7f7ee; color: #10b981; }
.status-badge.warn{ background: #fff3e6; color: #f59e0b; }
.status-badge.dot::before {
    content: '●'; font-size: 0.5rem;
}

.trend-up   { color: #10b981; }
.trend-down { color: #ef4444; }

/* ===================== Barras de progreso (Avance por Frente) ===================== */
.progress-row {
    display: flex; justify-content: space-between;
    font-size: 0.88rem; color: #374151; margin-bottom: 0.3rem;
}
.progress-row .pct { font-weight: 600; color: #111827; }
.progress-bar {
    width: 100%; height: 6px;
    background: #f3f4f6;
    border-radius: 999px;
    margin-bottom: 1rem;
    overflow: hidden;
}
.progress-bar .fill {
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #3b82f6, #2563eb);
}

/* ===================== Tabs / segmented control ===================== */
.segmented {
    display: inline-flex;
    background: #f3f4f6;
    border-radius: 8px;
    padding: 3px;
    gap: 2px;
}
.segmented .seg {
    padding: 0.3rem 0.85rem;
    font-size: 0.82rem;
    border-radius: 6px;
    color: #6b7280;
    cursor: pointer;
}
.segmented .seg.active {
    background: white;
    color: #111827;
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

/* ===================== Botones link ===================== */
.link-action {
    color: #2563eb;
    font-size: 0.85rem;
    font-weight: 500;
    text-decoration: none;
}
.link-action:hover { text-decoration: underline; }

/* ===================== Radio de superficies 3D ===================== */
.surface-radio {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.4rem;
    font-size: 0.85rem;
}
.surface-radio.selected {
    background: #eff6ff;
    border-color: #93c5fd;
}
.surface-radio .title { color: #111827; font-weight: 500; }
.surface-radio .meta  { color: #9ca3af; font-size: 0.75rem; }

/* ===================== Overrides Streamlit ===================== */
div[data-testid="stMetricValue"] { font-size: 1.5rem; }
div[data-testid="stDataFrame"] { border: none; }
div[data-baseweb="select"] > div { border-radius: 8px; }
</style>
"""


def inject_css() -> None:
    """Inserta el CSS global. Llamar una sola vez al inicio de cada página."""
    st.markdown(CSS, unsafe_allow_html=True)
