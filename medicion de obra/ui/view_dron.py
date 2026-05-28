"""Vista 'Comparativo Pre/Post': ejecuta calculo_volumen_odm.py."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card, Pill
from .runner import ProcessDialog


class DronView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self._build()
        self.refresh()

    def _build(self):
        SectionTitle(self, text="Comparativo Pre / Post (vuelo único)").pack(
            anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self, font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
            text=("Calcula volúmenes comparando dos DSM puntuales. "
                  "Usa esta vista para mediciones de un par de vuelos, "
                  "sin seguimiento continuo."),
        ).pack(anchor="w", padx=24, pady=(0, 14))

        card = Card(self, title="Archivos esperados en 02_dron_odm/")
        card.pack(fill="x", padx=20, pady=(0, 16))

        self.rows = ctk.CTkFrame(card, fg_color="transparent")
        self.rows.pack(fill="x", padx=18, pady=(0, 16))

        ctk.CTkLabel(card, font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                     justify="left", anchor="w",
                     text=("Ajusta los parámetros (EPSG, progresiva, ancho, etc.) "
                           "editando las constantes al inicio de "
                           "02_dron_odm/calculo_volumen_odm.py.")
                     ).pack(anchor="w", padx=18, pady=(0, 14))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(0, 20))
        self.btn = ctk.CTkButton(
            bar, text="▶  Ejecutar comparativo", height=44, width=220,
            font=T.FONT_H2, fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            command=self._ejecutar)
        self.btn.pack(side="right")

        ctk.CTkButton(
            bar, text="Generar DEMs de ejemplo", height=44, width=200,
            fg_color="transparent", border_width=1, border_color=T.PRIMARY,
            text_color=T.PRIMARY, hover_color=T.HOVER_BG,
            command=self._demo,
        ).pack(side="right", padx=(0, 10))

    def refresh(self):
        for w in self.rows.winfo_children():
            w.destroy()
        carpeta = self.state.odm_script.parent
        items = [
            ("dem_pre.tif",     "DSM del vuelo de referencia (antes)"),
            ("dem_post.tif",    "DSM del vuelo de medición (después)"),
            ("eje_via.dwg / .dxf / .geojson", "Eje del corredor"),
        ]
        completo = True
        for nombre, desc in items:
            existe = False
            if "/" in nombre:
                # caso multi-extensión
                for ext in ("dwg", "dxf", "geojson"):
                    if (carpeta / f"eje_via.{ext}").exists():
                        existe = True; break
            else:
                existe = (carpeta / nombre).exists()
            if not existe:
                completo = False

            row = ctk.CTkFrame(self.rows, fg_color="transparent")
            row.pack(fill="x", pady=3)
            Pill(row, "✓ OK" if existe else "✗ Falta",
                 color=T.SUCCESS if existe else T.DANGER).pack(side="left")
            ctk.CTkLabel(row, text=f"  {nombre}", font=T.FONT_BODY,
                          anchor="w").pack(side="left", padx=(6, 10))
            ctk.CTkLabel(row, text=desc, font=T.FONT_SMALL,
                          text_color=T.TEXT_MUTED, anchor="w").pack(side="left")

        self.btn.configure(state="normal" if completo else "disabled")

    def _ejecutar(self):
        ProcessDialog(
            self.winfo_toplevel(),
            titulo="Comparativo Pre/Post (Dron + ODM)",
            popen_factory=self.state.run_odm,
        )

    def _demo(self):
        if not messagebox.askyesno(
            "Generar DEMs de ejemplo",
            "Esto creará dem_pre.tif y dem_post.tif sintéticos en 02_dron_odm/. "
            "¿Continuar?"):
            return
        import subprocess, os
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        ProcessDialog(
            self.winfo_toplevel(),
            titulo="Generando DEMs de ejemplo",
            popen_factory=lambda: subprocess.Popen(
                [self.state.python_exe(), str(self.state.gen_dems_script)],
                cwd=str(self.state.gen_dems_script.parent), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, text=True, encoding="utf-8", errors="replace",
            ),
            on_done=lambda ok: (ok and self.refresh()),
        )
