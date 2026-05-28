"""Vista 'Vuelo diario': procesa el DSM del día con pipeline.py."""
from __future__ import annotations

from datetime import date
import customtkinter as ctk
from tkinter import messagebox

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card, Pill
from .runner import ProcessDialog


class DiarioView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState, on_processed=None):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self.on_processed = on_processed
        self._build()
        self.refresh()

    def _build(self):
        SectionTitle(self, text="Procesar vuelo diario").pack(
            anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(self, font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                     text=("Selecciona la fecha del vuelo. Debes haber copiado "
                           "previamente el DSM a vuelos/<fecha>/dsm.tif."),
                     anchor="w").pack(anchor="w", padx=24, pady=(0, 14))

        # ── Tarjeta selector ─────────────────────────────────────────────
        sel = Card(self, title="Vuelo a procesar")
        sel.pack(fill="x", padx=20, pady=(0, 16))

        row = ctk.CTkFrame(sel, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkLabel(row, text="Fecha del vuelo", font=T.FONT_BODY).pack(
            side="left", padx=(0, 12))

        self.combo_fecha = ctk.CTkComboBox(
            row, values=[], width=200,
            command=lambda _=None: self._actualizar_estado_fecha())
        self.combo_fecha.pack(side="left", padx=(0, 16))

        ctk.CTkButton(row, text="↻", width=36,
                      command=self.refresh).pack(side="left", padx=(0, 16))

        self.pill_estado = Pill(row, "—", color=T.TEXT_MUTED)
        self.pill_estado.pack(side="left", padx=(0, 12))

        # ── Opciones ─────────────────────────────────────────────────────
        opts = Card(self, title="Opciones del pipeline")
        opts.pack(fill="x", padx=20, pady=(0, 16))
        col = ctk.CTkFrame(opts, fg_color="transparent")
        col.pack(fill="x", padx=18, pady=(0, 16))

        self.var_sem = ctk.BooleanVar()
        self.var_men = ctk.BooleanVar()
        ctk.CTkCheckBox(col, text="Forzar reporte semanal",
                        variable=self.var_sem).pack(anchor="w", pady=4)
        ctk.CTkCheckBox(col, text="Forzar reporte mensual",
                        variable=self.var_men).pack(anchor="w", pady=4)

        ctk.CTkLabel(col, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, justify="left",
                     text=("Por defecto, el reporte semanal se genera los lunes "
                           "y el mensual el día 1.")).pack(anchor="w", pady=(8, 0))

        # ── Botón ejecutar ───────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_ejec = ctk.CTkButton(
            bar, text="▶  Ejecutar pipeline", height=44, width=220,
            font=T.FONT_H2, fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            command=self._ejecutar)
        self.btn_ejec.pack(side="right")

        self.btn_demo = ctk.CTkButton(
            bar, text="Generar serie de 7 días (demo)", height=44, width=240,
            fg_color="transparent", border_width=1, border_color=T.PRIMARY,
            text_color=T.PRIMARY, hover_color=T.HOVER_BG,
            command=self._generar_demo)
        self.btn_demo.pack(side="right", padx=(0, 10))

    # ── Estado ──────────────────────────────────────────────────────────
    def refresh(self):
        disponibles = self.state.vuelos_disponibles()
        procesados = self.state.vuelos_procesados()

        # Solo los no procesados quedan al frente; el resto siguen seleccionables
        pendientes = [f for f in disponibles if f not in procesados]
        todos = pendientes + sorted(
            [f for f in disponibles if f in procesados], reverse=True)

        if not todos:
            self.combo_fecha.configure(values=[date.today().isoformat()])
            self.combo_fecha.set(date.today().isoformat())
        else:
            self.combo_fecha.configure(values=todos)
            self.combo_fecha.set(pendientes[0] if pendientes else todos[0])

        self._actualizar_estado_fecha()

    def _actualizar_estado_fecha(self):
        fecha = self.combo_fecha.get()
        disponibles = self.state.vuelos_disponibles()
        procesados  = self.state.vuelos_procesados()

        if fecha not in disponibles:
            self.pill_estado.configure(text="DSM no encontrado", fg_color=T.DANGER)
            self.btn_ejec.configure(state="disabled")
        elif fecha in procesados:
            self.pill_estado.configure(text="Ya procesado · re-ejecutará",
                                        fg_color=T.WARNING)
            self.btn_ejec.configure(state="normal")
        else:
            self.pill_estado.configure(text="Listo para procesar",
                                        fg_color=T.SUCCESS)
            self.btn_ejec.configure(state="normal")

    # ── Acciones ────────────────────────────────────────────────────────
    def _ejecutar(self):
        fecha = self.combo_fecha.get()
        if not self.state.project_configured():
            messagebox.showwarning(
                "Proyecto sin configurar",
                "Primero configura el proyecto en la pestaña Configuración.")
            return
        ok, falt = self.state.baseline_ready()
        if not ok:
            messagebox.showwarning(
                "Baseline incompleto",
                "Faltan archivos en baseline/:\n  · " + "\n  · ".join(falt))
            return

        ProcessDialog(
            self.winfo_toplevel(),
            titulo=f"Pipeline diario — {fecha}",
            popen_factory=lambda: self.state.run_pipeline(
                fecha, self.var_sem.get(), self.var_men.get()),
            on_done=lambda ok: (ok and self.on_processed and self.on_processed()),
        )

    def _generar_demo(self):
        if not messagebox.askyesno(
            "Generar serie de ejemplo",
            "Esto creará 7 días de DSM sintéticos en vuelos/. "
            "Útil para probar el flujo. ¿Continuar?"):
            return
        ProcessDialog(
            self.winfo_toplevel(),
            titulo="Generando serie de DSM de ejemplo",
            popen_factory=self.state.run_generar_serie,
            on_done=lambda ok: (ok and self.refresh()),
        )
