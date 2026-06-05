"""Vista 'Volúmenes': frentes de obra y cálculo de ΔZ."""
from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

import numpy as np
import pandas as pd
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from . import theme as T
from .state import ProjectState
from .widgets import Card, SectionTitle


# ── Helper ────────────────────────────────────────────────────────────────
def _km_str(m: float) -> str:
    m_int = int(m)
    return f"K{m_int // 1000}+{m_int % 1000:03d}"


def _fmt_vol(v: float) -> str:
    return f"{v:,.0f}"


# ═══════════════════════════════════════════════════════════════════════════
# Vista principal
# ═══════════════════════════════════════════════════════════════════════════
class VolumenesView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState, on_updated=None):
        super().__init__(master, fg_color=T.APP_BG)
        self.state = state
        self.on_updated = on_updated
        self._build()
        self.refresh()

    # ── Layout ──────────────────────────────────────────────────────────
    def _build(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=T.APP_BG)
        self.scroll.pack(fill="both", expand=True)
        self._fig_mapa    = None
        self._fig_frentes = None
        self._build_header()
        self._build_frentes_section()
        self._build_mapa_abscisas()
        self._build_resultados_section()
        self._build_historial_section()

    # ── Encabezado ──────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(18, 14))
        SectionTitle(hdr, text="Volúmenes", text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(
            hdr, font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
            text=("Define los frentes de obra y calcula los ΔZ y volúmenes "
                  "de corte/relleno por abscisa."),
            wraplength=860,
        ).pack(anchor="w")

    # ── Frentes de obra ──────────────────────────────────────────────────
    def _build_frentes_section(self):
        card = Card(self.scroll, title="Frentes de obra", light=True)
        card.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            card,
            text=("Define los tramos del proyecto acotados por abscisado. "
                  "Se calculará el volumen de corte/relleno de forma independiente para cada frente."),
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            wraplength=860,
        ).pack(anchor="w", padx=18, pady=(0, 12))

        # ── Formulario de ingreso ──────────────────────────────────────
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 8))

        self._ent_nombre = ctk.CTkEntry(
            form, placeholder_text="Nombre del frente",
            width=180, height=34, font=T.FONT_BODY,
        )
        self._ent_nombre.grid(row=0, column=0, padx=(0, 8))

        self._ent_encargado = ctk.CTkEntry(
            form, placeholder_text="Encargado del frente",
            width=170, height=34, font=T.FONT_BODY,
        )
        self._ent_encargado.grid(row=0, column=1, padx=(0, 8))

        self._ent_abs_ini = ctk.CTkEntry(
            form, placeholder_text="Abscisa inicio (m)",
            width=140, height=34, font=T.FONT_BODY,
        )
        self._ent_abs_ini.grid(row=0, column=2, padx=(0, 8))

        self._ent_abs_fin = ctk.CTkEntry(
            form, placeholder_text="Abscisa fin (m)",
            width=140, height=34, font=T.FONT_BODY,
        )
        self._ent_abs_fin.grid(row=0, column=3, padx=(0, 8))

        ctk.CTkButton(
            form, text="+ Agregar", width=110, height=34,
            font=T.FONT_BODY,
            fg_color=T.SUCCESS, hover_color=T.SUCCESS_HOV,
            text_color="white",
            command=self._add_frente,
        ).grid(row=0, column=4)

        # ── Divisor ───────────────────────────────────────────────────
        ctk.CTkFrame(card, height=1, fg_color=T.CARD_BORDER).pack(
            fill="x", padx=18, pady=(8, 6))

        # ── Lista dinámica de frentes ──────────────────────────────────
        self._frentes_list_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._frentes_list_frame.pack(fill="x", padx=18, pady=(0, 8))

        # ── Selector de fecha de vuelo ─────────────────────────────────
        ctk.CTkFrame(card, height=1, fg_color=T.CARD_BORDER).pack(
            fill="x", padx=18, pady=(8, 6))

        fecha_row = ctk.CTkFrame(card, fg_color="transparent")
        fecha_row.pack(fill="x", padx=18, pady=(0, 8))

        ctk.CTkLabel(
            fecha_row, text="Fecha de vuelo:",
            font=T.FONT_BODY, text_color=T.TEXT, anchor="w",
        ).pack(side="left", padx=(0, 8))

        self._fecha_vuelo_var = ctk.StringVar(value="Objetivo (diseño)")
        self._fecha_combo = ctk.CTkComboBox(
            fecha_row,
            variable=self._fecha_vuelo_var,
            values=["Objetivo (diseño)"],
            width=220, font=T.FONT_BODY,
            state="readonly",
        )
        self._fecha_combo.pack(side="left")

        ctk.CTkButton(
            fecha_row, text="↻", width=32, height=30,
            fg_color="transparent", border_width=1,
            border_color=T.CARD_BORDER, text_color=T.TEXT_MUTED,
            hover_color=T.HOVER_BG,
            command=self._refresh_fechas_combo,
        ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(
            fecha_row,
            text="Eje DXF referenciado desde K0+000",
            font=T.FONT_TINY, text_color=T.TEXT_FAINT, anchor="w",
        ).pack(side="left", padx=(14, 0))

        # ── Botón recalcular ───────────────────────────────────────────
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(4, 14))

        self.btn_recalc = ctk.CTkButton(
            btn_row,
            text="⟳  Recalcular Volúmenes por Frente",
            height=40, width=300,
            font=T.FONT_H2,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK,
            command=self._recalcular_frentes,
        )
        self.btn_recalc.pack(side="right")

        self._refresh_frentes_ui()
        self._refresh_fechas_combo()

    # ── Mapa de abscisado ────────────────────────────────────────────────
    def _build_mapa_abscisas(self):
        self._mapa_card = Card(
            self.scroll,
            title="Mapa de abscisado — Frentes de obra",
            light=True,
        )
        self._mapa_card.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkLabel(
            self._mapa_card,
            text="Posición de cada frente a lo largo del corredor vial.",
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 6))
        self._mapa_holder = ctk.CTkFrame(
            self._mapa_card, fg_color="transparent")
        self._mapa_holder.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        self._render_mapa_frentes()

    def _render_mapa_frentes(self):
        if self._fig_mapa is not None:
            try:
                plt.close(self._fig_mapa)
            except Exception:
                pass
            self._fig_mapa = None
        for w in self._mapa_holder.winfo_children():
            w.destroy()

        frentes = self.state.load_frentes()

        if not frentes:
            ctk.CTkLabel(
                self._mapa_holder,
                text=(
                    "Sin frentes definidos. "
                    "Agrega frentes para ver el mapa de abscisado."
                ),
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=14)
            return

        _PALETTE = [
            "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
            "#8B5CF6", "#06B6D4", "#84CC16", "#F97316",
            "#EC4899", "#14B8A6",
        ]

        plt.style.use("default")
        bg     = T.mc(T.CARD_BG)
        axis_c = T.mc(T.AXIS_FG)
        grid_c = T.mc(T.GRID_COLOR)

        n      = len(frentes)
        fig_h  = max(2.4, 0.60 * n + 1.4)

        fig = Figure(figsize=(9, fig_h), dpi=100, facecolor=bg)
        self._fig_mapa = fig
        ax  = fig.add_subplot(111)
        ax.set_facecolor(bg)

        all_ini = [float(f.get("abs_ini", 0)) for f in frentes]
        all_fin = [float(f.get("abs_fin", 0)) for f in frentes]
        span    = max(all_fin) - min(all_ini) or 1.0
        margin  = span * 0.06

        for i, fr in enumerate(frentes):
            ini       = float(fr.get("abs_ini", 0))
            fin       = float(fr.get("abs_fin", 0))
            nombre    = str(fr.get("nombre", f"Frente {i + 1}"))
            encargado = str(fr.get("encargado", "")).strip()
            color     = _PALETTE[i % len(_PALETTE)]

            ax.barh(i, fin - ini, left=ini, height=0.60,
                    color=color, alpha=0.82, zorder=2,
                    edgecolor=bg, linewidth=0.8)

            # Etiqueta dentro de la barra: nombre · encargado
            mid = (ini + fin) / 2
            lbl = nombre if not encargado else f"{nombre}  ·  {encargado}"
            ax.text(mid, i, lbl,
                    ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold",
                    zorder=3, clip_on=True)

            # Abscisas de inicio y fin bajo la barra
            ax.text(ini, i - 0.42, _km_str(ini),
                    ha="left", va="top", fontsize=6.5, color=axis_c, zorder=4)
            ax.text(fin, i - 0.42, _km_str(fin),
                    ha="right", va="top", fontsize=6.5, color=axis_c, zorder=4)

        # Ejes y estilo
        tick_vals = sorted(set(all_ini + all_fin))
        ax.set_xticks(tick_vals)
        ax.set_xticklabels(
            [_km_str(v) for v in tick_vals],
            fontsize=8, color=axis_c, rotation=30, ha="right",
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels([])
        ax.set_xlim(min(all_ini) - margin, max(all_fin) + margin)
        ax.set_ylim(-0.85, n - 0.15)
        ax.grid(axis="x", ls="--", color=grid_c, alpha=0.45, zorder=0)

        for s in ax.spines.values():
            s.set_color(grid_c)
        ax.tick_params(colors=axis_c, left=False)

        fig.tight_layout(pad=0.5)

        canvas = FigureCanvasTkAgg(fig, master=self._mapa_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ── Resultados por frente ────────────────────────────────────────────
    def _build_resultados_section(self):
        self._res_card = Card(
            self.scroll, title="Resultados por frente", light=True)
        self._res_card.pack(fill="x", padx=20, pady=(0, 32))
        self._res_body = ctk.CTkFrame(self._res_card, fg_color="transparent")
        self._res_body.pack(fill="x", padx=18, pady=(0, 10))

        # Separador + sección gráfica
        ctk.CTkFrame(self._res_card, height=1,
                     fg_color=T.CARD_BORDER).pack(fill="x", padx=18, pady=(4, 6))
        ctk.CTkLabel(
            self._res_card,
            text="Abscisado vs. Volumen por frente",
            font=(T.FONT_FAMILY, 11, "bold"), text_color=T.TEXT, anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 4))
        self._chart_holder = ctk.CTkFrame(self._res_card, fg_color="transparent")
        self._chart_holder.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        self._refresh_resultados()

    # ── Combo de fechas de vuelo ─────────────────────────────────────────
    def _refresh_fechas_combo(self):
        """Actualiza la lista de fechas de vuelos procesados en el combo."""
        procesadas = sorted(self.state.vuelos_procesados(), reverse=True)
        opciones = ["Objetivo (diseño)"] + list(procesadas)
        self._fecha_combo.configure(values=opciones)
        current = self._fecha_vuelo_var.get()
        if current not in opciones:
            self._fecha_vuelo_var.set("Objetivo (diseño)")

    def _fecha_seleccionada(self) -> str | None:
        """Devuelve la fecha seleccionada o None si se eligió 'Objetivo'."""
        val = self._fecha_vuelo_var.get()
        if val.startswith("Objetivo"):
            return None
        return val

    # ── Rutas de archivos ────────────────────────────────────────────────
    def _eje_path(self) -> Path | None:
        bd = self.state.baseline_dir
        for ext in ("dxf", "DXF", "dwg", "DWG"):
            p = bd / f"eje_via.{ext}"
            if p.exists():
                return p
        return None

    def _dem_final_path(self) -> Path | None:
        return self.state.dem_final_path()

    def refresh(self):
        if hasattr(self, "_hist_body"):
            self._refresh_historial()
        if hasattr(self, "_fecha_combo"):
            self._refresh_fechas_combo()

    # ── Frentes: lista dinámica ──────────────────────────────────────────
    def _refresh_frentes_ui(self):
        for w in self._frentes_list_frame.winfo_children():
            w.destroy()

        frentes = self.state.load_frentes()

        if not frentes:
            ctk.CTkLabel(
                self._frentes_list_frame,
                text="No hay frentes definidos. Usa el formulario para agregar tramos.",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=10)
            return

        # Cabecera de columnas
        _COLS = [
            ("NOMBRE",     200, "w"),
            ("ENCARGADO",  170, "w"),
            ("INICIO",     110, "w"),
            ("FIN",        110, "w"),
            ("LONGITUD",   100, "w"),
            ("",            48, "center"),
        ]
        hdr = ctk.CTkFrame(self._frentes_list_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=(2, 4))
        for col_i, (txt, w, anchor) in enumerate(_COLS):
            ctk.CTkLabel(
                hdr, text=txt, font=T.FONT_TINY,
                text_color=T.TEXT_MUTED, width=w, anchor=anchor,
            ).grid(row=0, column=col_i, sticky="w", padx=4)

        for i, fr in enumerate(frentes):
            nombre     = str(fr.get("nombre", f"Frente {i + 1}"))
            encargado  = str(fr.get("encargado", "")).strip()
            abs_ini    = float(fr.get("abs_ini", 0))
            abs_fin    = float(fr.get("abs_fin", 0))
            longitud   = abs_fin - abs_ini

            row = ctk.CTkFrame(
                self._frentes_list_frame,
                fg_color=T.TABLE_HOVER if i % 2 == 0 else "transparent",
                corner_radius=6,
            )
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=f"  {nombre}",
                font=(T.FONT_FAMILY, 11, "bold"),
                text_color=T.TEXT, width=200, anchor="w",
            ).grid(row=0, column=0, padx=4, pady=6)

            ctk.CTkLabel(
                row, text=encargado if encargado else "—",
                font=T.FONT_BODY,
                text_color=T.TEXT if encargado else T.TEXT_MUTED,
                width=170, anchor="w",
            ).grid(row=0, column=1, padx=4)

            ctk.CTkLabel(
                row, text=_km_str(abs_ini),
                font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                width=110, anchor="w",
            ).grid(row=0, column=2, padx=4)

            ctk.CTkLabel(
                row, text=_km_str(abs_fin),
                font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                width=110, anchor="w",
            ).grid(row=0, column=3, padx=4)

            ctk.CTkLabel(
                row, text=f"{longitud:,.0f} m",
                font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                width=100, anchor="w",
            ).grid(row=0, column=4, padx=4)

            def _make_del(idx=i):
                return lambda: self._remove_frente(idx)

            ctk.CTkButton(
                row, text="✕", width=32, height=26,
                fg_color="transparent",
                hover_color=("#FEE2E2", "#7F1D1D"),
                text_color=T.DANGER,
                font=(T.FONT_FAMILY, 11, "bold"),
                command=_make_del(),
            ).grid(row=0, column=5, padx=(0, 4))

    def _add_frente(self):
        nombre      = self._ent_nombre.get().strip()
        encargado   = self._ent_encargado.get().strip()
        abs_ini_str = self._ent_abs_ini.get().strip()
        abs_fin_str = self._ent_abs_fin.get().strip()

        if not nombre:
            messagebox.showwarning(
                "Campo requerido", "El nombre del frente no puede estar vacío.")
            return
        try:
            abs_ini = float(abs_ini_str)
            abs_fin = float(abs_fin_str)
        except ValueError:
            messagebox.showwarning(
                "Valor inválido",
                "Las abscisas deben ser números en metros.\n"
                "Ejemplo: 2600  y  3200")
            return
        if abs_fin <= abs_ini:
            messagebox.showwarning(
                "Abscisas inválidas",
                "La abscisa fin debe ser mayor que la abscisa inicio.")
            return

        frentes = self.state.load_frentes()
        frentes.append({
            "nombre": nombre,
            "encargado": encargado,
            "abs_ini": abs_ini,
            "abs_fin": abs_fin,
        })
        self.state.save_frentes(frentes)

        self._ent_nombre.delete(0, "end")
        self._ent_encargado.delete(0, "end")
        self._ent_abs_ini.delete(0, "end")
        self._ent_abs_fin.delete(0, "end")
        self._refresh_frentes_ui()
        self._render_mapa_frentes()
        if self.on_updated:
            self.on_updated()

    def _remove_frente(self, idx: int):
        frentes = self.state.load_frentes()
        if 0 <= idx < len(frentes):
            frentes.pop(idx)
            self.state.save_frentes(frentes)
            self._refresh_frentes_ui()
            self._render_mapa_frentes()
            if self.on_updated:
                self.on_updated()

    # ── Resultados ───────────────────────────────────────────────────────
    def _refresh_resultados(self, ok: bool = True):
        for w in self._res_body.winfo_children():
            w.destroy()

        resultados, fecha_res, modo_res = self.state.load_frentes_resultado()

        if not resultados:
            ctk.CTkLabel(
                self._res_body,
                text=(
                    "Sin resultados. Carga los tres insumos, define al menos un frente "
                    "y haz clic en '⟳ Recalcular'."
                ),
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=14)
            self._render_grafica_frentes([])
            return

        # Banner de modo/fecha del resultado
        if modo_res:
            banner = ctk.CTkFrame(self._res_body, fg_color=T.HOVER_BG, corner_radius=6)
            banner.pack(fill="x", pady=(4, 8))
            icono = "📅" if fecha_res else "📐"
            ctk.CTkLabel(
                banner,
                text=f"  {icono}  {modo_res}",
                font=(T.FONT_FAMILY, 11, "bold"),
                text_color=T.PRIMARY, anchor="w",
            ).pack(anchor="w", padx=12, pady=6)

        _COLS = [
            ("FRENTE",        200),
            ("INICIO",        110),
            ("FIN",           110),
            ("CORTE (m³)",    130),
            ("RELLENO (m³)",  140),
            ("BALANCE (m³)",  130),
        ]

        # Cabecera
        hdr = ctk.CTkFrame(self._res_body, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 2))
        for col_i, (txt, w) in enumerate(_COLS):
            ctk.CTkLabel(
                hdr, text=txt, font=T.FONT_TINY,
                text_color=T.TEXT_MUTED, width=w, anchor="w",
            ).grid(row=0, column=col_i, sticky="w", padx=4)

        ctk.CTkFrame(self._res_body, height=1,
                     fg_color=T.CARD_BORDER).pack(fill="x", pady=(0, 4))

        for j, r in enumerate(resultados):
            is_total = r.get("nombre") == "TOTAL"

            if is_total:
                ctk.CTkFrame(self._res_body, height=1,
                             fg_color=T.CARD_BORDER).pack(fill="x", pady=(4, 4))

            row = ctk.CTkFrame(
                self._res_body,
                fg_color=(
                    "transparent" if is_total
                    else (T.TABLE_HOVER if j % 2 == 0 else "transparent")
                ),
                corner_radius=6 if not is_total else 0,
            )
            row.pack(fill="x", pady=(2 if not is_total else 4))

            nombre     = str(r.get("nombre", ""))
            abs_ini    = r.get("abs_ini")
            abs_fin    = r.get("abs_fin")
            corte      = float(r.get("corte_m3", 0))
            relleno    = float(r.get("relleno_m3", 0))
            balance    = float(r.get("balance_m3", 0))

            ini_str = _km_str(abs_ini) if abs_ini is not None else "—"
            fin_str = _km_str(abs_fin) if abs_fin is not None else "—"
            bal_str = f"{balance:+,.0f}"
            bal_color = T.DANGER if balance < 0 else T.SUCCESS

            font_n = (T.FONT_FAMILY, 11, "bold") if is_total else T.FONT_BODY

            cells = [
                (f"  {nombre}",        T.TEXT,           font_n),
                (ini_str,              T.TEXT_MUTED,     T.FONT_BODY),
                (fin_str,              T.TEXT_MUTED,     T.FONT_BODY),
                (_fmt_vol(corte),      T.CORTE_COLOR,    font_n),
                (_fmt_vol(relleno),    T.RELLENO_COLOR,  font_n),
                (bal_str,              bal_color,        font_n),
            ]
            widths = [w for _, w in _COLS]
            for col_i, ((txt, color, font), w) in enumerate(zip(cells, widths)):
                ctk.CTkLabel(
                    row, text=txt, font=font,
                    text_color=color, width=w, anchor="w",
                ).grid(row=0, column=col_i, sticky="w", padx=4, pady=6)

        self._render_grafica_frentes(resultados)

    # ── Gráfica estilo Excel: corte/lleno por abscisa ────────────────────
    def _render_grafica_frentes(self, resultados: list):
        if self._fig_frentes is not None:
            try:
                plt.close(self._fig_frentes)
            except Exception:
                pass
            self._fig_frentes = None
        for w in self._chart_holder.winfo_children():
            w.destroy()

        perfil_obj             = self.state.load_perfil_objetivo()
        perfil_avance, f_fecha = self.state.load_perfil_avance()

        if not perfil_obj and not perfil_avance:
            ctk.CTkLabel(
                self._chart_holder,
                text=(
                    "Sin perfil disponible. Recalcula usando 'Objetivo (diseño)' "
                    "y después con una fecha de vuelo."
                ),
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=14)
            return

        frentes = self.state.load_frentes()
        frentes_ranges = [
            (float(fr["abs_ini"]), float(fr["abs_fin"]))
            for fr in frentes
            if fr.get("abs_ini") is not None
        ]

        def _in_frentes(v: float) -> bool:
            return any(ini <= v <= fin for ini, fin in frentes_ranges)

        # Unir abscisas de ambos perfiles, filtradas a los frentes definidos
        all_abs = sorted({
            p["abs"] for src in (perfil_obj, perfil_avance) for p in src
            if _in_frentes(p["abs"])
        })

        if not all_abs:
            ctk.CTkLabel(
                self._chart_holder,
                text="No hay datos en las abscisas de los frentes definidos.",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=14)
            return

        obj_map    = {p["abs"]: p for p in perfil_obj}
        avance_map = {p["abs"]: p for p in perfil_avance}

        xs = all_abs
        # corte → negativo (bajo el cero), relleno → positivo (sobre el cero)
        obj_corte   = [-obj_map[x]["corte_m3"]    if x in obj_map    else float("nan") for x in xs]
        obj_relleno = [ obj_map[x]["relleno_m3"]  if x in obj_map    else float("nan") for x in xs]
        dia_corte   = [-avance_map[x]["corte_m3"] if x in avance_map else float("nan") for x in xs]
        dia_relleno = [ avance_map[x]["relleno_m3"] if x in avance_map else float("nan") for x in xs]

        plt.style.use("default")
        bg     = T.mc(T.CARD_BG)
        axis_c = T.mc(T.AXIS_FG)
        grid_c = T.mc(T.GRID_COLOR)

        fig = Figure(figsize=(9, 4.0), dpi=100, facecolor=bg)
        self._fig_frentes = fig
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        xs_arr       = np.array(xs,          dtype="float64")
        obj_c_arr    = np.array(obj_corte,   dtype="float64")
        obj_r_arr    = np.array(obj_relleno, dtype="float64")
        dia_c_arr    = np.array(dia_corte,   dtype="float64")
        dia_r_arr    = np.array(dia_relleno, dtype="float64")

        zeros = np.zeros_like(xs_arr)

        # ── Áreas rellenas día ──────────────────────────────────────────
        if avance_map:
            ax.fill_between(xs_arr, dia_c_arr, zeros,
                            where=np.isfinite(dia_c_arr),
                            color=T.CORTE_COLOR, alpha=0.70,
                            step="mid", zorder=2, label="Corte día")
            ax.fill_between(xs_arr, dia_r_arr, zeros,
                            where=np.isfinite(dia_r_arr),
                            color=T.RELLENO_COLOR, alpha=0.70,
                            step="mid", zorder=2, label="Lleno día")

        # ── Líneas objetivo ─────────────────────────────────────────────
        if obj_map:
            ax.step(xs_arr, obj_c_arr, where="mid",
                    color=T.CORTE_COLOR, lw=1.8, ls="--", alpha=0.9,
                    zorder=3, label="Objetivo corte")
            ax.step(xs_arr, obj_r_arr, where="mid",
                    color=T.RELLENO_COLOR, lw=1.8, ls="--", alpha=0.9,
                    zorder=3, label="Objetivo lleno")

        # ── Línea de cero ───────────────────────────────────────────────
        ax.axhline(0, color=axis_c, lw=0.8, zorder=4)

        # ── Líneas divisorias entre frentes ────────────────────────────
        for ini, fin in frentes_ranges:
            ax.axvline(ini, color=grid_c, lw=0.9, ls=":", zorder=1)
        if frentes_ranges:
            ax.axvline(frentes_ranges[-1][1], color=grid_c, lw=0.9, ls=":", zorder=1)

        # ── Eje X con etiquetas inteligentes ───────────────────────────
        boundary_abs = sorted({v for r in frentes_ranges for v in r})
        span = (xs[-1] - xs[0]) if len(xs) > 1 else 1.0
        step_lbl = 50 if span < 600 else (100 if span < 1500 else 200)
        mid_ticks = [
            x for x in xs
            if round(x % step_lbl) < 10.01
            and x not in boundary_abs
        ]
        tick_vals = sorted(set(boundary_abs + mid_ticks))
        ax.set_xticks(tick_vals)
        ax.set_xticklabels(
            [_km_str(v) for v in tick_vals],
            fontsize=7.5, color=axis_c, rotation=30, ha="right",
        )
        ax.set_xlim(xs[0] - span * 0.01, xs[-1] + span * 0.01)

        # ── Eje Y ───────────────────────────────────────────────────────
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{abs(v):,.0f}"))
        ax.set_ylabel("Volumen (m³)", fontsize=8, color=axis_c)
        ax.tick_params(colors=axis_c, labelsize=8)

        # Anotaciones de totales por frente (de resultados agregados)
        for r in resultados:
            if r.get("nombre") == "TOTAL" or r.get("abs_ini") is None:
                continue
            ini_fr = float(r["abs_ini"])
            fin_fr = float(r["abs_fin"])
            mid    = (ini_fr + fin_fr) / 2.0
            c_tot  = float(r.get("corte_m3", 0))
            r_tot  = float(r.get("relleno_m3", 0))
            y_min, y_max = ax.get_ylim()
            if c_tot:
                ax.annotate(
                    f"{c_tot:,.0f}",
                    xy=(mid, y_min * 0.5), xytext=(0, 0),
                    textcoords="offset points",
                    ha="center", va="center", fontsize=7.5,
                    color=T.CORTE_COLOR, fontweight="bold", zorder=5,
                )
            if r_tot:
                ax.annotate(
                    f"{r_tot:,.0f}",
                    xy=(mid, y_max * 0.5), xytext=(0, 0),
                    textcoords="offset points",
                    ha="center", va="center", fontsize=7.5,
                    color=T.RELLENO_COLOR, fontweight="bold", zorder=5,
                )

        ax.legend(fontsize=8, frameon=False, loc="upper right",
                  labelcolor=axis_c, ncol=4)
        ax.grid(axis="y", ls="--", color=grid_c, alpha=0.40, zorder=0)

        for s in ax.spines.values():
            s.set_color(grid_c)

        fig.tight_layout(pad=0.6)

        canvas = FigureCanvasTkAgg(fig, master=self._chart_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ── Historial diario ──────────────────────────────────────────────────
    def _build_historial_section(self):
        card = Card(
            self.scroll,
            title="Comparativo diario de volúmenes",
            light=True,
        )
        card.pack(fill="x", padx=20, pady=(0, 32))
        ctk.CTkLabel(
            card,
            text="Día procesado más reciente (★). Numeración consecutiva desde el primer vuelo cargado.",
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 10))
        self._hist_body = ctk.CTkFrame(card, fg_color="transparent")
        self._hist_body.pack(fill="x", padx=18, pady=(0, 16))
        self._refresh_historial()

    def _refresh_historial(self):
        for w in self._hist_body.winfo_children():
            w.destroy()

        try:
            df = self.state.load_registro()
        except Exception:
            df = None

        if df is None or df.empty:
            ctk.CTkLabel(
                self._hist_body,
                text="Sin registros de vuelos disponibles.",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=10)
            return

        # Solo fechas que existen como vuelos en la sección "Vuelos y modelos DEM"
        fechas_vuelos = set(self.state.vuelos_disponibles())
        if fechas_vuelos:
            df = df[df["fecha"].dt.strftime("%Y-%m-%d").isin(fechas_vuelos)]
        else:
            df = pd.DataFrame()

        # Solo filas con cálculo real de volúmenes (pipeline ejecutado)
        vol_col = "vol_corte_dia"
        if not df.empty and vol_col in df.columns:
            df = df[df[vol_col].notna()]
        elif not df.empty:
            df = pd.DataFrame()

        if df.empty:
            ctk.CTkLabel(
                self._hist_body,
                text="Sin cálculos de volumen aún. Procesa un vuelo con el pipeline para ver datos aquí.",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=10)
            return

        # Todos los registros con volumen, más reciente primero
        df = (
            df.sort_values("fecha")
            .iloc[::-1]
            .reset_index(drop=True)
        )

        # Numerar vuelos desde la primera fecha cargada en "Vuelos y modelos DEM"
        all_vuelos_sorted = sorted(self.state.vuelos_disponibles())
        vuelo_rank = {v: i + 1 for i, v in enumerate(all_vuelos_sorted)}

        _COLS = [
            ("FECHA",             130),
            ("VUELO",              64),
            ("CORTE DÍA (m³)",   140),
            ("RELLENO DÍA (m³)", 150),
            ("BALANCE (m³)",     140),
            ("Δ CORTE",          110),
            ("Δ RELLENO",        110),
        ]

        # Cabecera
        hdr = ctk.CTkFrame(self._hist_body, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 2))
        for col_i, (txt, col_w) in enumerate(_COLS):
            ctk.CTkLabel(
                hdr, text=txt, font=T.FONT_TINY,
                text_color=T.TEXT_MUTED, width=col_w, anchor="w",
            ).grid(row=0, column=col_i, sticky="w", padx=4)

        ctk.CTkFrame(self._hist_body, height=1,
                     fg_color=T.CARD_BORDER).pack(fill="x", pady=(2, 4))

        rows_frame = ctk.CTkScrollableFrame(
            self._hist_body, fg_color="transparent", height=300)
        rows_frame.pack(fill="x")

        for i in range(len(df)):
            r         = df.iloc[i]
            is_latest = (i == 0)

            corte   = float(r.get("vol_corte_dia",   0) or 0)
            relleno = float(r.get("vol_relleno_dia", 0) or 0)
            balance = float(r.get("balance_dia",     0) or 0)
            fecha_key = r["fecha"].strftime("%Y-%m-%d")
            vuelo = vuelo_rank.get(fecha_key, int(r.get("vuelo_num", 0) or 0))

            # Δ respecto al día anterior en la lista (= siguiente en el tiempo)
            delta_c_txt, delta_c_col = "—", T.TEXT_MUTED
            delta_r_txt, delta_r_col = "—", T.TEXT_MUTED
            if i + 1 < len(df):
                prev = df.iloc[i + 1]
                pc   = float(prev.get("vol_corte_dia",   0) or 0)
                pr   = float(prev.get("vol_relleno_dia", 0) or 0)
                if pc != 0:
                    pct = (corte - pc) / abs(pc) * 100
                    arrow = "↑" if pct >= 0 else "↓"
                    delta_c_txt = f"{arrow} {abs(pct):.1f}%"
                    delta_c_col = T.SUCCESS if pct >= 0 else T.DANGER
                if pr != 0:
                    pct = (relleno - pr) / abs(pr) * 100
                    arrow = "↑" if pct >= 0 else "↓"
                    delta_r_txt = f"{arrow} {abs(pct):.1f}%"
                    delta_r_col = T.SUCCESS if pct >= 0 else T.DANGER

            # Estilo de fila
            if is_latest:
                row_bg   = ("#EFF6FF", "#1E3A5F")   # azul suave claro/oscuro
                name_fnt = (T.FONT_FAMILY, 11, "bold")
            else:
                row_bg   = T.TABLE_HOVER if i % 2 == 0 else "transparent"
                name_fnt = T.FONT_BODY

            fecha_str = r["fecha"].strftime("%d %b %Y")
            prefix    = "★  " if is_latest else "    "
            bal_color = T.DANGER if balance < 0 else T.SUCCESS

            row_frame = ctk.CTkFrame(
                rows_frame, fg_color=row_bg, corner_radius=6)
            row_frame.pack(fill="x", pady=2)

            cells = [
                (f"{prefix}{fecha_str}", T.TEXT,           name_fnt),
                (f"#{vuelo}",           T.TEXT_MUTED,     T.FONT_BODY),
                (f"{corte:,.0f}",       T.CORTE_COLOR,    T.FONT_BODY),
                (f"{relleno:,.0f}",     T.RELLENO_COLOR,  T.FONT_BODY),
                (f"{balance:+,.0f}",    bal_color,        name_fnt),
                (delta_c_txt,           delta_c_col,      T.FONT_SMALL),
                (delta_r_txt,           delta_r_col,      T.FONT_SMALL),
            ]
            for col_i, ((cell_txt, cell_color, cell_font), col_w) in enumerate(
                zip(cells, [w for _, w in _COLS])
            ):
                ctk.CTkLabel(
                    row_frame, text=cell_txt,
                    font=cell_font, text_color=cell_color,
                    width=col_w, anchor="w",
                ).grid(row=0, column=col_i, sticky="w", padx=4, pady=7)

    # ── Acciones ─────────────────────────────────────────────────────────
    def _recalcular_frentes(self):
        fecha = self._fecha_seleccionada()

        # Validar insumos según el modo
        if fecha is None:
            # Modo objetivo: necesita dem_final
            if not all([self.state.dem_baseline_path(),
                        self._eje_path(),
                        self._dem_final_path()]):
                messagebox.showwarning(
                    "Insumos faltantes",
                    "Para calcular el volumen objetivo carga:\n"
                    "  · DEM Inicial\n  · Eje de la Vía\n  · DEM Final",
                )
                return
        else:
            # Modo avance real: necesita dz_acum del vuelo
            if not all([self.state.dem_baseline_path(), self._eje_path()]):
                messagebox.showwarning(
                    "Insumos faltantes",
                    "Carga el DEM Inicial y el Eje de la Vía antes de calcular.",
                )
                return
            from pathlib import Path
            dz_path = self.state.vuelos_dir / fecha / "dz_acum.tif"
            if not dz_path.exists():
                messagebox.showerror(
                    "Vuelo sin procesar",
                    f"No se encontró dz_acum.tif para la fecha {fecha}.\n\n"
                    "Ejecuta el pipeline para ese vuelo antes de calcular.",
                )
                return

        frentes = self.state.load_frentes()
        if not frentes:
            messagebox.showwarning(
                "Sin frentes",
                "Define al menos un frente de obra antes de recalcular.",
            )
            return

        titulo = (
            f"Calculando Volúmenes por Frente — {fecha}"
            if fecha else "Calculando Volúmenes por Frente — Objetivo (diseño)"
        )

        def _on_done(ok):
            self.after(0, self._refresh_resultados, ok)
            if ok and self.on_updated:
                self.after(200, self.on_updated)

        from .runner import ProcessDialog
        ProcessDialog(
            self.winfo_toplevel(),
            titulo=titulo,
            popen_factory=lambda: self.state.run_volumen_frentes(fecha),
            on_done=_on_done,
        )
