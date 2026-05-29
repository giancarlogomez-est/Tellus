"""Vista 'Reportes': árbol de reportes y previsualización de heatmap."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card, Pill


_FECHA_DIA  = re.compile(r"reporte_(\d{4}-\d{2}-\d{2})\.xlsx$")
_SEMANA     = re.compile(r"reporte_(\d{4}-W\d{2})\.xlsx$")
_MES        = re.compile(r"reporte_(\d{4}-\d{2})\.xlsx$")


class ReportesView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self._seleccion: Path | None = None
        self._preview = None
        self._build()
        self.refresh()

    def _build(self):
        SectionTitle(self, text="Reportes generados").pack(
            anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self, font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
            text="Lista de Excel y heatmaps generados por el pipeline.",
        ).pack(anchor="w", padx=24, pady=(0, 14))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=1, uniform="rep")
        body.grid_columnconfigure(1, weight=2, uniform="rep")
        body.grid_rowconfigure(0, weight=1)

        # ── Columna izquierda: tabs por tipo de reporte ──────────────────
        izq = Card(body, title="Reportes disponibles")
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.tabs = ctk.CTkTabview(izq, height=400)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tabs.add("Diarios")
        self.tabs.add("Semanales")
        self.tabs.add("Mensuales")

        self.list_dia = self._lista_scroll(self.tabs.tab("Diarios"))
        self.list_sem = self._lista_scroll(self.tabs.tab("Semanales"))
        self.list_mes = self._lista_scroll(self.tabs.tab("Mensuales"))

        # ── Columna derecha: preview + acciones ──────────────────────────
        der = Card(body, title="Vista previa")
        der.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.preview_holder = ctk.CTkFrame(der, fg_color="transparent",
                                            height=320)
        self.preview_holder.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.info_lbl = ctk.CTkLabel(der, text="Selecciona un reporte a la izquierda",
                                      font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                                      anchor="w")
        self.info_lbl.pack(fill="x", padx=18, pady=(0, 8))

        bar = ctk.CTkFrame(der, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 14))
        self.btn_abrir = ctk.CTkButton(bar, text="Abrir en Excel", state="disabled",
                                        command=self._abrir_excel,
                                        fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV)
        self.btn_abrir.pack(side="left")
        self.btn_carpeta = ctk.CTkButton(bar, text="Mostrar en carpeta",
                                          state="disabled",
                                          command=self._abrir_carpeta,
                                          fg_color="transparent", border_width=1,
                                          border_color=T.PRIMARY, text_color=T.PRIMARY,
                                          hover_color=T.HOVER_BG)
        self.btn_carpeta.pack(side="left", padx=(8, 0))

    def _lista_scroll(self, parent):
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=340)
        frame.pack(fill="both", expand=True)
        return frame

    # ── Refresh ─────────────────────────────────────────────────────────
    def refresh(self):
        for holder, tipo, regex in [
            (self.list_dia, "diarios",   _FECHA_DIA),
            (self.list_sem, "semanales", _SEMANA),
            (self.list_mes, "mensuales", _MES),
        ]:
            for w in holder.winfo_children():
                w.destroy()
            archivos = self.state.listar_reportes(tipo)
            if not archivos:
                ctk.CTkLabel(holder, text="(sin reportes aún)",
                              font=T.FONT_BODY, text_color=T.TEXT_MUTED
                              ).pack(anchor="w", pady=8, padx=4)
                continue
            for path in archivos:
                m = regex.search(path.name)
                etiqueta = m.group(1) if m else path.stem
                btn = ctk.CTkButton(
                    holder, text=etiqueta, anchor="w",
                    height=32, corner_radius=6,
                    fg_color="transparent", text_color=T.TEXT,
                    hover_color=T.HOVER_BG,
                    command=lambda p=path: self._seleccionar(p),
                )
                btn.pack(fill="x", pady=2, padx=2)

    def _seleccionar(self, path: Path):
        self._seleccion = path
        self.btn_abrir.configure(state="normal")
        self.btn_carpeta.configure(state="normal")
        self.info_lbl.configure(text=path.name, text_color=T.TEXT)

        # Limpiar preview previo
        for w in self.preview_holder.winfo_children():
            w.destroy()

        # Buscar heatmap asociado si es diario
        m = _FECHA_DIA.search(path.name)
        if m:
            fecha = m.group(1)
            heat = self.state.heatmap_para_fecha(fecha)
            if heat:
                self._mostrar_imagen(heat)
                return
        # Para semanales/mensuales: buscar heatmap del mes
        m = _MES.search(path.name)
        if m:
            heat = path.parent / f"heatmap_{m.group(1)}.png"
            if heat.exists():
                self._mostrar_imagen(heat); return

        ctk.CTkLabel(
            self.preview_holder,
            text="(no hay heatmap PNG asociado a este reporte)",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED
        ).pack(expand=True)

    def _mostrar_imagen(self, ruta: Path):
        try:
            self.update_idletasks()
            ancho = max(self.preview_holder.winfo_width() - 20, 400)
            alto  = max(self.preview_holder.winfo_height() - 20, 300)
            img = Image.open(ruta)
            ratio = min(ancho / img.width, alto / img.height)
            size = (max(int(img.width * ratio), 100),
                    max(int(img.height * ratio), 80))
            ctkimg = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self._preview = ctkimg
            ctk.CTkLabel(self.preview_holder, image=ctkimg, text="").pack(
                expand=True)
        except Exception as e:
            ctk.CTkLabel(self.preview_holder, text=f"No se pudo abrir: {e}",
                          font=T.FONT_BODY, text_color=T.DANGER).pack(expand=True)

    def _abrir_excel(self):
        if not self._seleccion: return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(self._seleccion))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self._seleccion)])
            else:
                subprocess.Popen(["xdg-open", str(self._seleccion)])
        except Exception as e:
            print(e)

    def _abrir_carpeta(self):
        if not self._seleccion: return
        carpeta = self._seleccion.parent
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", str(self._seleccion)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(self._seleccion)])
            else:
                subprocess.Popen(["xdg-open", str(carpeta)])
        except Exception as e:
            print(e)
