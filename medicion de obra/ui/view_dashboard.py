"""Vista Dashboard: KPIs + gráficos del avance global del proyecto."""
from __future__ import annotations

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from . import theme as T
from .state import ProjectState
from .widgets import KPICard, Card, SectionTitle
from .view_perfil import PerfilView


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self._mpl_canvas = None
        self._view_perfil: PerfilView | None = None
        self._build()
        self.refresh()

    def _build(self):
        SectionTitle(self, text="Dashboard del proyecto").pack(
            anchor="w", padx=24, pady=(20, 4))
        self.subtitulo = ctk.CTkLabel(
            self, text="", font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w")
        self.subtitulo.pack(anchor="w", padx=24, pady=(0, 14))

        kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        kpi_row.pack(fill="x", padx=20, pady=(0, 14))
        for i in range(4):
            kpi_row.grid_columnconfigure(i, weight=1, uniform="kpi")

        self.kpi_vuelos  = KPICard(kpi_row, "Vuelos procesados",
                                   accent=T.PRIMARY)
        self.kpi_corte   = KPICard(kpi_row, "Corte acumulado", unit="m³",
                                   accent=T.CORTE_COLOR)
        self.kpi_relleno = KPICard(kpi_row, "Relleno acumulado", unit="m³",
                                   accent=T.RELLENO_COLOR)
        self.kpi_avance  = KPICard(kpi_row, "Avance del corte", unit="del objetivo",
                                   accent=T.SUCCESS)
        for i, c in enumerate([self.kpi_vuelos, self.kpi_corte,
                               self.kpi_relleno, self.kpi_avance]):
            c.grid(row=0, column=i, sticky="nsew", padx=6)

        # Tabs: evolución 2D y perfil longitudinal
        self.tabs = ctk.CTkTabview(self, height=420,
                                    command=self._on_tab_change)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.tabs.add("Evolución (2D)")
        self.tabs.add("Perfil longitudinal")

        # ── Tab 2D ──────────────────────────────────────────────────────
        self.plot_holder = ctk.CTkFrame(
            self.tabs.tab("Evolución (2D)"), fg_color="transparent")
        self.plot_holder.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Tab Perfil — lazy load ──────────────────────────────────────
        self._tab_perfil_parent = self.tabs.tab("Perfil longitudinal")
        self._tab_perfil_placeholder = ctk.CTkLabel(
            self._tab_perfil_parent,
            text="(haz clic en esta pestaña para cargar el módulo de perfil)",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED)
        self._tab_perfil_placeholder.pack(expand=True)

    def _on_tab_change(self):
        if (self.tabs.get() == "Perfil longitudinal"
                and self._view_perfil is None):
            self._tab_perfil_placeholder.destroy()
            self._view_perfil = PerfilView(
                self._tab_perfil_parent, self.state)
            self._view_perfil.pack(fill="both", expand=True, padx=4, pady=4)

    # ── Datos ──────────────────────────────────────────────────────────
    def refresh(self):
        cfg = self.state.load_config() or {}
        df = self.state.load_registro()

        nombre = cfg.get("nombre", "Proyecto sin configurar")
        tramo  = cfg.get("tramo", "")
        self.subtitulo.configure(text=f"{nombre} · {tramo}" if tramo else nombre)

        if df.empty:
            self.kpi_vuelos.set("0")
            self.kpi_corte.set("—")
            self.kpi_relleno.set("—")
            self.kpi_avance.set("—")
            self._mensaje_vacio()
            return

        ult = df.iloc[-1]
        self.kpi_vuelos.set(str(int(ult["vuelo_num"])))
        self.kpi_corte.set(f"{ult['vol_corte_acum']:,.0f}")
        self.kpi_relleno.set(f"{ult['vol_relleno_acum']:,.0f}")

        obj_c = cfg.get("vol_corte_objetivo", 0) or 0
        if obj_c:
            pct = ult["vol_corte_acum"] / obj_c * 100
            color = T.SUCCESS if pct >= 100 else (
                T.WARNING if pct >= 60 else T.PRIMARY)
            self.kpi_avance.set(f"{pct:.1f}%", accent=color)
        else:
            self.kpi_avance.set("—")

        self._dibujar_grafico(df, cfg)
        if self._view_perfil:
            self._view_perfil.refresh()

    def _mensaje_vacio(self):
        for w in self.plot_holder.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.plot_holder,
            text=("Aún no hay vuelos procesados.\n\n"
                  "Ve a 'Vuelo diario' para procesar un DSM, "
                  "o genera datos de ejemplo desde la barra inferior."),
            font=T.FONT_BODY, text_color=T.TEXT_MUTED, justify="center",
        ).pack(expand=True)

    def _dibujar_grafico(self, df, cfg):
        # Limpia figura previa para no acumular memoria de matplotlib
        if getattr(self, "_fig2d", None) is not None:
            try: plt.close(self._fig2d)
            except Exception: pass
            self._fig2d = None
        for w in self.plot_holder.winfo_children():
            w.destroy()

        plt.style.use("dark_background")
        fig = Figure(figsize=(11, 4.6), dpi=100, facecolor="#1a1d23")
        self._fig2d = fig

        ax1 = fig.add_subplot(1, 2, 1)
        ax1.set_facecolor("#1a1d23")
        fechas = [f.strftime("%d/%m") for f in df["fecha"]]
        x = range(len(fechas))
        ax1.bar(x,  df["vol_corte_dia"].values,
                color=T.CORTE_COLOR, label="Corte", alpha=0.95)
        ax1.bar(x, -df["vol_relleno_dia"].values,
                color=T.RELLENO_COLOR, label="Relleno", alpha=0.95)
        ax1.axhline(0, color="#9CA3AF", lw=0.6)
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(fechas, fontsize=8, rotation=30, ha="right")
        ax1.set_title("Producción diaria (m³)", fontsize=10, color="white")
        ax1.legend(fontsize=8, frameon=False)
        ax1.grid(axis="y", ls="--", alpha=0.18)
        ax1.tick_params(colors="#cbd5e1", labelsize=8)
        for s in ax1.spines.values(): s.set_color("#374151")

        ax2 = fig.add_subplot(1, 2, 2)
        ax2.set_facecolor("#1a1d23")
        ax2.plot(x, df["vol_corte_acum"].values,
                 "-o", color=T.CORTE_LIGHT, lw=2, ms=4, label="Corte acum.")
        ax2.plot(x, df["vol_relleno_acum"].values,
                 "-o", color=T.RELLENO_LIGHT, lw=2, ms=4, label="Relleno acum.")
        obj_c = cfg.get("vol_corte_objetivo", 0) or 0
        obj_r = cfg.get("vol_relleno_objetivo", 0) or 0
        if obj_c:
            ax2.axhline(obj_c, color=T.CORTE_LIGHT, lw=0.7, ls="--", alpha=0.6,
                        label=f"Obj. corte {obj_c:,.0f}")
        if obj_r:
            ax2.axhline(obj_r, color=T.RELLENO_LIGHT, lw=0.7, ls="--", alpha=0.6,
                        label=f"Obj. relleno {obj_r:,.0f}")
        ax2.set_xticks(list(x))
        ax2.set_xticklabels(fechas, fontsize=8, rotation=30, ha="right")
        ax2.set_title("Acumulado vs objetivo (m³)", fontsize=10, color="white")
        ax2.legend(fontsize=7, frameon=False, loc="upper left")
        ax2.grid(axis="y", ls="--", alpha=0.18)
        ax2.tick_params(colors="#cbd5e1", labelsize=8)
        for s in ax2.spines.values(): s.set_color("#374151")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.plot_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvas = canvas
