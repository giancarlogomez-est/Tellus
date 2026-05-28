"""Vista 'Volúmenes': gestión de insumos base y cálculo de ΔZ / volúmenes."""
from __future__ import annotations

import shutil
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import theme as T
from .state import ProjectState
from .widgets import Card, SectionTitle, StatusBadge, UploadCard


# ═══════════════════════════════════════════════════════════════════════════
# Vista principal
# ═══════════════════════════════════════════════════════════════════════════
class VolumenesView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState):
        super().__init__(master, fg_color=T.APP_BG)
        self.state = state
        self._build()
        self.refresh()

    # ── Layout ──────────────────────────────────────────────────────────
    def _build(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=T.APP_BG)
        self.scroll.pack(fill="both", expand=True)
        self._build_header()
        self._build_upload_section()
        self._build_status_section()

    def _build_header(self):
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(18, 14))
        SectionTitle(hdr, text="Volúmenes", text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(
            hdr, font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
            text=("Carga los insumos base del proyecto. A partir del DEM inicial "
                  "y los DEMs diarios (cargados en Vuelos y modelos DEM) se "
                  "calcularán los ΔZ y volúmenes de corte/relleno por abscisa."),
            wraplength=860,
        ).pack(anchor="w")

    def _build_upload_section(self):
        card = Card(self.scroll, title="Insumos base del proyecto", light=True)
        card.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            card,
            text=("Haz clic en cada tarjeta para seleccionar el archivo. "
                  "Se copiarán automáticamente a la carpeta baseline/ del proyecto."),
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            wraplength=860,
        ).pack(anchor="w", padx=18, pady=(0, 16))

        cards_row = ctk.CTkFrame(card, fg_color="transparent")
        cards_row.pack(padx=18, pady=(0, 22))

        self._card_dem = UploadCard(
            cards_row, 1, "Terreno Natural",
            "DEM inicial  (GeoTIFF / XYZ)",
            on_upload=self._upload_dem,
        )
        self._card_dem.grid(row=0, column=0, padx=14, pady=6)

        self._card_eje = UploadCard(
            cards_row, 2, "Eje de la Vía",
            "Geometría del corredor  (DXF)",
            on_upload=self._upload_eje,
        )
        self._card_eje.grid(row=0, column=1, padx=14, pady=6)

        self._card_bordes = UploadCard(
            cards_row, 3, "Bordes Laterales",
            "Límites del área de trabajo  (DXF)",
            on_upload=self._upload_bordes,
        )
        self._card_bordes.grid(row=0, column=2, padx=14, pady=6)

    def _build_status_section(self):
        self._status_card = Card(
            self.scroll, title="Estado de los insumos", light=True)
        self._status_card.pack(fill="x", padx=20, pady=(0, 16))
        self._status_body = ctk.CTkFrame(
            self._status_card, fg_color="transparent")
        self._status_body.pack(fill="x", padx=18, pady=(0, 16))

        # Botones de acción
        btn_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 28))

        self.btn_calc = ctk.CTkButton(
            btn_row, text="▶  Calcular Volúmenes ΔZ",
            height=44, width=260,
            font=T.FONT_H2,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK,
            command=self._calcular,
            state="disabled",
        )
        self.btn_calc.pack(side="right")

        ctk.CTkButton(
            btn_row, text="Generar DEMs de ejemplo",
            height=44, width=220,
            fg_color="transparent", border_width=1,
            border_color=T.PRIMARY, text_color=T.PRIMARY,
            hover_color=T.HOVER_BG, font=T.FONT_BODY,
            command=self._demo,
        ).pack(side="right", padx=(0, 10))

    # ── Upload handlers ─────────────────────────────────────────────────
    def _upload_dem(self):
        path = filedialog.askopenfilename(
            title="Seleccionar DEM inicial",
            filetypes=[
                ("GeoTIFF / XYZ", "*.tif *.tiff *.xyz *.TIF *.TIFF"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not path:
            return
        try:
            dest = self._ensure_baseline() / "dem_baseline.tif"
            shutil.copy2(path, dest)
            self._card_dem.set_loaded(dest)
            self._refresh_status()
        except Exception as exc:
            messagebox.showerror("Error al copiar archivo", str(exc))

    def _upload_eje(self):
        path = filedialog.askopenfilename(
            title="Seleccionar eje de la vía",
            filetypes=[
                ("AutoCAD DXF", "*.dxf *.DXF"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not path:
            return
        try:
            dest = self._ensure_baseline() / "eje_via.dxf"
            shutil.copy2(path, dest)
            self._card_eje.set_loaded(dest)
            self._refresh_status()
        except Exception as exc:
            messagebox.showerror("Error al copiar archivo", str(exc))

    def _upload_bordes(self):
        path = filedialog.askopenfilename(
            title="Seleccionar bordes laterales",
            filetypes=[
                ("AutoCAD DXF", "*.dxf *.DXF"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not path:
            return
        try:
            dest = self._ensure_baseline() / "bordes_laterales.dxf"
            shutil.copy2(path, dest)
            self._card_bordes.set_loaded(dest)
            self._refresh_status()
        except Exception as exc:
            messagebox.showerror("Error al copiar archivo", str(exc))

    # ── Rutas de archivos ────────────────────────────────────────────────
    def _ensure_baseline(self) -> Path:
        d = self.state.baseline_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _eje_path(self) -> Path | None:
        bd = self.state.baseline_dir
        for ext in ("dxf", "DXF", "dwg", "DWG"):
            p = bd / f"eje_via.{ext}"
            if p.exists():
                return p
        return None

    def _bordes_path(self) -> Path | None:
        bd = self.state.baseline_dir
        for ext in ("dxf", "DXF"):
            p = bd / f"bordes_laterales.{ext}"
            if p.exists():
                return p
        return None

    # ── Refresco de estado ───────────────────────────────────────────────
    def _refresh_status(self):
        for w in self._status_body.winfo_children():
            w.destroy()

        dem    = self.state.dem_baseline_path()
        eje    = self._eje_path()
        bordes = self._bordes_path()

        items = [
            ("DEM Inicial",       "dem_baseline.tif",        dem),
            ("Eje de la Vía",     "eje_via.dxf",             eje),
            ("Bordes Laterales",  "bordes_laterales.dxf",    bordes),
        ]
        all_ok = True
        for nombre, archivo, path in items:
            ok = path is not None
            if not ok:
                all_ok = False
            row = ctk.CTkFrame(self._status_body, fg_color="transparent")
            row.pack(fill="x", pady=5)
            StatusBadge(row, "Cargado" if ok else "Falta",
                        kind="ok" if ok else "err").pack(side="left")
            ctk.CTkLabel(
                row, text=f"  {nombre}",
                font=(T.FONT_FAMILY, 12, "bold"),
                text_color=T.TEXT, anchor="w",
            ).pack(side="left", padx=(4, 6))
            ctk.CTkLabel(
                row, text=f"({archivo})" if not ok else str(path),
                font=T.FONT_TINY, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(side="left")

        self.btn_calc.configure(state="normal" if all_ok else "disabled")

    def refresh(self):
        dem    = self.state.dem_baseline_path()
        eje    = self._eje_path()
        bordes = self._bordes_path()
        self._card_dem.set_loaded(dem)
        self._card_eje.set_loaded(eje)
        self._card_bordes.set_loaded(bordes)
        self._refresh_status()

    # ── Acciones ─────────────────────────────────────────────────────────
    def _calcular(self):
        from .runner import ProcessDialog
        ProcessDialog(
            self.winfo_toplevel(),
            titulo="Calculando Volúmenes ΔZ",
            popen_factory=self.state.run_odm,
        )

    def _demo(self):
        if not messagebox.askyesno(
            "Generar DEMs de ejemplo",
            "Esto creará dem_pre.tif y dem_post.tif sintéticos en 02_dron_odm/.\n"
            "¿Continuar?",
        ):
            return
        import subprocess
        from .runner import ProcessDialog
        ProcessDialog(
            self.winfo_toplevel(),
            titulo="Generando DEMs de ejemplo",
            popen_factory=lambda: subprocess.Popen(
                [self.state.python_exe(), str(self.state.gen_dems_script)],
                cwd=str(self.state.gen_dems_script.parent),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ),
            on_done=lambda ok: (ok and self.refresh()),
        )
