"""Vista 'Configuración': formulario que edita proyecto_config.json."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card, Pill


SEP = " — "
EPSG_PRESETS = [
    ("EPSG:9377",   "MAGNA-SIRGAS 2018 / Origen Nacional (Colombia)"),
    ("ESRI:102233", "MAGNA Ciudad Bogotá (cartesiano local de Bogotá)"),
    ("EPSG:6247",   "MAGNA-SIRGAS / Bogotá urban grid"),
    ("EPSG:3116",   "MAGNA-SIRGAS / Colombia Bogotá zone"),
    ("EPSG:3117",   "MAGNA-SIRGAS / Colombia East Central zone"),
    ("EPSG:3115",   "MAGNA-SIRGAS / Colombia West zone"),
    ("EPSG:3114",   "MAGNA-SIRGAS / Colombia Far West zone"),
    ("EPSG:3118",   "MAGNA-SIRGAS / Colombia East zone"),
    ("EPSG:32617",  "WGS 84 / UTM 17N"),
    ("EPSG:32618",  "WGS 84 / UTM 18N"),
    ("EPSG:32619",  "WGS 84 / UTM 19N"),
]


def _nucleo(state):
    import sys
    if str(state.base) not in sys.path:
        sys.path.insert(0, str(state.base))
    import nucleo
    return nucleo


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
        self._campo(cont, "resolucion_trabajo",   "Resolución de cálculo (m/píxel)",
                    "0.5 recomendado · 0 = nativa del DEM", numeric=True)
        self._campo(cont, "umbral_dz",            "Umbral de ruido |ΔZ| (m)",
                    "cambios menores no suman volumen", numeric=True)

        # ── Proyección ──────────────────────────────────────────────────
        card = Card(scroll, title="Sistema de coordenadas")
        card.pack(fill="x", pady=(0, 14))
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=18, pady=(0, 14))

        fr = _row(cont, "Sistema del proyecto",
                  "Elige uno de la lista o escribe un código: EPSG:9377, ESRI:102233, 3116 …")
        self._vars["epsg_proyecto"] = ctk.StringVar()
        opciones = [f"{e}{SEP}{desc}" for e, desc in EPSG_PRESETS]
        combo = ctk.CTkComboBox(
            fr, values=opciones, width=440,
            variable=self._vars["epsg_proyecto"],
            command=lambda _=None: self._verificar_crs())
        combo.grid(row=0, column=1, sticky="w", padx=(8, 0))
        combo.bind("<Return>", lambda _e: self._verificar_crs())
        combo.bind("<FocusOut>", lambda _e: self._verificar_crs())

        fr = _row(cont, "", "")
        ctk.CTkButton(fr, text="Verificar", width=110, height=30,
                       fg_color="transparent", border_width=1,
                       border_color=T.PRIMARY, text_color=T.PRIMARY,
                       hover_color=T.HOVER_BG,
                       command=self._verificar_crs
                       ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkButton(fr, text="Detectar desde un GeoTIFF…", width=210, height=30,
                       fg_color="transparent", border_width=1,
                       border_color=T.PRIMARY, text_color=T.PRIMARY,
                       hover_color=T.HOVER_BG,
                       command=self._detectar_crs
                       ).grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._btn_crs_base = ctk.CTkButton(
            fr, text="Usar el del DEM de referencia", width=220, height=30,
            fg_color="transparent", border_width=1,
            border_color=T.PRIMARY, text_color=T.PRIMARY,
            hover_color=T.HOVER_BG,
            command=lambda: self._detectar_crs(
                self.state.baseline_dir / "dem_baseline.tif"))
        self._btn_crs_base.grid(row=0, column=3, sticky="w", padx=(8, 0))

        self._crs_valor = None          # definición completa cuando no hay código
        self._crs_estado = ctk.CTkLabel(
            cont, text="", font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            anchor="w", justify="left", wraplength=760)
        self._crs_estado.pack(fill="x", padx=(228, 0), pady=(2, 0))

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

    # ── Sistema de coordenadas ──────────────────────────────────────────
    def _texto_crs(self, valor) -> str:
        """Texto del desplegable para un valor guardado en la configuración."""
        nucleo = _nucleo(self.state)
        et = nucleo.etiqueta_crs(valor)
        if not et:
            return ""
        desc = next((d for e, d in EPSG_PRESETS if e == et), None)
        if desc is None:
            desc = nucleo.describir_crs(valor)["nombre"]
        return f"{et}{SEP}{desc}" if desc and desc != et else et

    def _valor_crs(self):
        """Valor a guardar según lo que hay escrito en el desplegable."""
        txt = self._vars["epsg_proyecto"].get().strip()
        if txt.startswith("personalizado") and self._crs_valor:
            return self._crs_valor
        self._crs_valor = None
        return _nucleo(self.state).normalizar_crs(txt.split(SEP)[0].strip())

    def _verificar_crs(self, avisar_dem: bool = True) -> dict:
        nucleo = _nucleo(self.state)
        info = nucleo.describir_crs(self._valor_crs())
        texto = ("✓ " if info["ok"] else "✗ ") + info["mensaje"]
        color = T.SUCCESS if info["ok"] else T.DANGER
        if info["ok"]:
            self._vars["epsg_proyecto"].set(self._texto_crs(info["valor"]))
            dem = self.state.baseline_dir / "dem_baseline.tif"
            if avisar_dem and dem.exists():
                try:
                    del_dem = nucleo.crs_de_archivo(dem)
                except nucleo.EntradaInvalida:
                    del_dem = None
                if del_dem is not None and not nucleo._mismo_crs(
                        nucleo.resolver_crs(del_dem), nucleo.resolver_crs(info["valor"])):
                    texto += (f"\n⚠ El DEM de referencia está en "
                              f"{nucleo.etiqueta_crs(del_dem)}: no coincide con el "
                              "sistema elegido. El cálculo se hace en el sistema del "
                              "DEM y el eje se reproyecta desde el sistema elegido.")
                    color = T.DANGER
        self._crs_estado.configure(text=texto, text_color=color)
        return info

    def _detectar_crs(self, path=None):
        if path is None:
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="GeoTIFF del que leer el sistema de coordenadas",
                filetypes=[("GeoTIFF (ortofoto o modelo de elevación)", "*.tif *.tiff"),
                           ("Todos los archivos", "*.*")])
            if not path:
                return
        nucleo = _nucleo(self.state)
        try:
            valor = nucleo.crs_de_archivo(path)
        except nucleo.EntradaInvalida as e:
            messagebox.showerror("No se pudo leer", str(e))
            return
        if valor is None:
            messagebox.showwarning(
                "Sin sistema de coordenadas",
                "El archivo no trae sistema de coordenadas. Elígelo de la lista "
                "o escribe su código.")
            return
        self._crs_valor = valor
        self._vars["epsg_proyecto"].set(self._texto_crs(valor))
        self._verificar_crs()

    # ── Datos ───────────────────────────────────────────────────────────
    def refresh(self):
        cfg = self.state.load_config() or {
            "nombre": "Mi Proyecto Vial",
            "tramo":  "K0+000 – K0+300",
            "contrato": "",
            "prog_inicio_m": 0,
            "espaciado_secciones": 20,
            "ancho_corredor": 28,
            "resolucion_trabajo": 0.5,
            "umbral_dz": 0.05,
            "epsg_proyecto": 9377,
            "vol_corte_objetivo":  15000,
            "vol_relleno_objetivo": 25000,
            "factor_esponjamiento": 1.25,
            "factor_contraccion":   0.90,
            "paso_muestreo_landxml": 4,
        }
        for k, v in self._vars.items():
            val = cfg.get(k, {"resolucion_trabajo": 0.5, "umbral_dz": 0.05}.get(k, ""))
            if k == "epsg_proyecto":
                self._crs_valor = val if isinstance(val, str) else None
                v.set(self._texto_crs(val))
            else:
                v.set("" if val in (None, "") else str(val))
        self._btn_crs_base.configure(
            state="normal" if (self.state.baseline_dir / "dem_baseline.tif").exists()
            else "disabled")
        self._verificar_crs()

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
            cfg["resolucion_trabajo"]  = float(self._vars["resolucion_trabajo"].get() or 0)
            cfg["umbral_dz"]           = float(self._vars["umbral_dz"].get() or 0)
            cfg["vol_corte_objetivo"]   = float(self._vars["vol_corte_objetivo"].get() or 0)
            cfg["vol_relleno_objetivo"] = float(self._vars["vol_relleno_objetivo"].get() or 0)
            cfg["factor_esponjamiento"] = float(self._vars["factor_esponjamiento"].get() or 1.25)
            cfg["factor_contraccion"]   = float(self._vars["factor_contraccion"].get() or 0.90)
            cfg["paso_muestreo_landxml"] = int(float(
                self._vars["paso_muestreo_landxml"].get() or 4))

            info_crs = self._verificar_crs()
            if not info_crs["ok"]:
                raise ValueError("Sistema de coordenadas: " + info_crs["mensaje"])
            cfg["epsg_proyecto"] = info_crs["valor"]

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
