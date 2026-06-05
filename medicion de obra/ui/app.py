"""Aplicación principal con sidebar y router de vistas."""
from __future__ import annotations

import sys
from pathlib import Path
import customtkinter as ctk
from PIL import Image

from . import theme as T
from .state import ProjectState
from .view_dashboard import DashboardView
from .view_diario import DiarioView
from .view_dron import VolumenesView
from .view_equipos import EquiposView
from .view_reportes import ReportesView
from .view_config import ConfigView


NAV = [
    ("dashboard", "Dashboard",           "📊"),
    ("diario",    "Vuelos y modelos DEM","✈"),
    ("dron",      "Volúmenes",           "📐"),
    ("equipos",   "Equipos y Rendtos.",  "🚜"),
    ("reportes",  "Reportes",            "📁"),
    ("config",    "Configuración",       "⚙"),
]


class App(ctk.CTk):
    def __init__(self, base: Path):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.state_ = ProjectState(base)
        self.title("TELLUS — Medición de Volúmenes en Obras Viales")
        self.geometry("1280x780")
        self.minsize(1100, 680)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._views: dict[str, ctk.CTkFrame] = {}
        self._current: str | None = None
        self.show("dashboard")

    # ── Sidebar ─────────────────────────────────────────────────────────
    def _build_sidebar(self):
        side = ctk.CTkFrame(self, width=230, corner_radius=0,
                             fg_color=T.SIDEBAR_BG)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)

        # Branding — logo + nombre
        logo_path = (
            Path(sys._MEIPASS) / "ui" / "logoTELLUS.png"
            if getattr(sys, "frozen", False)
            else Path(__file__).parent / "logoTELLUS.png"
        )
        brand_frame = ctk.CTkFrame(side, fg_color="transparent")
        brand_frame.pack(fill="x", padx=14, pady=(18, 0))
        if logo_path.exists():
            pil_img = Image.open(logo_path)
            ctk_logo = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(42, 28))
            ctk.CTkLabel(brand_frame, image=ctk_logo, text="  TELLUS",
                         compound="left", font=(T.FONT_FAMILY, 18, "bold"),
                         text_color=T.TEXT, anchor="w").pack(fill="x")
        else:
            ctk.CTkLabel(brand_frame, text="TELLUS",
                         font=(T.FONT_FAMILY, 18, "bold"),
                         text_color=T.TEXT, anchor="w").pack(fill="x")
        sub = ctk.CTkLabel(side, text="Avance de obras viales",
                            font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                            anchor="w")
        sub.pack(fill="x", padx=22, pady=(2, 26))

        self._nav_btns: dict[str, ctk.CTkButton] = {}
        for key, label, icon in NAV:
            b = ctk.CTkButton(
                side, text=f"  {icon}   {label}", anchor="w",
                height=42, corner_radius=8,
                fg_color="transparent", text_color=T.TEXT_MUTED,
                hover_color=T.HOVER_BG, font=T.FONT_BODY,
                command=lambda k=key: self.show(k),
            )
            b.pack(fill="x", padx=14, pady=2)
            self._nav_btns[key] = b

        # Pie de sidebar
        footer = ctk.CTkFrame(side, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=14, pady=14)
        self.tema_var = ctk.StringVar(value="Claro")
        ctk.CTkOptionMenu(
            footer, values=["Oscuro", "Claro", "Sistema"],
            variable=self.tema_var, command=self._cambiar_tema,
            fg_color=T.INPUT_BG, button_color=T.INPUT_BG,
            button_hover_color=T.INPUT_HOVER, text_color=T.TEXT,
            dropdown_fg_color=T.CARD_BG, dropdown_text_color=T.TEXT,
        ).pack(fill="x", pady=(0, 6))

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color=T.MAIN_BG)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

    # ── Router ──────────────────────────────────────────────────────────
    def show(self, key: str):
        if key not in self._views:
            self._views[key] = self._construir_vista(key)
            self._views[key].grid(row=0, column=0, sticky="nsew")
        for k, b in self._nav_btns.items():
            if k == key:
                b.configure(fg_color=T.PRIMARY, text_color=T.TEXT_ON_DARK)
            else:
                b.configure(fg_color="transparent", text_color=T.TEXT_MUTED)
        self._views[key].tkraise()
        # Refrescar la vista cada vez que se entra
        v = self._views[key]
        if hasattr(v, "refresh"):
            v.refresh()
        self._current = key

    def _construir_vista(self, key: str) -> ctk.CTkFrame:
        if key == "dashboard":
            return DashboardView(self.main, self.state_, navigate=self.show)
        if key == "diario":
            return DiarioView(self.main, self.state_,
                              on_processed=self._refresh_all)
        if key == "equipos":
            return EquiposView(self.main, self.state_,
                               on_updated=self._refresh_all)
        if key == "dron":
            return VolumenesView(self.main, self.state_, on_updated=self._refresh_all)
        if key == "reportes":
            return ReportesView(self.main, self.state_)
        if key == "config":
            return ConfigView(self.main, self.state_,
                              on_saved=self._refresh_all)
        raise ValueError(key)

    def _refresh_all(self):
        for v in self._views.values():
            if hasattr(v, "refresh"):
                try: v.refresh()
                except Exception: pass

    def _cambiar_tema(self, valor: str):
        m = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}
        ctk.set_appearance_mode(m.get(valor, "dark"))
        # Re-renderizar vistas con figuras matplotlib (no conmutan solas)
        self._refresh_all()


def main():
    import sys
    if getattr(sys, "frozen", False):
        # Ejecutando como .exe de PyInstaller — datos junto al ejecutable
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    app = App(base)
    app.mainloop()


if __name__ == "__main__":
    main()
