"""Sidebar de navegación principal de Mensure v2.0."""
import streamlit as st


NAV_ITEMS = [
    ("Dashboard",     "🏠", "dashboard"),
    ("Vuelos",        "✈️", "vuelos"),
    ("Modelos DEM",   "🗺️", "dem"),
    ("Volúmenes",     "📐", "volumenes"),
    ("Equipos",       "🚜", "equipos"),
    ("Rendimientos", "📈", "rendimientos"),
    ("Reportes",      "📄", "reportes"),
    ("Configuración", "⚙️", "config"),
]


def render_sidebar(active: str = "dashboard") -> str:
    """
    Pinta la sidebar y devuelve la key del item seleccionado.

    Para mantener fidelidad visual con el mockup, usamos st.radio invisible
    (oculto vía CSS) y mostramos badges HTML; en una versión multipágina real
    bastaría con dejar que Streamlit gestione los pages.
    """
    with st.sidebar:
        # Logo
        st.markdown(
            '<div class="sidebar-logo">🛸</div>',
            unsafe_allow_html=True,
        )

        # Items de navegación (botones para que sean clicables)
        selected = active
        for label, icon, key in NAV_ITEMS:
            is_active = (key == active)
            css_class = "nav-item active" if is_active else "nav-item"
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                selected = key

        # Selector de proyecto
        st.markdown(
            """
            <div class="sidebar-project">
                <div class="label">Proyecto</div>
                <div class="value">Proyecto Central ⌄</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Usuario
        st.markdown(
            """
            <div class="sidebar-user">
                <div class="avatar">JP</div>
                <div>
                    <div class="name">Juan Pérez</div>
                    <div class="role">Administrador</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected
