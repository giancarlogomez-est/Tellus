"""Vistas placeholder para las secciones aún no implementadas."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card


class PlaceholderView(ctk.CTkFrame):
    """Pantalla "en construcción" con título y mensaje."""

    def __init__(self, master, state: ProjectState,
                 title: str, description: str = ""):
        super().__init__(master, fg_color=T.APP_BG)
        self.state = state
        self._title_text = title
        self._desc_text = description
        self._build()

    def _build(self):
        SectionTitle(self, text=self._title_text).pack(
            anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self, text=self._desc_text or "Sección en construcción.",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
        ).pack(anchor="w", padx=24, pady=(0, 14))

        card = Card(self, title="Próximamente")
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        ctk.CTkLabel(
            card,
            text=(
                "🚧  Esta sección se conectará con el backend correspondiente\n"
                "(rasterio, maquinaria o exportación Excel) en la siguiente\n"
                "iteración del proyecto."
            ),
            font=T.FONT_BODY, text_color=T.TEXT_MUTED, justify="center",
        ).pack(expand=True, pady=40)

    def refresh(self):
        pass
