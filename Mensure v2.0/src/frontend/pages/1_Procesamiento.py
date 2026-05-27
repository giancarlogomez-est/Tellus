"""
Página: Procesamiento de jornada (carga DEM + maquinaria + reporte).

Mantiene el pipeline funcional original: ingresa los DEMs y el registro
diario de maquinaria, ejecuta el backend y descarga el Excel.
El Dashboard principal sólo muestra el resumen visual.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from config.settings import (
    COMMON_CRS, HISTORY_FILE, MACHINERY_TYPES,
    PAVEMENT_LAYERS_DEFAULT, REPORTS_DIR,
)
from src.backend.raster_processor import (
    cut_fill_volume, load_raster, pavement_layer_volume,
)
from src.backend.machinery import (
    build_machinery_dataframe, compute_yields, fleet_summary,
)
from src.backend.excel_export import export_report
from src.frontend.styles import inject_css


st.set_page_config(page_title="Procesamiento — Mensure v2.0",
                   page_icon="⚙️", layout="wide")
inject_css()

if "records" not in st.session_state:
    st.session_state.records = []
if "results" not in st.session_state:
    st.session_state.results = None
if "report_buffer" not in st.session_state:
    st.session_state.report_buffer = None


st.markdown(
    """
    <div class="page-header">
        <h1>Procesamiento de Jornada</h1>
        <div class="subtitle">Carga DEMs, registra maquinaria y genera el reporte Excel</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Configuración CRS / fecha
# ---------------------------------------------------------------------------
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    fecha_jornada = st.date_input("Fecha de la jornada", value=date.today())
with c2:
    crs_label = st.selectbox("CRS predefinido", list(COMMON_CRS.keys()))
with c3:
    epsg_code = st.number_input(
        "EPSG personalizado",
        min_value=1000, max_value=999999,
        value=COMMON_CRS[crs_label], step=1,
    )


# ---------------------------------------------------------------------------
# Carga de DEMs
# ---------------------------------------------------------------------------
st.subheader("1. Carga de DEMs (GeoTIFF)")
u1, u2, u3 = st.columns(3)
with u1:
    dem_natural = st.file_uploader("Terreno Natural", type=["tif", "tiff"])
with u2:
    dem_diseno = st.file_uploader("Superficie de Diseño", type=["tif", "tiff"])
with u3:
    dem_avance = st.file_uploader("Avance Diario", type=["tif", "tiff"])


# ---------------------------------------------------------------------------
# Pavimentos
# ---------------------------------------------------------------------------
st.subheader("2. Capas de pavimento (opcional)")
incluir_pavimentos = st.checkbox("Calcular volúmenes de pavimento")
if incluir_pavimentos:
    pavement_df_input = st.data_editor(
        pd.DataFrame(
            [{"capa": k, "espesor_m": v} for k, v in PAVEMENT_LAYERS_DEFAULT.items()]
        ),
        num_rows="dynamic", use_container_width=True,
    )
else:
    pavement_df_input = None


# ---------------------------------------------------------------------------
# Maquinaria
# ---------------------------------------------------------------------------
st.subheader("3. Registro de maquinaria")
with st.form("form_maquinaria", clear_on_submit=True):
    f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
    with f1: tipo = st.selectbox("Tipo", MACHINERY_TYPES)
    with f2: id_equipo = st.text_input("ID del equipo")
    with f3: horas = st.number_input("Horas", 0.0, 24.0, 8.0, 0.5)
    with f4:
        st.write(""); st.write("")
        if st.form_submit_button("➕ Agregar", use_container_width=True):
            if id_equipo.strip():
                st.session_state.records.append({
                    "fecha": fecha_jornada.isoformat(),
                    "tipo": tipo,
                    "id_equipo": id_equipo.strip().upper(),
                    "horas": float(horas),
                })

if st.session_state.records:
    edited = st.data_editor(
        pd.DataFrame(st.session_state.records),
        num_rows="dynamic", use_container_width=True,
    )
    st.session_state.records = edited.to_dict("records")
    if st.button("🗑️ Limpiar registros"):
        st.session_state.records = []
        st.rerun()


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------
st.subheader("4. Ejecutar cálculo")
listo = bool(dem_natural and dem_avance and st.session_state.records)
if not listo:
    st.warning("Carga Terreno Natural + Avance Diario y registra al menos un equipo.")

if st.button("🚀 Procesar jornada", type="primary", disabled=not listo):
    with st.spinner("Procesando..."):
        rd_nat = load_raster(dem_natural, int(epsg_code))
        rd_avc = load_raster(dem_avance, int(epsg_code))
        rd_dis = load_raster(dem_diseno, int(epsg_code)) if dem_diseno else None

        cut_fill = cut_fill_volume(rd_nat, rd_avc)
        volumen_dia = abs(cut_fill["volumen_neto_m3"])

        pavement_results = None
        if incluir_pavimentos and rd_dis is not None and pavement_df_input is not None:
            pavement_results = {}
            for _, row in pavement_df_input.iterrows():
                if pd.notna(row["capa"]) and pd.notna(row["espesor_m"]):
                    pavement_results[str(row["capa"])] = pavement_layer_volume(
                        rd_avc, rd_dis, float(row["espesor_m"])
                    )

        mach_df = build_machinery_dataframe(st.session_state.records)
        yields_df = compute_yields(mach_df, volumen_dia)
        fleet_df = fleet_summary(yields_df)

        st.session_state.results = {
            "cut_fill": cut_fill, "yields_df": yields_df,
            "fleet_df": fleet_df, "pavement_results": pavement_results,
            "epsg": int(epsg_code), "fecha": fecha_jornada,
        }
        st.success("Cálculo completado ✅")


# ---------------------------------------------------------------------------
# Resultados + descarga
# ---------------------------------------------------------------------------
if st.session_state.results:
    res = st.session_state.results
    st.subheader("5. Resultados")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Corte (m³)",   f"{res['cut_fill']['volumen_corte_m3']:,.1f}")
    k2.metric("Relleno (m³)", f"{res['cut_fill']['volumen_relleno_m3']:,.1f}")
    k3.metric("Neto (m³)",    f"{res['cut_fill']['volumen_neto_m3']:,.1f}")
    k4.metric("Esp. prom (m)", f"{res['cut_fill']['espesor_promedio_m']:.3f}")

    st.dataframe(res["yields_df"], use_container_width=True)

    if st.button("Generar Excel"):
        path = REPORTS_DIR / f"Mensure_{res['fecha'].isoformat()}.xlsx"
        buf = export_report(
            output_path=path, history_path=HISTORY_FILE,
            fecha=res["fecha"], crs_epsg=res["epsg"],
            cut_fill=res["cut_fill"], yields_df=res["yields_df"],
            fleet_df=res["fleet_df"], pavement_results=res["pavement_results"],
        )
        st.session_state.report_buffer = buf.getvalue()
        st.session_state.report_filename = path.name

    if st.session_state.report_buffer:
        st.download_button(
            "⬇️ Descargar Reporte",
            data=st.session_state.report_buffer,
            file_name=st.session_state.get("report_filename", "reporte.xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
