"""
App principal de Mensure v2.0 (CustomTkinter, tema claro).

Reproduce la sidebar del mockup:
    - Logo + marca arriba.
    - 8 items de navegación con icono.
    - Selector de proyecto.
    - Avatar de usuario con badge de estado.

Cada item activa una vista que se monta perezosamente en el panel principal.
"""
from __future__ import annotations

from pathlib import Path
import customtkinter as ctk

from . import theme as T
from .state import ProjectState
from .view_dashboard import DashboardView
from .view_placeholder import PlaceholderView


NAV = [
    ("dashboard",     "Dashboard",      "▦"),
    ("vuelos",        "Vuelos",         "✈"),
    ("dem",           "Modelos DEM",    "🗺"),
    ("volumenes",     "Volúmenes",      "📐"),
    ("equipos",       "Equipos",        "🚜"),
    ("rendimientos",  "Rendimientos",   "📈"),
    ("reportes",      "Reportes",       "📁"),
    ("config",        "Configuración",  "⚙"),
]


class App(ctk.CTk):
    def __init__(self, base: Path):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.state_ = ProjectState(base)
        self.title("Mensure v2.0 — Medición de Obra")
        self.geometry("1440x860")
        self.minsize(1180, 740)
        self.configure(fg_color=T.APP_BG)

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
        side = ctk.CTkFrame(self, width=240, corner_radius=0,
                             fg_color=T.SIDEBAR_BG, border_width=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)

        # Línea derecha (borde de la sidebar)
        ctk.CTkFrame(side, width=1,
                       fg_color=T.SIDEBAR_BORDER).place(
            relx=1.0, rely=0, relheight=1.0, x=-1)

        # Branding
        brand = ctk.CTkFrame(side, fg_color="transparent", height=70)
        brand.pack(fill="x", padx=22, pady=(22, 18))
        ctk.CTkLabel(brand, text="🛸", font=(T.FONT_FAMILY, 26),
                      text_color=T.PRIMARY).pack(side="left")
        bt = ctk.CTkFrame(brand, fg_color="transparent")
        bt.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(bt, text="Mensure",
                      font=(T.FONT_FAMILY, 16, "bold"),
                      text_color=T.TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(bt, text="v2.0",
                      font=T.FONT_TINY, text_color=T.TEXT_MUTED,
                      anchor="w").pack(anchor="w")

        # Items de navegación
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        for key, label, icon in NAV:
            b = ctk.CTkButton(
                side, text=f"   {icon}    {label}", anchor="w",
                height=40, corner_radius=8,
                fg_color="transparent", text_color=T.TEXT_MUTED,
                hover_color=T.HOVER_BG, font=T.FONT_BODY,
                command=lambda k=key: self.show(k),
            )
            b.pack(fill="x", padx=14, pady=2)
            self._nav_btns[key] = b

        # Selector de proyecto
        proj = ctk.CTkFrame(side, fg_color="#F9FAFB", corner_radius=8,
                              border_width=1, border_color=T.SIDEBAR_BORDER,
                              height=58)
        proj.pack(fill="x", padx=14, pady=(20, 6), side="bottom")
        proj.pack_propagate(False)
        ctk.CTkLabel(proj, text="PROYECTO", font=T.FONT_TINY,
                      text_color=T.TEXT_FAINT, anchor="w").pack(
            anchor="w", padx=12, pady=(8, 0))
        nombre = (self.state_.load_config() or {}).get(
            "nombre", "Proyecto Central")
        ctk.CTkLabel(proj, text=f"{nombre}   ⌄",
                      font=(T.FONT_FAMILY, 12, "bold"),
                      text_color=T.TEXT, anchor="w").pack(
            anchor="w", padx=12)

        # Usuario
        user = ctk.CTkFrame(side, fg_color="transparent", height=54)
        user.pack(fill="x", padx=14, pady=(0, 16), side="bottom")
        user.pack_propagate(False)

        av = ctk.CTkFrame(user, width=36, height=36, corner_radius=18,
                            fg_color=T.PRIMARY)
        av.pack(side="left", padx=(4, 10))
        av.pack_propagate(False)
        ctk.CTkLabel(av, text="JP", font=(T.FONT_FAMILY, 11, "bold"),
                      text_color="white").place(relx=0.5, rely=0.5,
                                                  anchor="center")
        ut = ctk.CTkFrame(user, fg_color="transparent")
        ut.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(ut, text="Juan Pérez",
                      font=(T.FONT_FAMILY, 11, "bold"),
                      text_color=T.TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(ut, text="Administrador",
                      font=T.FONT_TINY, text_color=T.TEXT_MUTED,
                      anchor="w").pack(anchor="w")

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color=T.APP_BG)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

    # ── Router ──────────────────────────────────────────────────────────
    def show(self, key: str):
        if key not in self._views:
            self._views[key] = self._construir_vista(key)
            self._views[key].grid(row=0, column=0, sticky="nsew")
        # Estado visual
        for k, b in self._nav_btns.items():
            if k == key:
                b.configure(fg_color="#EFF6FF", text_color=T.PRIMARY,
                             font=(T.FONT_FAMILY, 11, "bold"))
            else:
                b.configure(fg_color="transparent",
                             text_color=T.TEXT_MUTED, font=T.FONT_BODY)
        self._views[key].tkraise()
        v = self._views[key]
        if hasattr(v, "refresh"):
            v.refresh()
        self._current = key

    def _construir_vista(self, key: str) -> ctk.CTkFrame:
        if key == "dashboard":
            return DashboardView(self.main, self.state_)
        # Vistas pendientes — placeholders consistentes con el mockup
        return PlaceholderView(
            self.main, self.state_,
            title=dict(NAV)[key] if key in dict(NAV) else key.title(),
            description={
                "vuelos":       "Catálogo y procesado de vuelos / DEMs diarios.",
                "dem":          "Inventario de Modelos Digitales de Elevación.",
                "volumenes":    "Cubicación detallada y comparación de superficies.",
                "equipos":      "Gestión de la flota de maquinaria pesada.",
                "rendimientos": "Análisis de productividad por equipo y frente.",
                "reportes":     "Reportes Excel generados y descargas.",
                "config":       "Sistema de referencia (CRS), capas y objetivos.",
            }.get(key, ""),
        )


def main():
    base = Path(__file__).resolve().parent.parent
    app = App(base)
    app.mainloop()


if __name__ == "__main__":
    main()
