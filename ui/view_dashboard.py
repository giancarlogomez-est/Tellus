"""
Vista Dashboard de Mensure v2.0 — Resumen general del proyecto.

Reproduce el mockup:
    Fila 1: 3 KPIs de volumen + tarjeta Vista 3D (ocupa 2 filas).
    Fila 1b: 3 KPIs (Área, Pavimento, Avance).
    Fila 2: Vuelos y Modelos | Volúmenes por Periodo | Distribución (donut).
    Fila 3: Equipos Activos | Rendimientos | Avance por Frente.

Los KPIs y los gráficos consumen el histórico (data/processed/historico_acumulado.xlsx)
cuando existe; si no, se muestran valores demo coincidentes con la imagen.
"""
from __future__ import annotations

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from . import theme as T
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
    ("CAT 336",  "Excavadora",     "Frente A", "8.2 h"),
    ("CAT D8T",  "Bulldozer",      "Frente A", "7.5 h"),
    ("CAT 740B", "Volqueta",       "Frente A", "9.1 h"),
    ("CAT 320",  "Excavadora",     "Frente B", "8.0 h"),
    ("CAT 140K", "Motoniveladora", "Frente B", "6.7 h"),
]
RENDIMIENTOS_DEMO = [
    ("CAT 336",  "Excavadora",     "2,850 m³",  "347 m³/h",   True),
    ("CAT D8T",  "Bulldozer",      "4,200 m³",  "560 m³/h",   True),
    ("CAT 740B", "Volqueta",       "28 viajes", "186 m³/h",   True),
    ("CAT 320",  "Excavadora",     "2,150 m³",  "269 m³/h",   False),
    ("CAT 140K", "Motoniveladora", "1.8 ha",    "0.27 ha/h",  True),
]
FRENTES_DEMO = [
    ("Frente A - Movimiento de Tierras", 68.3),
    ("Frente B - Movimiento de Tierras", 54.7),
    ("Frente C - Pavimentos",            38.9),
    ("Frente D - Obras Complementarias", 72.1),
]
# Serie demo: 7 días para el gráfico de barras
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
        SectionTitle(title_col, text="Dashboard").pack(anchor="w")
        self.subtitulo = ctk.CTkLabel(
            title_col, text="Resumen general del proyecto",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
        )
        self.subtitulo.pack(anchor="w")

        # Filtros (periodo, frente)
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

        self.kpi_exc  = KPICardIcon(left, "⛏", "orange",
                                      "Volumen Excavación", "—")
        self.kpi_ter  = KPICardIcon(left, "▲", "green",
                                      "Volumen Terraplén", "—")
        self.kpi_net  = KPICardIcon(left, "⚖", "dark",
                                      "Volumen Neto", "—")
        self.kpi_area = KPICardIcon(left, "📐", "purple",
                                      "Área Topografiada", "—")
        self.kpi_pav  = KPICardIcon(left, "🛣", "blue",
                                      "Longitud Pavimento", "—")
        self.kpi_avg  = KPICardIcon(left, "📊", "indigo",
                                      "Avance General", "—",
                                      delta_suffix="vs semana pasada")

        cards = [self.kpi_exc, self.kpi_ter, self.kpi_net,
                 self.kpi_area, self.kpi_pav, self.kpi_avg]
        for i, k in enumerate(cards):
            r, c = divmod(i, 3)
            k.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

        # ── Columna derecha: Vista 3D ───────────────────────────────────
        v3d = Card(top, title="Vista 3D - Comparación de Superficies")
        v3d.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Placeholder (gradiente simulado)
        ph = ctk.CTkFrame(v3d, height=170, corner_radius=8,
                            fg_color="#DBEAFE")
        ph.pack(fill="x", padx=18, pady=(0, 8))
        ph.pack_propagate(False)
        ctk.CTkLabel(ph, text="🏔",
                      font=(T.FONT_FAMILY, 60),
                      text_color="#94A3B8").place(relx=0.5, rely=0.5,
                                                    anchor="center")
        ctk.CTkLabel(ph, text="Cotas (m)   100  120  140  160",
                      font=T.FONT_TINY, fg_color="white",
                      corner_radius=4, text_color=T.TEXT,
                      padx=6, pady=2).place(x=8, rely=1.0,
                                              anchor="sw", y=-8)

        self._surf_var = ctk.StringVar(value="actual")
        radios = ctk.CTkFrame(v3d, fg_color="transparent")
        radios.pack(fill="x", padx=18, pady=(2, 6))
        for val, txt in [("actual",   "Superficie actual"),
                         ("anterior", "Superficie anterior"),
                         ("diseno",   "Diseño")]:
            ctk.CTkRadioButton(
                radios, text=txt, variable=self._surf_var, value=val,
                font=T.FONT_BODY, text_color=T.TEXT,
                fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
                border_color="#D1D5DB",
            ).pack(anchor="w", pady=2)

        ctk.CTkButton(
            v3d, text="Abrir visor 3D",
            fg_color="transparent", border_width=1,
            border_color=T.CARD_BORDER,
            text_color=T.TEXT, hover_color=T.HOVER_BG,
        ).pack(fill="x", padx=18, pady=(4, 14))

    # ── Fila 2: Vuelos | Volúmenes por Periodo | Donut ──────────────────
    def _build_middle_row(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 14))
        row.grid_columnconfigure(0, weight=12, uniform="m")
        row.grid_columnconfigure(1, weight=17, uniform="m")
        row.grid_columnconfigure(2, weight=11, uniform="m")

        # Vuelos y Modelos
        self.card_vuelos = Card(row, title="Vuelos y Modelos",
                                  action_text="+ Nuevo vuelo")
        self.card_vuelos.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.vuelos_holder = ctk.CTkFrame(self.card_vuelos,
                                            fg_color="transparent")
        self.vuelos_holder.pack(fill="both", expand=True,
                                  padx=18, pady=(0, 14))

        # Volúmenes por Periodo
        self.card_bar = Card(row, title="Volúmenes por Periodo")
        self.card_bar.grid(row=0, column=1, sticky="nsew", padx=8)
        self.bar_holder = ctk.CTkFrame(self.card_bar, fg_color="transparent")
        self.bar_holder.pack(fill="both", expand=True,
                              padx=12, pady=(0, 14))

        # Donut
        self.card_donut = Card(row, title="Distribución de Volúmenes")
        self.card_donut.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        self.donut_holder = ctk.CTkFrame(self.card_donut, fg_color="transparent")
        self.donut_holder.pack(fill="both", expand=True,
                                padx=12, pady=(0, 14))

    # ── Fila 3: Equipos | Rendimientos | Frentes ────────────────────────
    def _build_bottom_row(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 20))
        row.grid_columnconfigure(0, weight=15, uniform="b")
        row.grid_columnconfigure(1, weight=15, uniform="b")
        row.grid_columnconfigure(2, weight=12, uniform="b")

        # Equipos Activos
        c_eq = Card(row, title="Equipos Activos",
                     action_text="+ Registrar equipo")
        c_eq.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        eq_tbl = DataTable(
            c_eq, columns=["Equipo", "Tipo", "Frente", "Estado", "Horas hoy"],
            widths=[120, 110, 90, 80, 80],
        )
        eq_tbl.pack(fill="x", padx=18, pady=(0, 14))
        for nombre, tipo, frente, horas in EQUIPOS_DEMO:
            badge = StatusBadge(eq_tbl, "Activo", kind="ok")
            eq_tbl.add_row([nombre, tipo, frente, badge, horas])

        # Rendimientos
        c_re = Card(row, title="Rendimiento de Equipos (Hoy)")
        c_re.grid(row=0, column=1, sticky="nsew", padx=8)
        re_tbl = DataTable(
            c_re, columns=["Equipo", "Tipo", "Producción", "Rendimiento"],
            widths=[110, 110, 100, 110],
        )
        re_tbl.pack(fill="x", padx=18, pady=(0, 14))
        for nombre, tipo, prod, rend, up in RENDIMIENTOS_DEMO:
            arrow = "↗" if up else "↘"
            color = T.SUCCESS if up else T.DANGER
            rend_lbl = ctk.CTkLabel(
                re_tbl, text=f"{rend}  {arrow}", anchor="w",
                font=T.FONT_BODY, text_color=color,
            )
            re_tbl.add_row([nombre, tipo, prod, rend_lbl])

        # Avance por Frente
        c_fr = Card(row, title="Avance por Frente")
        c_fr.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        fr_box = ctk.CTkFrame(c_fr, fg_color="transparent")
        fr_box.pack(fill="x", padx=18, pady=(2, 14))
        for label, pct in FRENTES_DEMO:
            ProgressItem(fr_box, label, pct,
                          color=T.PRIMARY).pack(fill="x")

    # ═══════════════════════════════════════════════════════════════════
    # Refresh — alimenta KPIs y gráficos
    # ═══════════════════════════════════════════════════════════════════
    def refresh(self):
        cfg = self.state.load_config() or {}
        df = self.state.load_history()

        nombre = cfg.get("nombre", "Resumen general del proyecto")
        tramo = cfg.get("tramo", "")
        self.subtitulo.configure(
            text=f"{nombre} · {tramo}" if tramo else nombre,
        )

        # ── KPIs ───────────────────────────────────────────────────────
        if df.empty:
            # Demo (coincide con el mockup)
            self.kpi_exc.set_value("128,450 m³", "↑ 12.5%", True)
            self.kpi_ter.set_value("96,320 m³",  "↑ 8.3%",  True)
            self.kpi_net.set_value("32,130 m³",  "↑ 4.2%",  True)
            self.kpi_area.set_value("45.6 ha",   "↑ 5.1 ha", True)
            self.kpi_pav.set_value("2.45 km",    "↑ 0.18 km", True)
            self.kpi_avg.set_value("62.7%",      "↑ 3.6%",   True)
            self._render_flights_demo()
            self._render_bar_chart_demo()
            self._render_donut(128450, 96320, 32130)
            return

        # Datos reales del histórico
        ult = df.iloc[-1]
        corte = float(ult.get("volumen_corte_dia_m3", 0))
        relleno = float(ult.get("volumen_relleno_dia_m3", 0))
        neto = float(ult.get("volumen_neto_dia_m3", corte - relleno))

        self.kpi_exc.set_value(f"{corte:,.0f} m³",
                                self._delta(df, "volumen_corte_dia_m3"))
        self.kpi_ter.set_value(f"{relleno:,.0f} m³",
                                self._delta(df, "volumen_relleno_dia_m3"))
        self.kpi_net.set_value(f"{neto:,.0f} m³",
                                self._delta(df, "volumen_neto_dia_m3"),
                                delta_up=neto >= 0)
        self.kpi_area.set_value(f"{cfg.get('area_ha', 45.6)} ha",
                                 "↑ —")
        self.kpi_pav.set_value(f"{cfg.get('long_pavimento_km', 2.45)} km",
                                "↑ —")
        obj = cfg.get("vol_corte_objetivo", 0) or 0
        if obj:
            pct = corte / obj * 100
            self.kpi_avg.set_value(f"{pct:.1f}%", "↑ —")
        else:
            self.kpi_avg.set_value("—")

        self._render_flights(df)
        self._render_bar_chart(df)
        self._render_donut(corte, relleno, neto)

    # ── Helpers ─────────────────────────────────────────────────────────
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
            columns=["Fecha", "Neto día", "CRS", "Estado"],
            widths=[110, 90, 60, 90],
        )
        table.pack(fill="x")
        for _, r in df.tail(5).iloc[::-1].iterrows():
            fecha = r["fecha"].strftime("%d %b, %Y")
            neto = f"{r.get('volumen_neto_dia_m3', 0):,.0f} m³"
            crs = f"EPSG:{int(r.get('crs_epsg', 3116))}"
            badge = StatusBadge(table, "Procesado", kind="ok")
            table.add_row([f"✈ {fecha}", neto, crs, badge])
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
        exc = df.get("volumen_corte_dia_m3",
                       df.get("volumen_corte_m3", [0]*len(df))).tolist()
        ter = df.get("volumen_relleno_dia_m3",
                       df.get("volumen_relleno_m3", [0]*len(df))).tolist()
        self._draw_bar_chart(labels, exc, ter)

    def _draw_bar_chart(self, labels, exc, ter):
        self._clear_canvas("bar")

        plt.style.use("default")
        fig = Figure(figsize=(7, 3.2), dpi=100, facecolor=T.CARD_BG)
        self._fig_bar = fig
        ax = fig.add_subplot(111)
        ax.set_facecolor(T.CARD_BG)

        x = range(len(labels))
        ax.bar(x,  exc, color=T.CORTE_COLOR, label="Excavación (m³)", width=0.55)
        ax.bar(x, [-v for v in ter], color=T.RELLENO_COLOR,
                label="Terraplén (m³)", width=0.55)
        neto = [a - b for a, b in zip(exc, ter)]
        ax.plot(x, neto, "-o", color=T.PRIMARY, lw=2, ms=5,
                 mfc=T.PRIMARY, mec="white", label="Neto (m³)")
        ax.axhline(0, color="#E5E7EB", lw=0.6)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8, color="#9CA3AF")
        ax.legend(fontsize=8, frameon=False, loc="upper left",
                   ncol=3, bbox_to_anchor=(0, 1.08))
        ax.grid(axis="y", ls="-", color="#F3F4F6")
        ax.tick_params(colors="#9CA3AF", labelsize=8)
        for s in ax.spines.values():
            s.set_color("#F3F4F6")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.bar_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _render_donut(self, corte: float, relleno: float, neto: float):
        self._clear_canvas("donut")
        total = corte + relleno

        plt.style.use("default")
        fig = Figure(figsize=(4, 3.4), dpi=100, facecolor=T.CARD_BG)
        self._fig_donut = fig
        ax = fig.add_subplot(111)
        ax.set_facecolor(T.CARD_BG)
        ax.pie(
            [max(corte, 0.01), max(relleno, 0.01)],
            colors=[T.CORTE_COLOR, T.RELLENO_COLOR],
            startangle=90, counterclock=False,
            wedgeprops=dict(width=0.32, edgecolor="white"),
        )
        ax.text(0, 0.12, "Volumen Total", ha="center",
                 fontsize=9, color=T.TEXT_MUTED)
        ax.text(0, -0.12, f"{int(total):,} m³", ha="center",
                 fontsize=14, fontweight="bold", color=T.TEXT)
        ax.set(aspect="equal")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.donut_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", expand=False)

        legend = ctk.CTkFrame(self.donut_holder, fg_color="transparent")
        legend.pack(fill="x", pady=(4, 0))
        for color, name, value, pct in [
            (T.CORTE_COLOR, "Excavación", corte,
             corte / total * 100 if total else 0),
            (T.RELLENO_COLOR, "Terraplén", relleno,
             relleno / total * 100 if total else 0),
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
