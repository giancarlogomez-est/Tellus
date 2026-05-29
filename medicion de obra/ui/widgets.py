"""Componentes UI reutilizables."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from . import theme as T


# ═══════════════════════════════════════════════════════════════════════════
# KPI Cards
# ═══════════════════════════════════════════════════════════════════════════
class KPICard(ctk.CTkFrame):
    """Tarjeta numérica grande: etiqueta arriba, valor enorme, unidad debajo."""

    def __init__(self, master, label: str, value: str = "—",
                 unit: str = "", accent: str = T.PRIMARY, **kw):
        super().__init__(master, corner_radius=12, border_width=1,
                         border_color=T.CARD_BORDER, **kw)
        self._accent = accent

        self.lbl = ctk.CTkLabel(self, text=label.upper(),
                                font=T.FONT_KPI_LBL, text_color=T.TEXT_MUTED)
        self.lbl.pack(anchor="w", padx=18, pady=(14, 0))

        self.val = ctk.CTkLabel(self, text=value,
                                font=T.FONT_KPI, text_color=accent)
        self.val.pack(anchor="w", padx=18, pady=(2, 0))

        self.unit = ctk.CTkLabel(self, text=unit,
                                 font=T.FONT_SMALL, text_color=T.TEXT_MUTED)
        self.unit.pack(anchor="w", padx=18, pady=(0, 14))

    def set(self, value: str, unit: str | None = None, accent: str | None = None):
        self.val.configure(text=value)
        if unit is not None:
            self.unit.configure(text=unit)
        if accent is not None:
            self.val.configure(text_color=accent)
            self._accent = accent


class KPICardIcon(ctk.CTkFrame):
    """KPI con chip de icono coloreado a la izquierda (estilo mockup)."""

    def __init__(self, master, icon: str, chip: str,
                 label: str, value: str = "—",
                 delta: str = "", delta_up: bool = True,
                 delta_suffix: str = "vs ayer", **kw):
        super().__init__(master, corner_radius=12, border_width=1,
                         border_color=T.CARD_BORDER, fg_color=T.CARD_BG,
                         height=96, **kw)
        self.grid_propagate(False)
        chip_bg, chip_fg = T.CHIP.get(chip, T.CHIP["dark"])

        chip_box = ctk.CTkFrame(self, width=44, height=44, corner_radius=10,
                                fg_color=chip_bg)
        chip_box.place(x=18, y=20)
        chip_box.pack_propagate(False)
        ctk.CTkLabel(chip_box, text=icon,
                     font=(T.FONT_FAMILY, 18, "bold"),
                     text_color=chip_fg).place(relx=0.5, rely=0.5,
                                               anchor="center")

        tx = 78
        self.lbl = ctk.CTkLabel(self, text=label, font=T.FONT_KPI_LBL,
                                text_color=T.TEXT_MUTED, anchor="w")
        self.lbl.place(x=tx, y=12)
        self.val = ctk.CTkLabel(self, text=value, font=T.FONT_KPI,
                                text_color=T.TEXT, anchor="w")
        self.val.place(x=tx, y=36)
        color = T.SUCCESS if delta_up else T.DANGER
        self.delta = ctk.CTkLabel(
            self, font=T.FONT_SMALL, text_color=color, anchor="w",
            text=(f"{delta}    {delta_suffix}" if delta else ""),
        )
        self.delta.place(x=tx, y=70)

    def set_value(self, value: str, delta: str = "",
                  delta_up: bool = True,
                  delta_suffix: str = "vs ayer") -> None:
        self.val.configure(text=value)
        color = T.SUCCESS if delta_up else T.DANGER
        self.delta.configure(
            text=(f"{delta}    {delta_suffix}" if delta else ""),
            text_color=color,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Contenedores
# ═══════════════════════════════════════════════════════════════════════════
class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text: str, **kw):
        super().__init__(master, text=text, font=T.FONT_H1, anchor="w", **kw)


class Card(ctk.CTkFrame):
    """Contenedor con padding, borde sutil, título y acción opcionales."""

    def __init__(self, master, title: str | None = None,
                 action_text: str | None = None, action_cmd=None,
                 light: bool = False, **kw):
        if light:
            kw.setdefault("fg_color", T.CARD_BG)
            kw.setdefault("border_color", T.CARD_BORDER)
        else:
            kw.setdefault("border_color", T.CARD_BORDER)
        super().__init__(master, corner_radius=12, border_width=1, **kw)
        if title:
            header = ctk.CTkFrame(self, fg_color="transparent", height=36)
            header.pack(fill="x", padx=18, pady=(14, 4))
            header.pack_propagate(False)
            title_color = T.TEXT if light else None
            t = ctk.CTkLabel(header, text=title, font=T.FONT_H2,
                             anchor="w",
                             **({"text_color": title_color}
                                if title_color else {}))
            t.pack(side="left")
            if action_text:
                ctk.CTkButton(
                    header, text=action_text, font=T.FONT_SMALL,
                    fg_color="transparent", hover_color=T.HOVER_BG,
                    text_color=T.PRIMARY, width=10,
                    command=action_cmd or (lambda: None),
                ).pack(side="right")


# ═══════════════════════════════════════════════════════════════════════════
# Badges / pills
# ═══════════════════════════════════════════════════════════════════════════
class Pill(ctk.CTkLabel):
    """Etiqueta tipo badge (estado)."""

    def __init__(self, master, text: str, color: str = T.PRIMARY, **kw):
        super().__init__(
            master, text=f"  {text}  ", font=T.FONT_SMALL,
            corner_radius=10, fg_color=color, text_color="white",
            padx=8, pady=2, **kw,
        )


class StatusBadge(ctk.CTkLabel):
    """Pill estilo mockup: verde 'Activo', 'Procesado', etc."""

    def __init__(self, master, text: str, kind: str = "ok", **kw):
        bg, fg = {
            "ok":   ("#E7F7EE", "#10B981"),
            "warn": ("#FFF3E6", "#F59E0B"),
            "err":  ("#FEE2E2", "#EF4444"),
        }.get(kind, ("#E7F7EE", "#10B981"))
        super().__init__(
            master, text=f"  ● {text}  ", font=T.FONT_TINY,
            corner_radius=10, fg_color=bg, text_color=fg, **kw,
        )


# ═══════════════════════════════════════════════════════════════════════════
# DataTable (sin scroll)
# ═══════════════════════════════════════════════════════════════════════════
class DataTable(ctk.CTkFrame):
    """Tabla ligera estilo dashboard."""

    def __init__(self, master, columns: list[str],
                 widths: list[int] | None = None, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.columns = columns
        self.widths = widths or [120] * len(columns)
        for i, w in enumerate(self.widths):
            self.grid_columnconfigure(i, weight=w, uniform="col")

        for i, col in enumerate(columns):
            ctk.CTkLabel(
                self, text=col.upper(), font=T.FONT_TINY,
                text_color=T.TEXT_MUTED, anchor="w",
            ).grid(row=0, column=i, sticky="ew", padx=8, pady=(0, 6))
        sep = ctk.CTkFrame(self, height=1, fg_color=T.CARD_BORDER)
        sep.grid(row=1, column=0, columnspan=len(columns),
                 sticky="ew", padx=0, pady=(0, 2))
        self._row = 2

    def add_row(self, cells: list) -> None:
        for i, cell in enumerate(cells):
            if isinstance(cell, str):
                widget = ctk.CTkLabel(
                    self, text=cell, font=T.FONT_BODY,
                    text_color=T.TEXT, anchor="w",
                )
            else:
                widget = cell
            widget.grid(row=self._row, column=i, sticky="ew",
                        padx=8, pady=6)
        self._row += 1


# ═══════════════════════════════════════════════════════════════════════════
# Progress item (Avance por Frente)
# ═══════════════════════════════════════════════════════════════════════════
class ProgressItem(ctk.CTkFrame):
    def __init__(self, master, label: str, pct: float,
                 color: str = T.PRIMARY, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(row, text=label, font=T.FONT_BODY,
                     text_color=T.TEXT, anchor="w").pack(side="left")
        ctk.CTkLabel(
            row, text=f"{pct:.1f}%",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT, anchor="e",
        ).pack(side="right")

        bar = ctk.CTkProgressBar(
            self, height=6, progress_color=color,
            fg_color=T.HOVER_BG, corner_radius=3,
        )
        bar.set(min(max(pct / 100, 0.0), 1.0))
        bar.pack(fill="x", pady=(0, 14))


# ═══════════════════════════════════════════════════════════════════════════
# UploadCard  (borde punteado ámbar + icono OVNI)
# ═══════════════════════════════════════════════════════════════════════════
_UPLOAD_AMBER  = "#F59E0B"
_UPLOAD_CARD_W = 210
_UPLOAD_CARD_H = 210


class UploadCard(tk.Frame):
    """Tarjeta cuadrada con borde punteado ámbar, icono OVNI y chip de archivo.

    Parámetros
    ----------
    number      Número que aparece junto al nombre (ej. 1, 2, 3). Usa 0 para omitirlo.
    label       Nombre descriptivo de la tarjeta.
    fmt         Línea de formato/extensión (texto secundario).
    on_upload   Callable sin argumentos que se invoca al hacer clic.
    loaded_path Ruta del archivo cargado actualmente (None = sin archivo).
    """

    def __init__(self, master, number: int, label: str, fmt: str,
                 on_upload, loaded_path: "Path | None" = None,
                 icon: str = "📂", **kw):
        bg = T.mc(T.CARD_BG)
        super().__init__(master, width=_UPLOAD_CARD_W, height=_UPLOAD_CARD_H,
                         bg=bg, **kw)
        self.pack_propagate(False)
        self._on_upload = on_upload

        self._canvas = tk.Canvas(self, width=_UPLOAD_CARD_W, height=_UPLOAD_CARD_H,
                                 bg=bg, highlightthickness=0, cursor="hand2")
        self._canvas.place(x=0, y=0)
        self._draw_border(loaded_path is not None)

        # Ícono personalizable
        self._canvas.create_text(
            _UPLOAD_CARD_W // 2, 68,
            text=icon, font=("Segoe UI Emoji", 34),
            fill=_UPLOAD_AMBER, tags="click",
        )
        # Número + nombre
        prefix = f"{number}. " if number else ""
        self._canvas.create_text(
            _UPLOAD_CARD_W // 2, 122,
            text=f"{prefix}{label}",
            font=("Segoe UI", 11, "bold"),
            fill=T.mc(T.TEXT),
            width=_UPLOAD_CARD_W - 24, tags="click",
        )
        # Formato / extensión
        self._canvas.create_text(
            _UPLOAD_CARD_W // 2, 144,
            text=fmt, font=("Segoe UI", 8),
            fill=T.mc(T.TEXT_MUTED), tags="click",
        )
        # Chip de archivo (fondo + texto)
        self._canvas.create_rectangle(
            14, _UPLOAD_CARD_H - 34, _UPLOAD_CARD_W - 14, _UPLOAD_CARD_H - 14,
            fill=T.mc(T.HOVER_BG), outline="", tags="click",
        )
        self._chip = self._canvas.create_text(
            _UPLOAD_CARD_W // 2, _UPLOAD_CARD_H - 24,
            text=self._fmt_name(loaded_path),
            font=("Segoe UI", 8),
            fill=T.mc(T.SUCCESS if loaded_path else T.TEXT_MUTED),
            width=_UPLOAD_CARD_W - 36, tags="click",
        )

        self._canvas.tag_bind("click", "<Button-1>", lambda e: self._on_upload())
        self._canvas.bind("<Button-1>", lambda e: self._on_upload())

    # ── API pública ──────────────────────────────────────────────────────
    def set_loaded(self, p: "Path | None"):
        self._draw_border(p is not None)
        self._canvas.itemconfigure(
            self._chip,
            text=self._fmt_name(p),
            fill=T.mc(T.SUCCESS if p else T.TEXT_MUTED),
        )

    # ── Helpers ──────────────────────────────────────────────────────────
    def _draw_border(self, loaded: bool):
        self._canvas.delete("border")
        color = T.mc(T.SUCCESS) if loaded else _UPLOAD_AMBER
        m = 6
        self._canvas.create_rectangle(
            m, m, _UPLOAD_CARD_W - m, _UPLOAD_CARD_H - m,
            outline=color, width=2, dash=(6, 4), tags="border",
        )

    @staticmethod
    def _fmt_name(p: "Path | None") -> str:
        if p is None:
            return "Sin archivo  —  haz clic para cargar"
        n = p.name
        return n if len(n) <= 28 else n[:25] + "…"
