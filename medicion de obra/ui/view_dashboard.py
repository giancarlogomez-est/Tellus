"""
Vista Dashboard — Resumen general del proyecto (estilo mockup SaaS).

Layout:
    Header     : título + filtros (periodo, frente)
    Fila 1     : 3 KPIs de volumen + tarjeta Vista 3D (ocupa 2 filas).
    Fila 1b    : 3 KPIs (Área, Pavimento, Avance).
    Fila 2     : Vuelos y Modelos | Volúmenes por Período | Distribución (donut)
    Fila 3     : Equipos Activos | Rendimiento de Equipos | Avance por Frente

Si hay registro real (load_registro()), los KPIs y los gráficos lo consumen;
si no, se muestran valores demo que coinciden con la imagen del mockup.
"""
from __future__ import annotations

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from PIL import Image

from . import theme as T
from .basemap import build_overlay
from .state import ProjectState
from .widgets import (
    Card, DataTable, KPICardIcon, ProgressItem,
    SectionTitle, StatusBadge,
)


# ── Datos demo (mockup) ─────────────────────────────────────────────────
VUELOS_DEMO = [
    ("26 May, 2024", "45.6 ha", "2.3 cm"),
    ("25 May, 2024", "45.1 ha", "2.3 cm"),
    ("24 May, 2024", "44.8 ha", "2.4 cm"),
    ("23 May, 2024", "44.2 ha", "2.4 cm"),
    ("22 May, 2024", "43.6 ha", "2.5 cm"),
]
EQUIPOS_DEMO = [
    # nombre, tipo, frente, horas, producción, rendimiento, subió (bool)
    ("CAT 336",  "Excavadora",     "Frente A", "8.2 h", "2,850 m³",  "347 m³/h",  True),
    ("CAT D8T",  "Bulldozer",      "Frente A", "7.5 h", "4,200 m³",  "560 m³/h",  True),
    ("CAT 740B", "Volqueta",       "Frente A", "9.1 h", "28 viajes", "186 m³/h",  True),
    ("CAT 320",  "Excavadora",     "Frente B", "8.0 h", "2,150 m³",  "269 m³/h",  False),
    ("CAT 140K", "Motoniveladora", "Frente B", "6.7 h", "1.8 ha",    "0.27 ha/h", True),
]
FRENTES_DEMO = [
    ("Frente A - Movimiento de Tierras", 68.3),
    ("Frente B - Movimiento de Tierras", 54.7),
    ("Frente C - Pavimentos",            38.9),
    ("Frente D - Obras Complementarias", 72.1),
]
BAR_DEMO_LABELS = ["20 May", "21 May", "22 May", "23 May",
                   "24 May", "25 May", "26 May"]
BAR_DEMO_EXC = [98000, 115000, 105000, 112000, 108000, 118000, 128450]
BAR_DEMO_TER = [74000,  88000,  79000,  85000,  82000,  90000,  96320]


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState):
        super().__init__(master, fg_color=T.APP_BG)
        self.state = state
        self._fig_bar = None
        self._fig_donut = None
        self._build()
        self.refresh()

    # ═══════════════════════════════════════════════════════════════════
    # Construcción del layout
    # ═══════════════════════════════════════════════════════════════════
    def _build(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=T.APP_BG)
        self.scroll.pack(fill="both", expand=True)

        self._build_header()
        self._build_kpi_grid()
        self._build_middle_row()
        self._build_bottom_row()

    # ── Header (título + filtros) ───────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(18, 12))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left", fill="x", expand=True)
        SectionTitle(title_col, text="Dashboard",
                     text_color=T.TEXT).pack(anchor="w")
        self.subtitulo = ctk.CTkLabel(
            title_col, text="Resumen general del proyecto",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
        )
        self.subtitulo.pack(anchor="w")

        # Botón Actualizar
        ctk.CTkButton(
            header, text="↻  Actualizar", width=120, height=32,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK, font=T.FONT_BODY,
            corner_radius=8,
            command=self.refresh,
        ).pack(side="right", padx=(0, 0))

        # Filtros (frente y periodo, en orden visual: [periodo] [frente])
        for opciones in (
            ["Todos los frentes", "Frente A", "Frente B",
             "Frente C", "Frente D"],
            ["20 - 26 Mayo, 2024", "13 - 19 Mayo, 2024", "Mes actual"],
        ):
            ctk.CTkOptionMenu(
                header, values=opciones, width=160,
                fg_color=T.CARD_BG, button_color=T.CARD_BG,
                button_hover_color=T.HOVER_BG, text_color=T.TEXT,
                dropdown_fg_color=T.CARD_BG, dropdown_text_color=T.TEXT,
            ).pack(side="right", padx=(0, 8))

    # ── KPI grid + Vista 3D ─────────────────────────────────────────────
    def _build_kpi_grid(self):
        top = ctk.CTkFrame(self.scroll, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(0, 14))
        top.grid_columnconfigure(0, weight=2, uniform="top")
        top.grid_columnconfigure(1, weight=1, uniform="top")

        # ── Columna izquierda (2 filas × 3 KPIs) ────────────────────────
        left = ctk.CTkFrame(top, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        for c in range(3):
            left.grid_columnconfigure(c, weight=1, uniform="kpi")

        self.kpi_ter  = KPICardIcon(left, "▲", "green",
                                     "Volumen de Llenos", "—")
        self.kpi_exc  = KPICardIcon(left, "▲", "red",
                                     "Volumen de Cortes", "—")
        self.kpi_net  = KPICardIcon(left, "⚖", "dark",
                                     "Volumen Neto", "—")
        self.kpi_area = KPICardIcon(left, "📐", "purple",
                                     "Área Topografiada", "—")
        self.kpi_pav  = KPICardIcon(left, "🛣", "blue",
                                     "Longitud Pavimento", "—")
        self.kpi_avg  = KPICardIcon(left, "📊", "indigo",
                                     "Avance General", "—",
                                     delta_suffix="vs semana pasada")

        cards = [self.kpi_ter, self.kpi_exc, self.kpi_net,
                 self.kpi_area, self.kpi_pav, self.kpi_avg]
        for i, k in enumerate(cards):
            r, c = divmod(i, 3)
            k.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

        # ── Columna derecha: Vista 3D ───────────────────────────────────
        v3d = Card(top, title="Vista 3D - Comparación de Superficies",
                   light=True)
        v3d.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Basemap: hillshade del DEM + heatmap de cortes/llenos del vuelo
        self.v3d_holder = ctk.CTkFrame(v3d, height=190, corner_radius=8,
                                       fg_color=T.HOVER_BG)
        self.v3d_holder.pack(fill="x", padx=18, pady=(0, 4))
        self.v3d_holder.pack_propagate(False)
        self._v3d_img = None
        self.v3d_caption = ctk.CTkLabel(
            v3d, text="Rojo = corte · Verde = relleno",
            font=T.FONT_TINY, text_color=T.TEXT_MUTED)
        self.v3d_caption.pack(anchor="w", padx=18, pady=(0, 6))

        self._surf_var = ctk.StringVar(value="actual")
        radios = ctk.CTkFrame(v3d, fg_color="transparent")
        radios.pack(fill="x", padx=18, pady=(2, 6))
        for val, txt, sub in [
            ("actual",   "Superficie actual",   "26 Mayo, 2024"),
            ("anterior", "Superficie anterior", "25 Mayo, 2024"),
            ("diseno",   "Diseño",              "Superficie de proyecto"),
        ]:
            item = ctk.CTkFrame(radios, fg_color="transparent")
            item.pack(anchor="w", fill="x", pady=2)
            ctk.CTkRadioButton(
                item, text=txt, variable=self._surf_var, value=val,
                font=T.FONT_BODY, text_color=T.TEXT,
                fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
                border_color="#D1D5DB",
            ).pack(anchor="w")
            ctk.CTkLabel(
                item, text=sub, font=T.FONT_TINY,
                text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", padx=(26, 0))

        ctk.CTkButton(
            v3d, text="Abrir visor 3D",
            fg_color="transparent", border_width=1,
            border_color=T.CARD_BORDER,
            text_color=T.TEXT, hover_color=T.HOVER_BG,
        ).pack(fill="x", padx=18, pady=(4, 14))

    # ── Fila 2: Vuelos | Volúmenes por Período | Donut ──────────────────
    def _build_middle_row(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 14))
        row.grid_columnconfigure(0, weight=12, uniform="m")
        row.grid_columnconfigure(1, weight=17, uniform="m")
        row.grid_columnconfigure(2, weight=11, uniform="m")

        # Vuelos y Modelos
        self.card_vuelos = Card(row, title="Vuelos y Modelos",
                                action_text="+ Nuevo vuelo", light=True)
        self.card_vuelos.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.vuelos_holder = ctk.CTkFrame(self.card_vuelos,
                                          fg_color="transparent")
        self.vuelos_holder.pack(fill="both", expand=True,
                                padx=18, pady=(0, 14))

        # Volúmenes por Período
        self.card_bar = Card(row, title="Volúmenes por Período", light=True)
        self.card_bar.grid(row=0, column=1, sticky="nsew", padx=8)

        tabs = ctk.CTkFrame(self.card_bar, fg_color="transparent")
        tabs.pack(fill="x", padx=18, pady=(0, 4))
        self._bar_period = ctk.StringVar(value="Diario")
        ctk.CTkSegmentedButton(
            tabs, values=["Diario", "Semanal", "Mensual"],
            variable=self._bar_period,
            font=T.FONT_SMALL,
            fg_color=T.HOVER_BG, selected_color=T.CARD_BG,
            selected_hover_color=T.CARD_BG, unselected_color=T.HOVER_BG,
            unselected_hover_color=T.CARD_BORDER,
            text_color=T.TEXT, text_color_disabled=T.TEXT_MUTED,
            corner_radius=6, height=26,
        ).pack(side="right")

        self.bar_holder = ctk.CTkFrame(self.card_bar, fg_color="transparent")
        self.bar_holder.pack(fill="both", expand=True,
                             padx=12, pady=(0, 14))

        # Donut
        self.card_donut = Card(row, title="Distribución de Volúmenes",
                               light=True)
        self.card_donut.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        self.donut_holder = ctk.CTkFrame(self.card_donut,
                                         fg_color="transparent")
        self.donut_holder.pack(fill="both", expand=True,
                               padx=12, pady=(0, 14))

    # ── Fila 3: Equipos + Rendimientos (unificado) | Frentes ────────────
    def _build_bottom_row(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 20))
        row.grid_columnconfigure(0, weight=28, uniform="b")
        row.grid_columnconfigure(1, weight=12, uniform="b")

        # Tabla unificada equipos + rendimiento
        self.c_eq = Card(
            row, title="Equipos y Rendimiento (Hoy)",
            action_text="→ Ver detalle",
            light=True,
        )
        self.c_eq.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.eq_holder = ctk.CTkFrame(self.c_eq, fg_color="transparent")
        self.eq_holder.pack(fill="x", padx=18, pady=(0, 14))

        # Avance por Frente
        c_fr = Card(row, title="Avance por Frente", light=True)
        c_fr.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        fr_box = ctk.CTkFrame(c_fr, fg_color="transparent")
        fr_box.pack(fill="x", padx=18, pady=(2, 4))
        for label, pct in FRENTES_DEMO:
            ProgressItem(fr_box, label, pct,
                         color=T.PRIMARY).pack(fill="x")
        ctk.CTkButton(
            c_fr, text="Ver todos los frentes",
            fg_color="transparent", text_color=T.PRIMARY,
            hover_color=T.HOVER_BG, font=T.FONT_SMALL,
        ).pack(pady=(0, 12))

    # ═══════════════════════════════════════════════════════════════════
    # Refresh — alimenta KPIs y gráficos
    # ═══════════════════════════════════════════════════════════════════
    def refresh(self):
        cfg = self.state.load_config() or {}
        df = self._load_history_safe()

        nombre = cfg.get("nombre", "Resumen general del proyecto")
        tramo = cfg.get("tramo", "")
        self.subtitulo.configure(
            text=f"{nombre} · {tramo}" if tramo else nombre,
        )

        if df.empty:
            # Demo (coincide con el mockup)
            self.kpi_ter.set_value("96,320 m³",   "↑ 8.3%",  True)
            self.kpi_exc.set_value("128,450 m³",  "↑ 12.5%", False)
            self.kpi_net.set_value("-32,130 m³",  "↑ 4.2%",  True)
            self.kpi_area.set_value("45.6 ha",    "↑ 5.1 ha", True)
            self.kpi_pav.set_value("2.45 km",     "↑ 0.18 km", True)
            self.kpi_avg.set_value("62.7%",       "↑ 3.6%",   True,
                                   delta_suffix="vs semana pasada")
            self._render_flights_demo()
            self._render_bar_chart_demo()
            self._render_donut(128450, 96320, -32130)
            self._render_basemap(None)
            self._render_equipos_real()
            return

        # Datos reales del registro
        ult = df.iloc[-1]
        corte = float(ult.get("vol_corte_dia", 0))
        relleno = float(ult.get("vol_relleno_dia", 0))
        neto = corte - relleno

        self.kpi_ter.set_value(f"{relleno:,.0f} m³",
                               self._delta(df, "vol_relleno_dia"))
        self.kpi_exc.set_value(f"{corte:,.0f} m³",
                               self._delta(df, "vol_corte_dia"),
                               delta_up=False)
        self.kpi_net.set_value(f"{neto:,.0f} m³",
                               "↑ 0.0%", delta_up=neto >= 0)
        self.kpi_area.set_value(f"{cfg.get('area_ha', 45.6)} ha",
                                "↑ —")
        self.kpi_pav.set_value(f"{cfg.get('long_pavimento_km', 2.45)} km",
                               "↑ —")
        obj = cfg.get("vol_corte_objetivo", 0) or 0
        if obj:
            pct = float(ult.get("vol_corte_acum", 0)) / obj * 100
            self.kpi_avg.set_value(f"{pct:.1f}%", "↑ —",
                                    delta_suffix="vs semana pasada")
        else:
            self.kpi_avg.set_value("—",
                                    delta_suffix="vs semana pasada")

        self._render_flights(df)
        self._render_bar_chart(df)
        self._render_donut(corte, relleno, neto)
        self._render_basemap(ult["fecha"].strftime("%Y-%m-%d"))
        self._render_equipos_real()

    # ── Basemap (hillshade + heatmap cortes/llenos) ─────────────────────
    def _render_basemap(self, fecha):
        holder = getattr(self, "v3d_holder", None)
        if holder is None:
            return
        for w in holder.winfo_children():
            w.destroy()

        dz_path = self.state.dz_dia_path(fecha) if fecha else None
        if dz_path is None:
            dz_path = self.state.ultimo_dz_dia()
        dem_path = self.state.dem_baseline_path()

        img = build_overlay(dem_path, dz_path) if dz_path else None
        if img is None:
            self._v3d_img = None
            ctk.CTkLabel(
                holder, text="Sin datos de cortes/llenos para mostrar",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        holder.update_idletasks()
        avail_w = max(holder.winfo_width() - 4, 360)
        avail_h = max(holder.winfo_height() - 4, 150)
        ratio = min(avail_w / img.width, avail_h / img.height)
        size = (max(int(img.width * ratio), 120),
                max(int(img.height * ratio), 60))
        self._v3d_img = ctk.CTkImage(light_image=img, dark_image=img,
                                     size=size)
        ctk.CTkLabel(holder, image=self._v3d_img, text="").place(
            relx=0.5, rely=0.5, anchor="center")

    # ── Helpers ─────────────────────────────────────────────────────────
    def _load_history_safe(self):
        """Devuelve el registro si existe; DataFrame vacío en caso contrario."""
        try:
            return self.state.load_registro()
        except Exception:
            import pandas as pd
            return pd.DataFrame()

    def _delta(self, df, col: str) -> str:
        if col not in df.columns or len(df) < 2:
            return ""
        prev = float(df.iloc[-2][col]) or 1e-9
        curr = float(df.iloc[-1][col])
        return f"↑ {(curr - prev) / prev * 100:+.1f}%"

    def _render_flights_demo(self):
        for w in self.vuelos_holder.winfo_children():
            w.destroy()
        table = DataTable(
            self.vuelos_holder,
            columns=["Fecha", "Área", "GSD", "Estado"],
            widths=[110, 70, 60, 90],
        )
        table.pack(fill="x")
        for fecha, area, gsd in VUELOS_DEMO:
            badge = StatusBadge(table, "Procesado", kind="ok")
            table.add_row([f"✈ {fecha}", area, gsd, badge])
        ctk.CTkButton(
            self.vuelos_holder, text="Ver todos los vuelos",
            fg_color="transparent", text_color=T.PRIMARY,
            hover_color=T.HOVER_BG, font=T.FONT_SMALL,
        ).pack(pady=(8, 0))

    def _render_flights(self, df):
        for w in self.vuelos_holder.winfo_children():
            w.destroy()
        table = DataTable(
            self.vuelos_holder,
            columns=["Fecha", "Vuelo", "Corte día", "Estado"],
            widths=[110, 60, 100, 90],
        )
        table.pack(fill="x")
        for _, r in df.tail(5).iloc[::-1].iterrows():
            fecha = r["fecha"].strftime("%d %b, %Y")
            vuelo = f"#{int(r.get('vuelo_num', 0))}"
            corte = f"{r.get('vol_corte_dia', 0):,.0f} m³"
            badge = StatusBadge(table, "Procesado", kind="ok")
            table.add_row([f"✈ {fecha}", vuelo, corte, badge])
        ctk.CTkButton(
            self.vuelos_holder, text="Ver todos los vuelos",
            fg_color="transparent", text_color=T.PRIMARY,
            hover_color=T.HOVER_BG, font=T.FONT_SMALL,
        ).pack(pady=(8, 0))

    def _render_bar_chart_demo(self):
        self._draw_bar_chart(BAR_DEMO_LABELS, BAR_DEMO_EXC, BAR_DEMO_TER)

    def _render_bar_chart(self, df):
        df = df.tail(7)
        labels = [f.strftime("%d %b") for f in df["fecha"]]
        exc = df["vol_corte_dia"].tolist() if "vol_corte_dia" in df else [0]*len(df)
        ter = df["vol_relleno_dia"].tolist() if "vol_relleno_dia" in df else [0]*len(df)
        self._draw_bar_chart(labels, exc, ter)

    def _draw_bar_chart(self, labels, exc, ter):
        self._clear_canvas("bar")

        plt.style.use("default")
        bg = T.mc(T.CARD_BG); axis = T.mc(T.AXIS_FG); grid = T.mc(T.GRID_COLOR)
        fig = Figure(figsize=(7, 3.2), dpi=100, facecolor=bg)
        self._fig_bar = fig
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        x = range(len(labels))
        ax.bar(x,  exc, color=T.CORTE_COLOR, label="Cortes (m³)", width=0.55)
        ax.bar(x, [-v for v in ter], color=T.RELLENO_COLOR,
               label="Llenos (m³)", width=0.55)
        neto = [a - b for a, b in zip(exc, ter)]
        ax.plot(x, neto, "-o", color=T.PRIMARY, lw=2, ms=5,
                mfc=T.PRIMARY, mec=bg, label="Neto (m³)")
        ax.axhline(0, color=grid, lw=0.6)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8, color=axis)
        ax.legend(fontsize=8, frameon=False, loc="upper left",
                  ncol=3, bbox_to_anchor=(0, 1.08), labelcolor=axis)
        ax.grid(axis="y", ls="-", color=grid)
        ax.tick_params(colors=axis, labelsize=8)
        for s in ax.spines.values():
            s.set_color(grid)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.bar_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _render_donut(self, corte: float, relleno: float, neto: float):
        self._clear_canvas("donut")
        total = abs(corte) + abs(relleno)

        plt.style.use("default")
        bg = T.mc(T.CARD_BG)
        fig = Figure(figsize=(4, 3.4), dpi=100, facecolor=bg)
        self._fig_donut = fig
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)
        ax.pie(
            [max(abs(corte), 0.01), max(abs(relleno), 0.01)],
            colors=[T.CORTE_COLOR, T.RELLENO_COLOR],
            startangle=90, counterclock=False,
            wedgeprops=dict(width=0.32, edgecolor=bg),
        )
        ax.text(0, 0.12, "Volumen Total", ha="center",
                fontsize=9, color=T.mc(T.TEXT_MUTED))
        ax.text(0, -0.12, f"{int(total):,} m³", ha="center",
                fontsize=14, fontweight="bold", color=T.mc(T.TEXT))
        ax.set(aspect="equal")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.donut_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", expand=False)

        legend = ctk.CTkFrame(self.donut_holder, fg_color="transparent")
        legend.pack(fill="x", pady=(4, 0))
        for color, name, value, pct in [
            (T.CORTE_COLOR, "Cortes", corte,
             abs(corte) / total * 100 if total else 0),
            (T.RELLENO_COLOR, "Llenos", relleno,
             abs(relleno) / total * 100 if total else 0),
            (T.PRIMARY, "Neto", neto, None),
        ]:
            r = ctk.CTkFrame(legend, fg_color="transparent")
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text="●", text_color=color,
                         font=(T.FONT_FAMILY, 12, "bold")).pack(side="left")
            ctk.CTkLabel(r, text=f" {name}", font=T.FONT_BODY,
                         text_color=T.TEXT).pack(side="left")
            txt = f"{value:,.0f} m³"
            if pct is not None:
                txt += f"  ({pct:.1f}%)"
            ctk.CTkLabel(r, text=txt, font=T.FONT_SMALL,
                         text_color=T.TEXT_MUTED).pack(side="right")

    def _clear_canvas(self, which: str):
        target, fig = (
            (self.bar_holder, self._fig_bar) if which == "bar"
            else (self.donut_holder, self._fig_donut)
        )
        if fig is not None:
            try: plt.close(fig)
            except Exception: pass
            if which == "bar": self._fig_bar = None
            else: self._fig_donut = None
        for w in target.winfo_children():
            w.destroy()

    # ── Tabla unificada de equipos (demo) ────────────────────────────────
    def _render_equipos_demo(self):
        for w in self.eq_holder.winfo_children():
            w.destroy()
        tbl = DataTable(
            self.eq_holder,
            columns=["Equipo", "Tipo", "Frente", "Estado",
                     "Horas", "Producción", "Rendimiento"],
            widths=[110, 110, 90, 80, 70, 90, 100],
        )
        tbl.pack(fill="x")
        for nombre, tipo, frente, horas, prod, rend, up in EQUIPOS_DEMO:
            arrow = "↗" if up else "↘"
            color = T.SUCCESS if up else T.DANGER
            rend_lbl = ctk.CTkLabel(
                tbl, text=f"{rend}  {arrow}", anchor="w",
                font=T.FONT_BODY, text_color=color,
            )
            badge = StatusBadge(tbl, "Activo", kind="ok")
            tbl.add_row([nombre, tipo, frente, badge, horas, prod, rend_lbl])

    # ── Tabla unificada de equipos (datos reales) ────────────────────────
    def _render_equipos_real(self):
        for w in self.eq_holder.winfo_children():
            w.destroy()

        try:
            import pandas as pd
            equipos_data = self.state.load_equipos_data()
            df_reg = self.state.load_registros_equipos()
        except Exception:
            self._render_equipos_demo()
            return

        equipos_list = equipos_data.get("equipos", [])
        flotas = equipos_data.get("flotas", [])

        # Si no hay equipos registrados, mostrar demo
        if not equipos_list:
            self._render_equipos_demo()
            return

        # Mapa equipo_id → flota
        eq_to_flota: dict[str, dict] = {}
        for fl in flotas:
            for eid in fl.get("equipo_ids", []):
                eq_to_flota[eid] = fl

        # Último registro diario por equipo (si existe)
        latest_reg: dict[str, dict] = {}
        prev_rend: dict[str, float] = {}
        if not df_reg.empty:
            latest_date = df_reg["fecha"].max()
            for _, r in df_reg[df_reg["fecha"] == latest_date].iterrows():
                latest_reg[r["equipo_id"]] = r.to_dict()
            for _, r in df_reg[df_reg["fecha"] < latest_date].sort_values("fecha").iterrows():
                prev_rend[r["equipo_id"]] = float(r.get("rendimiento", 0) or 0)

        tbl = DataTable(
            self.eq_holder,
            columns=["Equipo", "Tipo", "Flota", "Estado",
                     "Horas", "Producción", "Rendimiento", "vs Ayer"],
            widths=[110, 100, 110, 80, 65, 90, 100, 90],
        )
        tbl.pack(fill="x")

        for eq in equipos_list:
            eid = eq["id"]
            fl = eq_to_flota.get(eid)
            flota_name = fl["nombre"] if fl else "Sin flota"
            u = eq.get("unidad_produccion", "m³")

            rec = latest_reg.get(eid)
            if rec:
                horas_val = rec.get("horas_trabajadas")
                prod_val  = rec.get("produccion")
                rend_val  = rec.get("rendimiento")
                horas_str = f"{horas_val:.1f} h" if pd.notna(horas_val) else "—"
                prod_str  = f"{prod_val:,.1f} {u}" if pd.notna(prod_val) else "—"
                rend_str  = f"{rend_val:.2f} {u}/h" if pd.notna(rend_val) else "—"
            else:
                horas_str = "—"
                prod_str  = "—"
                rend_str  = "—"
                rend_val  = None

            prev = prev_rend.get(eid)
            if prev and rend_val is not None and pd.notna(rend_val) and prev != 0:
                var = (float(rend_val) - prev) / abs(prev) * 100
                up = var >= 0
                arrow = "↗" if up else "↘"
                vs_lbl = ctk.CTkLabel(
                    tbl, text=f"{arrow} {abs(var):.1f}%",
                    font=T.FONT_BODY,
                    text_color=T.SUCCESS if up else T.DANGER,
                    anchor="w",
                )
            else:
                vs_lbl = ctk.CTkLabel(tbl, text="—", font=T.FONT_BODY,
                                      text_color=T.TEXT_MUTED, anchor="w")

            badge = StatusBadge(tbl, "Activo", kind="ok")
            tbl.add_row([
                eq.get("nombre", ""), eq.get("tipo", ""),
                flota_name, badge,
                horas_str, prod_str, rend_str, vs_lbl,
            ])
