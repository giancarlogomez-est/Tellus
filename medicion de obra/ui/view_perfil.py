"""Vista 'Perfil longitudinal':
Eje X = progresiva, Eje Y = cota.
Línea blanca = baseline. Una línea por cada vuelo seleccionado.
La capa marcada como 'activa' muestra el relleno corte/relleno vs baseline.
"""
from __future__ import annotations

import threading
import time

import customtkinter as ctk
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk,
)
from matplotlib.figure import Figure

from . import theme as T
from .state import ProjectState
from .dem_utils import cargar_dem_cached, alinear_dem_cached
from .eje_utils import cargar_eje, puntos_a_lo_largo, muestrear_array


PALETA = [
    "#3B82F6", "#F59E0B", "#8B5CF6", "#06B6D4",
    "#EC4899", "#84CC16", "#FB923C", "#A78BFA",
]


def _fmt_prog(m: float) -> str:
    """5300 → K5+300"""
    km = int(m // 1000)
    rm = int(m % 1000)
    return f"K{km}+{rm:03d}"


class PerfilView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self._fig: Figure | None = None
        self._mpl_canvas = None
        self._toolbar = None
        self._chk_vars: dict[str, ctk.BooleanVar] = {}
        self._activa_var = ctk.StringVar()  # fecha cuyo relleno corte/lleno se ve
        self._rendering = False
        self._build()
        self.refresh()

    def _build(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel = ctk.CTkFrame(self, fg_color="#0f1115",
                              corner_radius=10, width=290)
        panel.grid(row=0, column=0, sticky="ns", padx=(0, 10), pady=4)
        panel.grid_propagate(False)

        ctk.CTkLabel(panel, text="Capas del perfil", font=T.FONT_H2,
                      anchor="w").pack(fill="x", padx=14, pady=(14, 4))
        ctk.CTkLabel(panel, font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                      justify="left", anchor="w", wraplength=260,
                      text=("Marca las fechas a mostrar como líneas. "
                            "Elige cuál usa el relleno corte/relleno.")
                      ).pack(fill="x", padx=14, pady=(0, 6))

        self.fechas_holder = ctk.CTkScrollableFrame(
            panel, fg_color="transparent", height=260)
        self.fechas_holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        bar = ctk.CTkFrame(panel, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkButton(bar, text="Todas", height=28,
                       fg_color="transparent", border_width=1,
                       border_color=T.PRIMARY, text_color=T.PRIMARY,
                       hover_color="#1F2937",
                       command=self._sel_todas).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(bar, text="Ninguna", height=28,
                       fg_color="transparent", border_width=1,
                       border_color=T.PRIMARY, text_color=T.PRIMARY,
                       hover_color="#1F2937",
                       command=self._sel_ninguna).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        # Espaciado de muestreo
        sp = ctk.CTkFrame(panel, fg_color="transparent")
        sp.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkLabel(sp, text="Resolución del perfil (m)",
                      font=T.FONT_SMALL, anchor="w").pack(side="left")
        self._var_paso = ctk.StringVar(value="2")
        ctk.CTkOptionMenu(sp, values=["1", "2", "5", "10"],
                           variable=self._var_paso, width=80,
                           fg_color="#1F2937", button_color="#1F2937",
                           button_hover_color="#374151"
                           ).pack(side="right")

        self.btn_dibujar = ctk.CTkButton(
            panel, text="Dibujar perfil", height=38,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            font=T.FONT_H2, command=self._redibujar)
        self.btn_dibujar.pack(fill="x", padx=10, pady=(10, 6))

        self.info_lbl = ctk.CTkLabel(
            panel, text="", font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED, justify="left", anchor="w")
        self.info_lbl.pack(fill="x", padx=14, pady=(0, 12))

        # ── Canvas plot ──────────────────────────────────────────────────
        self.plot_holder = ctk.CTkFrame(self, fg_color="#1a1d23",
                                         corner_radius=10)
        self.plot_holder.grid(row=0, column=1, sticky="nsew", pady=4)

        self._mostrar_mensaje(
            "Selecciona al menos un vuelo y pulsa 'Dibujar perfil'")

    # ── Fechas ──────────────────────────────────────────────────────────
    def refresh(self):
        for w in self.fechas_holder.winfo_children():
            w.destroy()
        self._chk_vars.clear()

        disponibles = self.state.vuelos_disponibles()
        if not disponibles:
            ctk.CTkLabel(self.fechas_holder, text="(no hay DSMs en vuelos/)",
                          font=T.FONT_SMALL, text_color=T.TEXT_MUTED
                          ).pack(anchor="w", padx=4, pady=8)
            self.btn_dibujar.configure(state="disabled")
            return

        # Encabezados
        hdr = ctk.CTkFrame(self.fechas_holder, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(hdr, text="Mostrar", font=T.FONT_SMALL,
                      text_color=T.TEXT_MUTED, width=70, anchor="w"
                      ).pack(side="left", padx=(20, 0))
        ctk.CTkLabel(hdr, text="Activa", font=T.FONT_SMALL,
                      text_color=T.TEXT_MUTED, width=50, anchor="w"
                      ).pack(side="right", padx=(0, 8))

        self.btn_dibujar.configure(state="normal")
        for i, fecha in enumerate(disponibles):
            color = PALETA[i % len(PALETA)]
            row = ctk.CTkFrame(self.fechas_holder, fg_color="transparent")
            row.pack(fill="x", pady=2)
            sw = ctk.CTkFrame(row, width=12, height=12, fg_color=color,
                               corner_radius=3)
            sw.pack(side="left", padx=(2, 6))
            sw.pack_propagate(False)
            v = ctk.BooleanVar(value=(i == len(disponibles) - 1))
            self._chk_vars[fecha] = v
            ctk.CTkCheckBox(row, text=fecha, variable=v, font=T.FONT_BODY,
                             ).pack(side="left", anchor="w")
            ctk.CTkRadioButton(row, text="", variable=self._activa_var,
                                value=fecha, width=20).pack(
                side="right", padx=(0, 12))

        self._activa_var.set(disponibles[-1])  # última por defecto

    def _sel_todas(self):
        for v in self._chk_vars.values(): v.set(True)

    def _sel_ninguna(self):
        for v in self._chk_vars.values(): v.set(False)

    # ── Render ──────────────────────────────────────────────────────────
    def _redibujar(self):
        if self._rendering:
            return
        cfg = self.state.load_config() or {}
        baseline_path = self.state.baseline_dir / "dem_baseline.tif"

        # Localizar eje (cualquier extensión soportada)
        eje_path = None
        for ext in ("dxf", "dwg", "geojson", "shp"):
            p = self.state.baseline_dir / f"eje_via.{ext}"
            if p.exists():
                eje_path = p; break
        if eje_path is None:
            self._mostrar_mensaje(
                "No se encuentra baseline/eje_via.(dxf|geojson|shp).")
            return
        if not baseline_path.exists():
            self._mostrar_mensaje(
                "No se encuentra baseline/dem_baseline.tif.")
            return

        fechas_on = [f for f, v in self._chk_vars.items() if v.get()]

        self._rendering = True
        self.btn_dibujar.configure(state="disabled", text="Procesando…")
        self._mostrar_mensaje("Muestreando perfiles…")

        try:
            paso = float(self._var_paso.get())
        except ValueError:
            paso = 2.0

        threading.Thread(
            target=self._render_worker,
            args=(str(baseline_path), str(eje_path), fechas_on,
                   cfg.get("prog_inicio_m", 0.0), paso),
            daemon=True).start()

    def _render_worker(self, baseline_path, eje_path, fechas_on,
                        prog_inicio, paso):
        t0 = time.perf_counter()
        try:
            arr_base, tf, crs, _ = cargar_dem_cached(baseline_path)
            eje = cargar_eje(eje_path, crs)
            pts = puntos_a_lo_largo(eje, paso, prog_inicio)
            z_base = muestrear_array(arr_base, tf, pts["xs"], pts["ys"])

            capas = []
            for fecha in fechas_on:
                p = self.state.vuelos_dir / fecha / "dsm.tif"
                if not p.exists():
                    continue
                arr = alinear_dem_cached(str(p), baseline_path)
                z = muestrear_array(arr, tf, pts["xs"], pts["ys"])
                capas.append((fecha, z))

            self.after(0, self._dibujar_en_canvas,
                       pts["prog"], z_base, capas, t0)
        except Exception as e:
            import traceback; traceback.print_exc()
            self.after(0, self._mostrar_mensaje, f"Error: {e}")
            self.after(0, self._reset_boton)

    def _dibujar_en_canvas(self, prog, z_base, capas, t0):
        if self._fig is not None:
            try: plt.close(self._fig)
            except Exception: pass
            self._fig = None
        for w in self.plot_holder.winfo_children():
            w.destroy()

        plt.style.use("dark_background")
        fig = Figure(figsize=(11, 5.4), dpi=100, facecolor="#1a1d23")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#1a1d23")

        # 1) Baseline (blanco)
        ax.plot(prog, z_base, color="white", lw=1.8, label="Terreno natural")

        # 2) Capa activa con relleno corte/lleno
        activa = self._activa_var.get()
        z_activa = None
        for fecha, z in capas:
            if fecha == activa:
                z_activa = z; break

        if z_activa is not None:
            # Relleno verde donde z_activa > baseline (relleno)
            ax.fill_between(prog, z_base, z_activa,
                            where=(z_activa > z_base),
                            interpolate=True,
                            color=T.RELLENO_COLOR, alpha=0.55,
                            label="Relleno (capa activa)")
            # Relleno rojo donde z_activa < baseline (corte)
            ax.fill_between(prog, z_base, z_activa,
                            where=(z_activa < z_base),
                            interpolate=True,
                            color=T.CORTE_COLOR, alpha=0.55,
                            label="Corte (capa activa)")

        # 3) Líneas de todas las capas seleccionadas
        keys = list(self._chk_vars.keys())
        for fecha, z in capas:
            i = keys.index(fecha)
            color = PALETA[i % len(PALETA)]
            es_activa = (fecha == activa)
            ax.plot(prog, z, color=color,
                    lw=2.2 if es_activa else 1.3,
                    ls="-" if es_activa else "--",
                    label=f"Vuelo {fecha}" + (" (activa)" if es_activa else ""),
                    alpha=1.0 if es_activa else 0.85)

        # ── Estética ────────────────────────────────────────────────────
        ax.set_xlabel("Abscisa (m)", color="#cbd5e1", fontsize=10)
        ax.set_ylabel("Cota Z (m)",  color="#cbd5e1", fontsize=10)
        ax.tick_params(colors="#cbd5e1", labelsize=9)
        ax.grid(True, ls="--", alpha=0.18)
        for s in ax.spines.values(): s.set_color("#374151")

        # Eje X con etiquetas tipo K0+020
        if len(prog) > 0:
            # ~8 marcas máx
            n = len(prog)
            paso_idx = max(1, n // 8)
            ticks = list(prog[::paso_idx])
            if ticks[-1] != prog[-1]:
                ticks.append(prog[-1])
            ax.set_xticks(ticks)
            ax.set_xticklabels([_fmt_prog(t) for t in ticks],
                                rotation=20, ha="right", fontsize=8)

        cfg = self.state.load_config() or {}
        ax.set_title(
            f"Perfil longitudinal — {cfg.get('nombre', 'Proyecto')}",
            color="white", fontsize=11, pad=10)
        ax.legend(loc="best", fontsize=8, frameon=False,
                   labelcolor="#e5e7eb")

        fig.tight_layout()
        self._fig = fig

        canvas = FigureCanvasTkAgg(fig, master=self.plot_holder)
        canvas.draw()

        tb_frame = ctk.CTkFrame(self.plot_holder, fg_color="transparent",
                                 height=32)
        tb_frame.pack(side="bottom", fill="x")
        try:
            tb = NavigationToolbar2Tk(canvas, tb_frame, pack_toolbar=False)
            tb.config(background="#1a1d23")
            for c in tb.winfo_children():
                try: c.config(background="#1a1d23")
                except Exception: pass
            tb.update(); tb.pack(side="left")
            self._toolbar = tb
        except Exception:
            pass

        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvas = canvas

        # Info: longitud + tiempo
        long_total = float(prog[-1] - prog[0]) if len(prog) > 1 else 0.0
        elapsed = time.perf_counter() - t0
        self.info_lbl.configure(
            text=(f"{len(prog)} puntos · {long_total:.0f} m de eje · "
                  f"{len(capas)} capa(s) · {elapsed:.1f}s"),
            text_color=T.TEXT_MUTED)
        self._reset_boton()

    def _reset_boton(self):
        self._rendering = False
        self.btn_dibujar.configure(state="normal", text="Dibujar perfil")

    def _mostrar_mensaje(self, texto: str):
        for w in self.plot_holder.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.plot_holder, text=texto,
                      font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                      justify="center").pack(expand=True)
