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
from .state import ProjectState
from .widgets import (
    Card, DataTable, KPICardIcon, ProgressItem,
    SectionTitle, StatusBadge,
)


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState, navigate=None):
        super().__init__(master, fg_color=T.APP_BG)
        self.state = state
        self._navigate = navigate or (lambda key: None)
        self._fig_bar = None
        self._fig_donut = None
        self._fig_perfil = None
        self._df_history = None
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
        self._build_perfil_row()
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
        sub_row = ctk.CTkFrame(title_col, fg_color="transparent")
        sub_row.pack(anchor="w", fill="x")
        self.subtitulo = ctk.CTkLabel(
            sub_row, text="Resumen general del proyecto",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
        )
        self.subtitulo.pack(side="left")
        self.fecha_ref_badge = ctk.CTkLabel(
            sub_row, text="",
            font=T.FONT_SMALL, text_color=T.TEXT_ON_DARK,
            fg_color=T.PRIMARY, corner_radius=6,
            padx=8, pady=2,
        )

        # Botón Actualizar
        ctk.CTkButton(
            header, text="↻  Actualizar", width=120, height=32,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK, font=T.FONT_BODY,
            corner_radius=8,
            command=self.refresh,
        ).pack(side="right", padx=(0, 0))


    # ── KPI grid ────────────────────────────────────────────────────────
    def _build_kpi_grid(self):
        top = ctk.CTkFrame(self.scroll, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(0, 14))
        for c in range(3):
            top.grid_columnconfigure(c, weight=1, uniform="kpi")

        self.kpi_ter  = KPICardIcon(top, "▲", "green",
                                     "Volumen de Llenos", "—")
        self.kpi_exc  = KPICardIcon(top, "▲", "red",
                                     "Volumen de Cortes", "—")
        self.kpi_avg  = KPICardIcon(top, "📊", "indigo",
                                     "Avance General", "—",
                                     delta_suffix="vs semana pasada")

        for c, k in enumerate([self.kpi_ter, self.kpi_exc, self.kpi_avg]):
            k.grid(row=0, column=c, sticky="nsew", padx=4, pady=4)

    # ── Perfil de abscisas (full-width) ─────────────────────────────────
    def _build_perfil_row(self):
        self.card_perfil = Card(self.scroll, title="Perfil de Corte / Relleno por Abscisa",
                                light=True)
        self.card_perfil.pack(fill="x", padx=20, pady=(0, 14))
        self.perfil_holder = ctk.CTkFrame(self.card_perfil, fg_color="transparent")
        self.perfil_holder.pack(fill="both", expand=True, padx=12, pady=(0, 14))

    # ── Fila 2: Vuelos | Volúmenes por Período | Donut ──────────────────
    def _build_middle_row(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 14))
        row.grid_columnconfigure(0, weight=12, uniform="m")
        row.grid_columnconfigure(1, weight=17, uniform="m")
        row.grid_columnconfigure(2, weight=11, uniform="m")

        # Vuelos y Modelos
        self.card_vuelos = Card(row, title="Vuelos y Modelos",
                                action_text="+ Nuevo vuelo", light=True,
                                action_cmd=lambda: self._navigate("diario"))
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
            command=self._on_bar_period_change,
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
            action_cmd=lambda: self._navigate("equipos"),
            light=True,
        )
        self.c_eq.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.eq_holder = ctk.CTkFrame(self.c_eq, fg_color="transparent")
        self.eq_holder.pack(fill="x", padx=18, pady=(0, 14))

        # Volumen por Frente
        c_fr = Card(row, title="Volumen por Frente", light=True)
        c_fr.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.fr_box = ctk.CTkFrame(c_fr, fg_color="transparent")
        self.fr_box.pack(fill="x", padx=18, pady=(2, 4))
        ctk.CTkButton(
            c_fr, text="Ver todos los frentes",
            fg_color="transparent", text_color=T.PRIMARY,
            hover_color=T.HOVER_BG, font=T.FONT_SMALL,
            command=lambda: self._navigate("dron"),
        ).pack(pady=(0, 12))

    # ═══════════════════════════════════════════════════════════════════
    # Refresh — alimenta KPIs y gráficos
    # ═══════════════════════════════════════════════════════════════════
    def refresh(self):
        cfg = self.state.load_config() or {}
        df = self._load_history_safe()
        self._df_history = df

        nombre = cfg.get("nombre", "Resumen general del proyecto")
        tramo = cfg.get("tramo", "")
        self.subtitulo.configure(
            text=f"{nombre} · {tramo}" if tramo else nombre,
        )

        # Longitud y área calculadas desde frentes + configuración del corredor
        frentes_cfg = self.state.load_frentes()
        long_str = "—"
        area_str = "—"
        if frentes_cfg:
            total_long_m = sum(
                float(f.get("abs_fin", 0)) - float(f.get("abs_ini", 0))
                for f in frentes_cfg
            )
            if total_long_m > 0:
                long_str = f"{total_long_m / 1000:.2f} km"
                ancho = float(cfg.get("ancho_corredor", 0))
                if ancho > 0:
                    area_ha = (total_long_m * 2 * ancho) / 10_000
                    area_str = f"{area_ha:.1f} ha"

        if df.empty:
            # Fallback: usar frentes_resultado TOTAL si existe (sección Volúmenes)
            resultados, fecha_res, _ = self.state.load_frentes_resultado()
            self._update_fecha_badge(fecha_res)
            total_row = next(
                (r for r in resultados if r.get("nombre") == "TOTAL"), None)
            if total_row:
                c = float(total_row.get("corte_m3", 0))
                r = float(total_row.get("relleno_m3", 0))
                self.kpi_ter.set_value(f"{r:,.0f} m³",
                                       delta_suffix="Volúmenes · frentes")
                self.kpi_exc.set_value(f"{c:,.0f} m³",
                                       delta_suffix="Volúmenes · frentes")
                obj_total = self._objetivo_total(cfg)
                if obj_total:
                    pct = (c + r) / obj_total * 100
                    self.kpi_avg.set_value(f"{pct:.1f}%",
                                           delta_suffix="vs objetivo total")
                else:
                    self.kpi_avg.set_value("—", delta_suffix="configure objetivo")
                self._render_donut(c, r, c - r)
            else:
                self.kpi_ter.set_value("—")
                self.kpi_exc.set_value("—")
                self.kpi_avg.set_value("—", delta_suffix="vs semana pasada")
                self._render_donut(0, 0, 0)
            self._render_flights_empty()
            self._render_bar_chart_empty()
            self._render_perfil_chart(fecha_ref=None)
            self._render_equipos_real()
            self._render_frentes(fecha_ref=None)
            return

        # ── Fecha de referencia: último vuelo procesado ──────────────────
        ult = df.iloc[-1]
        fecha_ref = ult["fecha"]  # Timestamp del último vuelo
        self._update_fecha_badge(fecha_ref.strftime("%Y-%m-%d") if fecha_ref else None)

        corte_acum   = float(ult.get("vol_corte_acum",   0))
        relleno_acum = float(ult.get("vol_relleno_acum", 0))

        # Si las columnas acum no existen, caer a valores diarios
        if corte_acum == 0 and relleno_acum == 0:
            corte_acum   = float(ult.get("vol_corte_dia",   0))
            relleno_acum = float(ult.get("vol_relleno_dia", 0))

        neto_acum = corte_acum - relleno_acum

        self.kpi_ter.set_value(
            f"{relleno_acum:,.0f} m³",
            self._delta(df, "vol_relleno_acum") or self._delta(df, "vol_relleno_dia"),
            delta_suffix="acum. · vs vuelo anterior",
        )
        self.kpi_exc.set_value(
            f"{corte_acum:,.0f} m³",
            self._delta(df, "vol_corte_acum") or self._delta(df, "vol_corte_dia"),
            delta_up=False,
            delta_suffix="acum. · vs vuelo anterior",
        )

        obj_total = self._objetivo_total(cfg)
        if obj_total:
            ejecutado = corte_acum + relleno_acum
            pct = ejecutado / obj_total * 100
            self.kpi_avg.set_value(f"{pct:.1f}%",
                                   self._delta_semanal(df),
                                   delta_suffix="vs semana pasada")
        else:
            self.kpi_avg.set_value("—", delta_suffix="configure objetivo")

        self._render_flights(df)
        self._refresh_bar_chart(df)
        self._render_donut(corte_acum, relleno_acum, neto_acum)
        self._render_perfil_chart(fecha_ref=fecha_ref)

        self._render_equipos_real()
        self._render_frentes(fecha_ref=fecha_ref)

    # ── Helpers ─────────────────────────────────────────────────────────
    def _update_fecha_badge(self, fecha_str: str | None):
        """Muestra u oculta el badge de fecha de referencia en el header."""
        if fecha_str:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(str(fecha_str))
                label = f"✈ Acumulado al {dt.strftime('%d/%m/%Y')}"
            except Exception:
                label = f"✈ Acumulado al {fecha_str}"
            self.fecha_ref_badge.configure(text=label)
            self.fecha_ref_badge.pack(side="left", padx=(10, 0))
        else:
            self.fecha_ref_badge.pack_forget()

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
        chg = (curr - prev) / prev * 100
        arrow = "↑" if chg >= 0 else "↓"
        return f"{arrow} {abs(chg):.1f}%"

    def _delta_semanal(self, df) -> str:
        """Variación semanal de vol_corte_acum para el KPI de Avance."""
        from datetime import timedelta
        if "vol_corte_acum" not in df.columns or len(df) < 2:
            return ""
        latest = df.iloc[-1]["fecha"]
        semana_atras = latest - timedelta(days=7)
        prev_rows = df[df["fecha"] <= semana_atras]
        if prev_rows.empty:
            return ""
        prev_val = float(prev_rows.iloc[-1]["vol_corte_acum"]) or 1e-9
        curr_val = float(df.iloc[-1]["vol_corte_acum"])
        chg = (curr_val - prev_val) / prev_val * 100
        arrow = "↑" if chg >= 0 else "↓"
        return f"{arrow} {abs(chg):.1f}%"

    def _objetivo_total(self, cfg: dict) -> float:
        """Volumen total objetivo = corte_obj + relleno_obj.

        Prioridad:
        1. proyecto_config.json  (seteado al validar volumen objetivo)
        2. Suma del perfil_objetivo (si el pipeline ya generó el perfil)
        """
        obj_c = float(cfg.get("vol_corte_objetivo",   0) or 0)
        obj_r = float(cfg.get("vol_relleno_objetivo", 0) or 0)
        if obj_c + obj_r > 0:
            return obj_c + obj_r
        # Fallback: sumar corte + relleno del perfil objetivo
        try:
            perfil = self.state.load_perfil_objetivo()
            if perfil:
                return sum(
                    float(p.get("corte_m3", 0)) + float(p.get("relleno_m3", 0))
                    for p in perfil
                )
        except Exception:
            pass
        return 0.0

    def _render_flights_empty(self):
        for w in self.vuelos_holder.winfo_children():
            w.destroy()
        n_disp = len(self.state.vuelos_disponibles())
        if n_disp > 0:
            ctk.CTkLabel(
                self.vuelos_holder,
                text=f"✈ {n_disp} DEM(s) cargados — sin procesar aún",
                font=T.FONT_SMALL, text_color=T.WARNING,
            ).pack(anchor="w", pady=(8, 4))
            ctk.CTkLabel(
                self.vuelos_holder,
                text="Ir a «Vuelos y modelos DEM» para procesar",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            ).pack(anchor="w")
        else:
            ctk.CTkLabel(
                self.vuelos_holder,
                text="Sin vuelos procesados",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            ).pack(anchor="w", pady=14)

    def _render_flights(self, df):
        for w in self.vuelos_holder.winfo_children():
            w.destroy()

        # ── Estadísticas de vuelos (sección Vuelos y modelos DEM) ────────
        n_disp = len(self.state.vuelos_disponibles())
        n_proc = len(self.state.vuelos_procesados())
        n_pend = max(n_disp - n_proc, 0)

        stats = ctk.CTkFrame(self.vuelos_holder, fg_color="transparent")
        stats.pack(fill="x", pady=(2, 8))
        for txt, clr in [
            (f"✈ {n_disp} vuelos", T.TEXT),
            (f"   ✓ {n_proc} procesados", T.SUCCESS),
            (f"   ○ {n_pend} pendientes",
             T.WARNING if n_pend > 0 else T.TEXT_FAINT),
        ]:
            ctk.CTkLabel(stats, text=txt,
                         font=T.FONT_SMALL, text_color=clr).pack(side="left")

        table = DataTable(
            self.vuelos_holder,
            columns=["Fecha", "Vuelo", "Corte acum.", "Estado"],
            widths=[110, 60, 110, 90],
        )
        table.pack(fill="x")
        for _, r in df.tail(5).iloc[::-1].iterrows():
            fecha = r["fecha"].strftime("%d %b, %Y")
            vuelo = f"#{int(r.get('vuelo_num', 0))}"
            corte = f"{r.get('vol_corte_acum', r.get('vol_corte_dia', 0)):,.0f} m³"
            badge = StatusBadge(table, "Procesado", kind="ok")
            table.add_row([f"✈ {fecha}", vuelo, corte, badge])
        ctk.CTkButton(
            self.vuelos_holder, text="Ver todos los vuelos",
            fg_color="transparent", text_color=T.PRIMARY,
            hover_color=T.HOVER_BG, font=T.FONT_SMALL,
            command=lambda: self._navigate("diario"),
        ).pack(pady=(8, 0))

    def _on_bar_period_change(self, value):
        df = getattr(self, "_df_history", None)
        if df is None or df.empty:
            self._render_bar_chart_empty()
        else:
            self._refresh_bar_chart(df)

    def _refresh_bar_chart(self, df):
        period = self._bar_period.get()
        if period == "Semanal":
            self._render_bar_chart_weekly(df)
        elif period == "Mensual":
            self._render_bar_chart_monthly(df)
        else:
            self._render_bar_chart_daily(df)

    def _render_bar_chart_empty(self):
        self._clear_canvas("bar")
        ctk.CTkLabel(
            self.bar_holder,
            text="Sin datos de volúmenes",
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
        ).pack(anchor="center", pady=30)

    def _render_bar_chart(self, df):
        self._render_bar_chart_daily(df)

    def _render_bar_chart_daily(self, df):
        df = df.tail(7)
        labels = [f.strftime("%d %b") for f in df["fecha"]]
        exc = df["vol_corte_dia"].tolist() if "vol_corte_dia" in df else [0]*len(df)
        ter = df["vol_relleno_dia"].tolist() if "vol_relleno_dia" in df else [0]*len(df)
        self._draw_bar_chart(labels, exc, ter)

    def _render_bar_chart_weekly(self, df):
        import pandas as pd
        df = df.copy()
        if "semana" not in df.columns:
            df["semana"] = df["fecha"].dt.strftime("%Y-W%W")
        grouped = (
            df.groupby("semana", sort=True)
            .agg(
                vol_corte_dia=("vol_corte_dia", "sum"),
                vol_relleno_dia=("vol_relleno_dia", "sum"),
            )
            .reset_index()
            .tail(8)
        )
        labels = grouped["semana"].tolist()
        exc = grouped["vol_corte_dia"].tolist()
        ter = grouped["vol_relleno_dia"].tolist()
        self._draw_bar_chart(labels, exc, ter)

    def _render_bar_chart_monthly(self, df):
        import pandas as pd
        df = df.copy()
        if "mes" not in df.columns:
            df["mes"] = df["fecha"].dt.strftime("%Y-%m")
        grouped = (
            df.groupby("mes", sort=True)
            .agg(
                vol_corte_dia=("vol_corte_dia", "sum"),
                vol_relleno_dia=("vol_relleno_dia", "sum"),
            )
            .reset_index()
        )
        labels = grouped["mes"].tolist()
        exc = grouped["vol_corte_dia"].tolist()
        ter = grouped["vol_relleno_dia"].tolist()
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

    def _render_perfil_chart(self, fecha_ref=None):
        # Limpia el contenedor
        if self._fig_perfil is not None:
            try:
                plt.close(self._fig_perfil)
            except Exception:
                pass
            self._fig_perfil = None
        for w in self.perfil_holder.winfo_children():
            w.destroy()

        perfil_obj = self.state.load_perfil_objetivo()
        perfil_av, fecha_av = self.state.load_perfil_avance()

        if not perfil_obj:
            ctk.CTkLabel(
                self.perfil_holder,
                text="Sin datos de perfil objetivo. Procese un vuelo para generar el perfil.",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            ).pack(anchor="center", pady=30)
            return

        # Advertencia si el perfil de avance no corresponde al último vuelo
        if fecha_ref is not None and fecha_av:
            try:
                import pandas as pd
                from datetime import datetime
                fecha_ref_str = pd.Timestamp(fecha_ref).strftime("%Y-%m-%d")
                dt_av = datetime.fromisoformat(str(fecha_av))
                fecha_av_str = dt_av.strftime("%Y-%m-%d")
                if fecha_av_str != fecha_ref_str:
                    ctk.CTkLabel(
                        self.perfil_holder,
                        text=(f"⚠  El perfil de avance corresponde al {dt_av.strftime('%d/%m/%Y')} "
                              f"— el último vuelo es del {pd.Timestamp(fecha_ref).strftime('%d/%m/%Y')}. "
                              "Recalcule en «Vuelos y modelos DEM»."),
                        font=T.FONT_SMALL, text_color=T.WARNING,
                        anchor="w", wraplength=900,
                    ).pack(anchor="w", padx=4, pady=(0, 4))
            except Exception:
                pass

        abs_obj = [p["abs"] for p in perfil_obj]
        corte_obj  = [-p["corte_m3"]  for p in perfil_obj]
        relleno_obj = [ p["relleno_m3"] for p in perfil_obj]

        if perfil_av:
            abs_av     = [p["abs"] for p in perfil_av]
            corte_av   = [-p["corte_m3"]  for p in perfil_av]
            relleno_av = [ p["relleno_m3"] for p in perfil_av]
        else:
            abs_av = abs_obj
            corte_av   = [0.0] * len(abs_obj)
            relleno_av = [0.0] * len(abs_obj)

        plt.style.use("default")
        bg   = T.mc(T.CARD_BG)
        axis = T.mc(T.AXIS_FG)
        grid = T.mc(T.GRID_COLOR)

        fig = Figure(figsize=(14, 3.6), dpi=100, facecolor=bg)
        self._fig_perfil = fig
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        # 4 líneas según especificación
        ax.plot(abs_obj, corte_obj,  color="#EF4444", lw=1.8,
                label="Corte total objetivo",   zorder=4)
        ax.plot(abs_av,  corte_av,   color="#D946EF", lw=1.8, ls="--",
                label=f"Corte acumulado{' · ' + fecha_av if fecha_av else ''}",
                zorder=5)
        ax.plot(abs_obj, relleno_obj, color="#166534", lw=1.8,
                label="Lleno total objetivo",   zorder=4)
        ax.plot(abs_av,  relleno_av,  color="#84CC16", lw=1.8, ls="--",
                label=f"Lleno acumulado{' · ' + fecha_av if fecha_av else ''}",
                zorder=5)

        ax.axhline(0, color=grid, lw=0.8, zorder=1)
        ax.set_xlabel("Abscisa (m)", fontsize=9, color=axis)
        ax.set_ylabel("Excavación (−) / Relleno (+)  [m³]", fontsize=9, color=axis)
        ax.legend(fontsize=8, frameon=False, loc="upper left",
                  ncol=4, bbox_to_anchor=(0, 1.14), labelcolor=axis)
        ax.grid(axis="y", ls=":", color=grid, alpha=0.7)
        ax.grid(axis="x", ls=":", color=grid, alpha=0.4)
        ax.tick_params(colors=axis, labelsize=8)
        for sp in ax.spines.values():
            sp.set_color(grid)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.perfil_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

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

    # ── Volumen por frente (datos reales) ───────────────────────────────
    def _render_frentes(self, fecha_ref=None):
        for w in self.fr_box.winfo_children():
            w.destroy()
        resultados, fecha_res, _modo_res = self.state.load_frentes_resultado()
        total_row = next((r for r in resultados if r.get("nombre") == "TOTAL"), None)
        datos = [r for r in resultados if r.get("nombre") != "TOTAL"]
        if not datos:
            frentes = self.state.load_frentes()
            datos = frentes
        if not datos:
            ctk.CTkLabel(
                self.fr_box, text="Sin frentes definidos",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            ).pack(anchor="w", pady=10)
            return

        # Mostrar la fecha de los resultados de frentes
        if fecha_res:
            try:
                from datetime import datetime
                dt_res = datetime.fromisoformat(str(fecha_res))
                fecha_res_str = dt_res.strftime("%d/%m/%Y")
            except Exception:
                fecha_res_str = str(fecha_res)
            ctk.CTkLabel(
                self.fr_box, text=f"Vuelo: {fecha_res_str}",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            ).pack(anchor="w", pady=(0, 4))

            # Advertencia si la fecha de frentes no coincide con el último vuelo
            if fecha_ref is not None:
                try:
                    import pandas as pd
                    fecha_ref_str = pd.Timestamp(fecha_ref).strftime("%Y-%m-%d")
                    fecha_res_norm = dt_res.strftime("%Y-%m-%d")
                    if fecha_res_norm != fecha_ref_str:
                        ctk.CTkLabel(
                            self.fr_box,
                            text=f"⚠ Desact. respecto al último vuelo ({fecha_ref_str})",
                            font=T.FONT_SMALL, text_color=T.WARNING,
                            wraplength=160,
                        ).pack(anchor="w", pady=(0, 4))
                except Exception:
                    pass

        # Denominador: corte total del proyecto (fila TOTAL si existe)
        total_corte = float(total_row.get("corte_m3", 0)) if total_row else sum(
            float(r.get("corte_m3", 0)) for r in datos
        )
        for fr in datos:
            nombre = str(fr.get("nombre", "Frente"))
            corte = float(fr.get("corte_m3", 0))
            pct = (corte / total_corte * 100) if total_corte > 0 else 0.0
            ProgressItem(self.fr_box, nombre, pct,
                         color=T.PRIMARY).pack(fill="x")

    # ── Tabla unificada de equipos (datos reales) ────────────────────────
    def _render_equipos_real(self):
        for w in self.eq_holder.winfo_children():
            w.destroy()

        try:
            import pandas as pd
            equipos_data = self.state.load_equipos_data()
            df_reg = self.state.load_registros_equipos()
        except Exception:
            for w in self.eq_holder.winfo_children():
                w.destroy()
            ctk.CTkLabel(self.eq_holder, text="Sin equipos registrados",
                         font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                         ).pack(anchor="w", pady=14)
            return

        equipos_list = equipos_data.get("equipos", [])
        flotas = equipos_data.get("flotas", [])

        if not equipos_list:
            for w in self.eq_holder.winfo_children():
                w.destroy()
            ctk.CTkLabel(self.eq_holder, text="Sin equipos registrados",
                         font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                         ).pack(anchor="w", pady=14)
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
