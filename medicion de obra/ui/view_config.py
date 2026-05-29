"""Vista 'Configuración': formulario que edita proyecto_config.json."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card, Pill


EPSG_PRESETS = [
    ("9377",  "MAGNA-SIRGAS / Origen-Nacional (Colombia, recomendado)"),
    ("3116",  "MAGNA-SIRGAS / Bogotá zone"),
    ("3117",  "MAGNA-SIRGAS / East zone"),
    ("3114",  "MAGNA-SIRGAS / Far West zone"),
    ("3115",  "MAGNA-SIRGAS / West zone"),
    ("3118",  "MAGNA-SIRGAS / East of East zone"),
    ("32617", "WGS 84 / UTM 17N"),
    ("32618", "WGS 84 / UTM 18N"),
    ("32619", "WGS 84 / UTM 19N"),
    ("4326",  "WGS 84 geográfico (lat/lon)"),
]


def _row(parent, etiqueta: str, hint: str = "") -> ctk.CTkFrame:
    fr = ctk.CTkFrame(parent, fg_color="transparent")
    fr.pack(fill="x", pady=6)
    fr.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(fr, text=etiqueta, font=T.FONT_BODY,
                  width=220, anchor="w").grid(row=0, column=0, sticky="w")
    if hint:
        ctk.CTkLabel(fr, text=hint, font=T.FONT_SMALL,
                      text_color=T.TEXT_MUTED, anchor="w"
                      ).grid(row=1, column=1, sticky="w", padx=(8, 0))
    return fr


class ConfigView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState, on_saved=None):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self.on_saved = on_saved
        self._vars: dict[str, ctk.StringVar] = {}
        self._build()
        self.refresh()

    def _build(self):
        SectionTitle(self, text="Configuración del proyecto").pack(
            anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self, font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
            text="Estos parámetros se guardan en proyecto_config.json y los lee el pipeline.",
        ).pack(anchor="w", padx=24, pady=(0, 14))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 0))

        # ── Datos generales ─────────────────────────────────────────────
        card = Card(scroll, title="Datos generales")
        card.pack(fill="x", pady=(0, 14))
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=18, pady=(0, 14))

        self._campo(cont, "nombre",   "Nombre del proyecto")
        self._campo(cont, "tramo",    "Tramo / descripción", "ej. K0+000 – K0+300")
        self._campo(cont, "contrato", "N° de contrato (opcional)")

        # ── Geometría ───────────────────────────────────────────────────
        card = Card(scroll, title="Geometría del corredor")
        card.pack(fill="x", pady=(0, 14))
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=18, pady=(0, 14))

        self._campo(cont, "prog_inicio_m",        "Progresiva inicial (m)",
                    "5300 → K5+300", numeric=True)
        self._campo(cont, "espaciado_secciones",  "Espaciado entre secciones (m)",
                    numeric=True)
        self._campo(cont, "ancho_corredor",       "Ancho del corredor (m, a cada lado)",
                    numeric=True)

        # ── Proyección ──────────────────────────────────────────────────
        card = Card(scroll, title="Sistema de proyección")
        card.pack(fill="x", pady=(0, 14))
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=18, pady=(0, 14))

        fr = _row(cont, "Código EPSG", "")
        self._vars["epsg_proyecto"] = ctk.StringVar()
        opciones = [f"{e} — {desc}" for e, desc in EPSG_PRESETS]
        combo = ctk.CTkComboBox(
            fr, values=opciones, width=380,
            variable=self._vars["epsg_proyecto"])
        combo.grid(row=0, column=1, sticky="w", padx=(8, 0))

        # ── Volúmenes objetivo ──────────────────────────────────────────
        card = Card(scroll, title="Volúmenes objetivo y factores")
        card.pack(fill="x", pady=(0, 14))
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=18, pady=(0, 14))

        self._campo(cont, "vol_corte_objetivo",   "Volumen de corte objetivo (m³)",
                    numeric=True)
        self._campo(cont, "vol_relleno_objetivo", "Volumen de relleno objetivo (m³)",
                    numeric=True)
        self._campo(cont, "factor_esponjamiento", "Factor de esponjamiento",
                    numeric=True)
        self._campo(cont, "factor_contraccion",   "Factor de contracción",
                    numeric=True)
        self._campo(cont, "paso_muestreo_landxml", "Paso malla LandXML (2/4/8)",
                    numeric=True)

        # ── Baseline ────────────────────────────────────────────────────
        card = Card(scroll, title="Archivos baseline")
        card.pack(fill="x", pady=(0, 14))
        self.baseline_holder = ctk.CTkFrame(card, fg_color="transparent")
        self.baseline_holder.pack(fill="x", padx=18, pady=(0, 14))

        # ── Botones ─────────────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=14)
        ctk.CTkButton(bar, text="Guardar configuración",
                       fg_color=T.SUCCESS, hover_color=T.SUCCESS_HOV,
                       height=42, width=200,
                       command=self._guardar).pack(side="right")
        ctk.CTkButton(bar, text="Recargar",
                       fg_color="transparent", border_width=1,
                       border_color=T.PRIMARY, text_color=T.PRIMARY,
                       hover_color=T.HOVER_BG, height=42, width=120,
                       command=self.refresh).pack(side="right", padx=(0, 10))

    def _campo(self, parent, key: str, etiqueta: str, hint: str = "",
               numeric: bool = False):
        fr = _row(parent, etiqueta, hint)
        var = ctk.StringVar()
        self._vars[key] = var
        entry = ctk.CTkEntry(fr, textvariable=var, width=240)
        entry.grid(row=0, column=1, sticky="w", padx=(8, 0))
        if numeric:
            entry.configure(justify="right")

    # ── Datos ───────────────────────────────────────────────────────────
    def refresh(self):
        cfg = self.state.load_config() or {
            "nombre": "Mi Proyecto Vial",
            "tramo":  "K0+000 – K0+300",
            "contrato": "",
            "prog_inicio_m": 0,
            "espaciado_secciones": 20,
            "ancho_corredor": 28,
            "epsg_proyecto": 9377,
            "vol_corte_objetivo":  15000,
            "vol_relleno_objetivo": 25000,
            "factor_esponjamiento": 1.25,
            "factor_contraccion":   0.90,
            "paso_muestreo_landxml": 4,
        }
        for k, v in self._vars.items():
            val = cfg.get(k, "")
            if k == "epsg_proyecto":
                etiqueta = next((f"{e} — {d}" for e, d in EPSG_PRESETS
                                  if e == str(val)), str(val))
                v.set(etiqueta)
            else:
                v.set("" if val in (None, "") else str(val))

        # Estado de archivos baseline
        for w in self.baseline_holder.winfo_children():
            w.destroy()
        items = [
            (self.state.baseline_dir / "dem_baseline.tif",
             "dem_baseline.tif", "DSM del vuelo de referencia (antes de la obra)"),
        ]
        # Detectar eje (cualquiera de los formatos)
        encontrados = [
            self.state.baseline_dir / f"eje_via.{e}"
            for e in ("dxf", "dwg", "geojson")
            if (self.state.baseline_dir / f"eje_via.{e}").exists()
        ]
        if encontrados:
            items.append((encontrados[0], encontrados[0].name,
                          "Eje del corredor (detectado)"))
        else:
            items.append((self.state.baseline_dir / "eje_via.dxf",
                          "eje_via.dxf / .dwg / .geojson", "Eje del corredor"))

        for path, nombre, desc in items:
            row = ctk.CTkFrame(self.baseline_holder, fg_color="transparent")
            row.pack(fill="x", pady=3)
            existe = path.exists()
            Pill(row, "✓ OK" if existe else "✗ Falta",
                  color=T.SUCCESS if existe else T.DANGER).pack(side="left")
            ctk.CTkLabel(row, text=f"  {nombre}", font=T.FONT_BODY,
                          anchor="w").pack(side="left", padx=(6, 10))
            ctk.CTkLabel(row, text=desc, font=T.FONT_SMALL,
                          text_color=T.TEXT_MUTED, anchor="w").pack(side="left")

    def _guardar(self):
        cfg = self.state.load_config() or {}
        try:
            cfg["nombre"]   = self._vars["nombre"].get().strip() or "Proyecto"
            cfg["tramo"]    = self._vars["tramo"].get().strip()
            cfg["contrato"] = self._vars["contrato"].get().strip()
            cfg["prog_inicio_m"]       = float(self._vars["prog_inicio_m"].get() or 0)
            cfg["espaciado_secciones"] = float(self._vars["espaciado_secciones"].get() or 20)
            cfg["ancho_corredor"]      = float(self._vars["ancho_corredor"].get() or 28)
            cfg["vol_corte_objetivo"]   = float(self._vars["vol_corte_objetivo"].get() or 0)
            cfg["vol_relleno_objetivo"] = float(self._vars["vol_relleno_objetivo"].get() or 0)
            cfg["factor_esponjamiento"] = float(self._vars["factor_esponjamiento"].get() or 1.25)
            cfg["factor_contraccion"]   = float(self._vars["factor_contraccion"].get() or 0.90)
            cfg["paso_muestreo_landxml"] = int(float(
                self._vars["paso_muestreo_landxml"].get() or 4))

            epsg_str = self._vars["epsg_proyecto"].get().split(" ")[0]
            cfg["epsg_proyecto"] = int(epsg_str)

            # Asegurar defaults si vienen vacíos
            cfg.setdefault("dem_baseline", "baseline/dem_baseline.tif")
            cfg.setdefault("eje_via", "baseline/eje_via.dxf")
            cfg.setdefault("dz_min_plot", -3.0)
            cfg.setdefault("dz_max_plot",  3.0)
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return

        self.state.save_config(cfg)
        messagebox.showinfo("Guardado",
                            "Configuración guardada en proyecto_config.json")
        if self.on_saved:
            self.on_saved()
