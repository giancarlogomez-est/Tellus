"""Vista 'Volúmenes': frentes de obra y cálculo de ΔZ."""
from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

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
        self._build_header()
        self._build_frentes_section()
        self._build_resultados_section()

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
            width=190, height=34, font=T.FONT_BODY,
        )
        self._ent_nombre.grid(row=0, column=0, padx=(0, 8))

        self._ent_abs_ini = ctk.CTkEntry(
            form, placeholder_text="Abscisa inicio (m)",
            width=150, height=34, font=T.FONT_BODY,
        )
        self._ent_abs_ini.grid(row=0, column=1, padx=(0, 8))

        self._ent_abs_fin = ctk.CTkEntry(
            form, placeholder_text="Abscisa fin (m)",
            width=150, height=34, font=T.FONT_BODY,
        )
        self._ent_abs_fin.grid(row=0, column=2, padx=(0, 8))

        ctk.CTkButton(
            form, text="+ Agregar", width=110, height=34,
            font=T.FONT_BODY,
            fg_color=T.SUCCESS, hover_color=T.SUCCESS_HOV,
            text_color="white",
            command=self._add_frente,
        ).grid(row=0, column=3)

        # ── Divisor ───────────────────────────────────────────────────
        ctk.CTkFrame(card, height=1, fg_color=T.CARD_BORDER).pack(
            fill="x", padx=18, pady=(8, 6))

        # ── Lista dinámica de frentes ──────────────────────────────────
        self._frentes_list_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._frentes_list_frame.pack(fill="x", padx=18, pady=(0, 8))

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

    # ── Resultados por frente ────────────────────────────────────────────
    def _build_resultados_section(self):
        self._res_card = Card(
            self.scroll, title="Resultados por frente", light=True)
        self._res_card.pack(fill="x", padx=20, pady=(0, 32))
        self._res_body = ctk.CTkFrame(self._res_card, fg_color="transparent")
        self._res_body.pack(fill="x", padx=18, pady=(0, 16))
        self._refresh_resultados()

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
        pass

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
            ("NOMBRE",    220, "w"),
            ("INICIO",    120, "w"),
            ("FIN",       120, "w"),
            ("LONGITUD",  110, "w"),
            ("",           48, "center"),
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
                text_color=T.TEXT, width=220, anchor="w",
            ).grid(row=0, column=0, padx=4, pady=6)

            ctk.CTkLabel(
                row, text=_km_str(abs_ini),
                font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                width=120, anchor="w",
            ).grid(row=0, column=1, padx=4)

            ctk.CTkLabel(
                row, text=_km_str(abs_fin),
                font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                width=120, anchor="w",
            ).grid(row=0, column=2, padx=4)

            ctk.CTkLabel(
                row, text=f"{longitud:,.0f} m",
                font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                width=110, anchor="w",
            ).grid(row=0, column=3, padx=4)

            def _make_del(idx=i):
                return lambda: self._remove_frente(idx)

            ctk.CTkButton(
                row, text="✕", width=32, height=26,
                fg_color="transparent",
                hover_color=("#FEE2E2", "#7F1D1D"),
                text_color=T.DANGER,
                font=(T.FONT_FAMILY, 11, "bold"),
                command=_make_del(),
            ).grid(row=0, column=4, padx=(0, 4))

    def _add_frente(self):
        nombre      = self._ent_nombre.get().strip()
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
        frentes.append({"nombre": nombre, "abs_ini": abs_ini, "abs_fin": abs_fin})
        self.state.save_frentes(frentes)

        self._ent_nombre.delete(0, "end")
        self._ent_abs_ini.delete(0, "end")
        self._ent_abs_fin.delete(0, "end")
        self._refresh_frentes_ui()
        if self.on_updated:
            self.on_updated()

    def _remove_frente(self, idx: int):
        frentes = self.state.load_frentes()
        if 0 <= idx < len(frentes):
            frentes.pop(idx)
            self.state.save_frentes(frentes)
            self._refresh_frentes_ui()
            if self.on_updated:
                self.on_updated()

    # ── Resultados ───────────────────────────────────────────────────────
    def _refresh_resultados(self, ok: bool = True):
        for w in self._res_body.winfo_children():
            w.destroy()

        resultados = self.state.load_frentes_resultado()

        if not resultados:
            ctk.CTkLabel(
                self._res_body,
                text=(
                    "Sin resultados. Carga los tres insumos, define al menos un frente "
                    "y haz clic en '⟳ Recalcular'."
                ),
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w", pady=14)
            return

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

    # ── Acciones ─────────────────────────────────────────────────────────
    def _recalcular_frentes(self):
        if not all([self.state.dem_baseline_path(),
                    self._eje_path(),
                    self._dem_final_path()]):
            messagebox.showwarning(
                "Insumos faltantes",
                "Carga el DEM Inicial, Eje de la Vía y DEM Final antes de calcular.",
            )
            return

        frentes = self.state.load_frentes()
        if not frentes:
            messagebox.showwarning(
                "Sin frentes",
                "Define al menos un frente de obra antes de recalcular.",
            )
            return

        def _on_done(ok):
            self.after(0, self._refresh_resultados, ok)
            if ok and self.on_updated:
                self.after(200, self.on_updated)

        from .runner import ProcessDialog
        ProcessDialog(
            self.winfo_toplevel(),
            titulo="Calculando Volúmenes por Frente",
            popen_factory=self.state.run_volumen_frentes,
            on_done=_on_done,
        )
