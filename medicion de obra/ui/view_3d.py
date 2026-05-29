"""Vista 3D: superficies superpuestas por fecha + overlay corte/relleno.

Optimizada para velocidad:
  - Submuestreo adaptativo del DEM (máx ~150x150 puntos).
  - antialiased=False, shade=False en plot_surface.
  - Cierre explícito de figuras anteriores (evita memory leak).
  - Render bajo demanda: los checkboxes NO disparan re-render automáticamente.
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
from matplotlib import cm
from matplotlib.colors import Normalize

from . import theme as T
from .state import ProjectState
from .dem_utils import (
    cargar_dem_cached, alinear_dem_cached, malla_xy,
)


PALETA = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16",
]

# Máximo de puntos por eje en el render 3D. 150x150 = 22.5k caras,
# que matplotlib mueve fluido al rotar.
MAX_PUNTOS_EJE = 150
# Aviso de rendimiento si el usuario activa demasiadas capas.
LIMITE_CAPAS_RECOMENDADO = 5


def _calcular_step(shape: tuple[int, int]) -> int:
    """Paso de submuestreo entero más pequeño tal que la malla resultante
    quede dentro de MAX_PUNTOS_EJE en cada eje."""
    nrows, ncols = shape
    mx = max(nrows, ncols)
    if mx <= MAX_PUNTOS_EJE:
        return 1
    return int(np.ceil(mx / MAX_PUNTOS_EJE))


class View3D(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self._mpl_canvas = None
        self._fig: Figure | None = None
        self._toolbar = None
        self._chk_vars: dict[str, ctk.BooleanVar] = {}
        self._var_overlay = ctk.BooleanVar(value=True)
        self._var_baseline = ctk.BooleanVar(value=True)
        self._var_wire = ctk.BooleanVar(value=False)
        self._var_alta_calidad = ctk.BooleanVar(value=False)
        self._rendering = False
        self._build()
        self.refresh()

    def _build(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Panel control ─────────────────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=T.CARD_BG,
                              corner_radius=10, width=270)
        panel.grid(row=0, column=0, sticky="ns", padx=(0, 10), pady=4)
        panel.grid_propagate(False)

        ctk.CTkLabel(panel, text="Capas a mostrar", font=T.FONT_H2,
                      anchor="w").pack(fill="x", padx=14, pady=(14, 6))

        ctk.CTkCheckBox(panel, text="Terreno natural (baseline)",
                         variable=self._var_baseline, font=T.FONT_BODY
                         ).pack(anchor="w", padx=14, pady=3)
        ctk.CTkCheckBox(panel, text="Overlay corte / relleno",
                         variable=self._var_overlay, font=T.FONT_BODY
                         ).pack(anchor="w", padx=14, pady=3)
        ctk.CTkCheckBox(panel, text="Solo wireframe (más rápido)",
                         variable=self._var_wire, font=T.FONT_BODY
                         ).pack(anchor="w", padx=14, pady=3)
        ctk.CTkCheckBox(panel, text="Alta calidad (lento)",
                         variable=self._var_alta_calidad, font=T.FONT_BODY
                         ).pack(anchor="w", padx=14, pady=(3, 4))

        ctk.CTkLabel(panel, text="Capas por fecha", font=T.FONT_H2,
                      anchor="w").pack(fill="x", padx=14, pady=(14, 4))

        self.fechas_holder = ctk.CTkScrollableFrame(
            panel, fg_color="transparent", height=240)
        self.fechas_holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        bar = ctk.CTkFrame(panel, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkButton(bar, text="Todas", height=28,
                       fg_color="transparent", border_width=1,
                       border_color=T.PRIMARY, text_color=T.PRIMARY,
                       hover_color=T.HOVER_BG,
                       command=self._sel_todas).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(bar, text="Ninguna", height=28,
                       fg_color="transparent", border_width=1,
                       border_color=T.PRIMARY, text_color=T.PRIMARY,
                       hover_color=T.HOVER_BG,
                       command=self._sel_ninguna).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        self.btn_dibujar = ctk.CTkButton(
            panel, text="Renderizar 3D", height=38,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            font=T.FONT_H2, command=self._redibujar)
        self.btn_dibujar.pack(fill="x", padx=10, pady=(6, 6))

        self.info_lbl = ctk.CTkLabel(
            panel, text="", font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED, justify="left", anchor="w")
        self.info_lbl.pack(fill="x", padx=14, pady=(0, 12))

        # ── Canvas plot ──────────────────────────────────────────────────
        self.plot_holder = ctk.CTkFrame(self, fg_color=T.PLOT_3D_BG,
                                         corner_radius=10)
        self.plot_holder.grid(row=0, column=1, sticky="nsew", pady=4)

        self._mostrar_mensaje(
            "Selecciona las fechas a comparar y pulsa 'Renderizar 3D'")

    # ── Lista de fechas ─────────────────────────────────────────────────
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

        self.btn_dibujar.configure(state="normal")
        for i, fecha in enumerate(disponibles):
            color = PALETA[i % len(PALETA)]
            row = ctk.CTkFrame(self.fechas_holder, fg_color="transparent")
            row.pack(fill="x", pady=2)
            sw = ctk.CTkFrame(row, width=14, height=14, fg_color=color,
                               corner_radius=3)
            sw.pack(side="left", padx=(2, 6))
            sw.pack_propagate(False)
            v = ctk.BooleanVar(value=(i == len(disponibles) - 1))
            self._chk_vars[fecha] = v
            # Sin command — el render solo dispara con el botón
            ctk.CTkCheckBox(row, text=fecha, variable=v, font=T.FONT_BODY,
                             ).pack(side="left", anchor="w")

    def _sel_todas(self):
        for v in self._chk_vars.values(): v.set(True)

    def _sel_ninguna(self):
        for v in self._chk_vars.values(): v.set(False)

    # ── Render ──────────────────────────────────────────────────────────
    def _redibujar(self):
        if self._rendering:
            return
        baseline_path = self.state.baseline_dir / "dem_baseline.tif"
        if not baseline_path.exists():
            self._mostrar_mensaje(
                "No se encuentra baseline/dem_baseline.tif.")
            return

        fechas_on = [f for f, v in self._chk_vars.items() if v.get()]
        if not fechas_on and not self._var_baseline.get():
            self._mostrar_mensaje("Selecciona al menos una capa.")
            return

        if len(fechas_on) > LIMITE_CAPAS_RECOMENDADO:
            self.info_lbl.configure(
                text=(f"{len(fechas_on)} capas activas — "
                      f"considera desmarcar algunas para ir más rápido."),
                text_color=T.WARNING)

        self._rendering = True
        self.btn_dibujar.configure(state="disabled", text="Renderizando…")
        self._mostrar_mensaje("Cargando DSMs…")
        threading.Thread(
            target=self._render_worker,
            args=(str(baseline_path), fechas_on),
            daemon=True).start()

    def _render_worker(self, baseline_path: str, fechas_on: list[str]):
        t0 = time.perf_counter()
        try:
            arr_base, tf, crs, _ = cargar_dem_cached(baseline_path)
            step = (1 if self._var_alta_calidad.get()
                    else _calcular_step(arr_base.shape))
            # Submuestreo
            arr_base_s = arr_base[::step, ::step]
            X, Y = malla_xy(arr_base.shape, tf)
            X_s, Y_s = X[::step, ::step], Y[::step, ::step]

            capas = []
            for fecha in fechas_on:
                p = self.state.vuelos_dir / fecha / "dsm.tif"
                if not p.exists():
                    continue
                arr = alinear_dem_cached(str(p), baseline_path)
                capas.append((fecha, arr[::step, ::step]))

            self.after(0, self._dibujar_en_canvas,
                       X_s, Y_s, arr_base_s, capas, step, t0)
        except Exception as e:
            self.after(0, self._mostrar_mensaje, f"Error: {e}")
            self.after(0, self._reset_boton)

    def _dibujar_en_canvas(self, X, Y, arr_base, capas, step, t0):
        # Limpia figura previa para liberar memoria
        if self._fig is not None:
            try: plt.close(self._fig)
            except Exception: pass
            self._fig = None
        for w in self.plot_holder.winfo_children():
            w.destroy()

        dark = ctk.get_appearance_mode() != "Light"
        plt.style.use("dark_background" if dark else "default")
        bg = T.mc(T.PLOT_3D_BG); axfg = T.mc(T.AXIS_FG)
        grid = T.mc(T.GRID_COLOR)
        pane_rgba = (0.10, 0.11, 0.14, 0.7) if dark else (0.95, 0.96, 0.98, 0.7)
        fig = Figure(figsize=(10, 6.5), dpi=92, facecolor=bg)
        ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
        ax.set_facecolor(bg)

        wire = self._var_wire.get()
        z_all = []

        # 1) Terreno natural
        if self._var_baseline.get():
            z_all.append(arr_base)
            if wire:
                ax.plot_wireframe(X, Y, arr_base, color="#9CA3AF",
                                   linewidth=0.3, rstride=1, cstride=1,
                                   alpha=0.6)
            else:
                ax.plot_surface(X, Y, arr_base, color="#6B7280",
                                 alpha=0.45, linewidth=0,
                                 antialiased=False, shade=False,
                                 rstride=1, cstride=1)

        # 2) Capas históricas por fecha
        for i, (fecha, arr) in enumerate(capas):
            color = PALETA[
                list(self._chk_vars.keys()).index(fecha) % len(PALETA)]
            z_all.append(arr)
            if wire:
                ax.plot_wireframe(X, Y, arr, color=color,
                                   linewidth=0.4, rstride=1, cstride=1,
                                   alpha=0.8)
            else:
                ax.plot_surface(X, Y, arr, color=color,
                                 alpha=0.50, linewidth=0,
                                 antialiased=False, shade=False,
                                 rstride=1, cstride=1)

        # 3) Overlay corte / relleno del último vuelo seleccionado
        if self._var_overlay.get() and capas:
            _, arr_ult = capas[-1]
            dz = arr_ult - arr_base
            # RdYlGn: rojo (dz<0, corte) → amarillo (0) → verde (dz>0, relleno)
            cmap = plt.get_cmap("RdYlGn")
            vmax = float(np.nanmax(np.abs(dz))) if np.isfinite(
                np.nanmax(np.abs(dz))) else 1.0
            vmax = vmax or 1.0
            norm = Normalize(vmin=-vmax, vmax=vmax)
            facec = cmap(norm(dz))
            alpha_mask = np.clip(np.abs(dz) / max(vmax, 0.05), 0.15, 0.9)
            facec[..., -1] = alpha_mask
            facec[np.isnan(dz)] = (0, 0, 0, 0)
            ax.plot_surface(X, Y, arr_ult + 0.04, facecolors=facec,
                             rstride=1, cstride=1, linewidth=0,
                             antialiased=False, shade=False)
            sm = cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
            cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.04, shrink=0.55)
            cb.set_label("ΔZ vs baseline (m)\nrojo = corte · verde = relleno",
                          color=axfg, fontsize=8)
            cb.ax.tick_params(colors=axfg, labelsize=7)

        ax.set_xlabel("Este (m)", color=axfg, fontsize=8)
        ax.set_ylabel("Norte (m)", color=axfg, fontsize=8)
        ax.set_zlabel("Cota Z (m)", color=axfg, fontsize=8)
        ax.tick_params(colors=axfg, labelsize=7)
        for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            pane.set_facecolor(pane_rgba)
            pane.set_edgecolor(grid)

        if z_all:
            zmin = float(np.nanmin([np.nanmin(z) for z in z_all]))
            zmax = float(np.nanmax([np.nanmax(z) for z in z_all]))
            margen = max((zmax - zmin) * 0.08, 0.2)
            ax.set_zlim(zmin - margen, zmax + margen)

        cfg = self.state.load_config() or {}
        ax.set_title(f"Modelo 3D — {cfg.get('nombre', 'Proyecto')}",
                      color=T.mc(T.TEXT), fontsize=11, pad=10)
        if capas:
            handles = [plt.Line2D([0], [0], color=PALETA[
                list(self._chk_vars.keys()).index(f) % len(PALETA)],
                lw=4, label=f) for f, _ in capas]
            ax.legend(handles=handles, loc="upper left", fontsize=7,
                       frameon=False, labelcolor=axfg)

        ax.view_init(elev=28, azim=-60)
        fig.tight_layout()
        self._fig = fig

        canvas = FigureCanvasTkAgg(fig, master=self.plot_holder)
        canvas.draw()

        tb_frame = ctk.CTkFrame(self.plot_holder, fg_color="transparent",
                                 height=32)
        tb_frame.pack(side="bottom", fill="x")
        try:
            toolbar = NavigationToolbar2Tk(canvas, tb_frame, pack_toolbar=False)
            toolbar.config(background="#1a1d23")
            for child in toolbar.winfo_children():
                try: child.config(background="#1a1d23")
                except Exception: pass
            toolbar.update()
            toolbar.pack(side="left")
            self._toolbar = toolbar
        except Exception:
            pass

        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvas = canvas

        # Info: tamaño + tiempo
        npts = arr_base.shape[0] * arr_base.shape[1]
        elapsed = time.perf_counter() - t0
        self.info_lbl.configure(
            text=(f"{arr_base.shape[1]}×{arr_base.shape[0]} pts "
                  f"(step={step}) · {len(capas)} capa(s) · "
                  f"{elapsed:.1f}s"),
            text_color=T.TEXT_MUTED)
        self._reset_boton()

    def _reset_boton(self):
        self._rendering = False
        self.btn_dibujar.configure(state="normal", text="Renderizar 3D")

    def _mostrar_mensaje(self, texto: str):
        for w in self.plot_holder.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.plot_holder, text=texto,
                      font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                      justify="center").pack(expand=True)
