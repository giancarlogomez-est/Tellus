"""Componentes UI reutilizables."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T


class KPICard(ctk.CTkFrame):
    """Tarjeta numérica grande: etiqueta arriba, valor enorme, unidad debajo."""

    def __init__(self, master, label: str, value: str = "—",
                 unit: str = "", accent: str = T.PRIMARY, **kw):
        super().__init__(master, corner_radius=12, border_width=1,
                         border_color="#374151", **kw)
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


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text: str, **kw):
        super().__init__(master, text=text, font=T.FONT_H1, anchor="w", **kw)


class Card(ctk.CTkFrame):
    """Contenedor con padding, borde sutil y título opcional."""

    def __init__(self, master, title: str | None = None, **kw):
        super().__init__(master, corner_radius=12, border_width=1,
                         border_color="#374151", **kw)
        if title:
            t = ctk.CTkLabel(self, text=title, font=T.FONT_H2, anchor="w")
            t.pack(fill="x", padx=18, pady=(14, 6))


class Pill(ctk.CTkLabel):
    """Etiqueta tipo badge (estado)."""

    def __init__(self, master, text: str, color: str = T.PRIMARY, **kw):
        super().__init__(
            master, text=f"  {text}  ", font=T.FONT_SMALL,
            corner_radius=10, fg_color=color, text_color="white",
            padx=8, pady=2, **kw,
        )
