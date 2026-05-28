"""Vista 'Vuelo diario': carga DEMs y ejecuta el pipeline."""
from __future__ import annotations

from datetime import date
import customtkinter as ctk
from tkinter import filedialog, messagebox

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card, Pill
from .runner import ProcessDialog


# ── Diálogo: fecha del DEM importado ────────────────────────────────────────

class _DateAskDialog(ctk.CTkToplevel):
    """Pide confirmación de fecha al importar un DEM."""

    def __init__(self, master, filename: str):
        super().__init__(master)
        self.title("Fecha del vuelo")
        self.resizable(False, False)
        self.grab_set()
        self.result: str | None = None

        ctk.CTkLabel(self, text=f"Archivo seleccionado:  {filename}",
                     font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                     anchor="w").pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(self, text="Fecha del vuelo (AAAA-MM-DD)",
                     font=T.FONT_BODY, anchor="w").pack(anchor="w", padx=24, pady=(0, 6))

        self.entry = ctk.CTkEntry(self, width=200,
                                  placeholder_text="2025-05-06")
        self.entry.insert(0, date.today().isoformat())
        self.entry.pack(padx=24, pady=(0, 18))
        self.entry.bind("<Return>", lambda _: self._confirm())

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(padx=24, pady=(0, 18))
        ctk.CTkButton(bar, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      border_color=T.CARD_BORDER, text_color=T.TEXT,
                      hover_color=T.HOVER_BG,
                      command=self.destroy).pack(side="left", padx=(0, 10))
        ctk.CTkButton(bar, text="Importar DEM", width=140,
                      fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
                      command=self._confirm).pack(side="left")

    def _confirm(self):
        val = self.entry.get().strip()
        try:
            date.fromisoformat(val)
        except ValueError:
            messagebox.showerror("Fecha inválida",
                                 "Usa el formato AAAA-MM-DD,  p.ej. 2025-05-06",
                                 parent=self)
            return
        self.result = val
        self.destroy()


# ── Fila de un DEM en la lista ────────────────────────────────────────────

class _DEMRow(ctk.CTkFrame):
    """Fila seleccionable que representa un DEM disponible."""

    def __init__(self, master, fecha: str, procesado: bool,
                 selected: bool = False, on_select=None, **kw):
        super().__init__(master, corner_radius=8, border_width=1,
                         border_color=T.PRIMARY if selected else T.CARD_BORDER,
                         fg_color=("#EFF6FF", "#1E3A5F") if selected else T.CARD_BG,
                         cursor="hand2", **kw)
        self.fecha = fecha
        self._on_select = on_select

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=9)

        # Icono de selección
        self._dot = ctk.CTkLabel(
            inner, width=18,
            text="●" if selected else "○",
            font=(T.FONT_FAMILY, 13),
            text_color=T.PRIMARY if selected else T.TEXT_FAINT,
        )
        self._dot.pack(side="left", padx=(0, 10))

        # Fecha
        self._lbl_fecha = ctk.CTkLabel(
            inner, text=fecha, font=T.FONT_BODY,
            text_color=T.TEXT, anchor="w", width=150,
        )
        self._lbl_fecha.pack(side="left")

        # Pill estado
        self._pill = Pill(
            inner,
            "Procesado" if procesado else "Pendiente",
            color=T.SUCCESS if procesado else T.WARNING,
        )
        self._pill.pack(side="left", padx=(0, 14))

        # Nombre archivo
        ctk.CTkLabel(inner, text="dsm.tif",
                     font=T.FONT_SMALL, text_color=T.TEXT_FAINT).pack(side="left")

        # Bind clics en todos los widgets hijos
        for w in (self, inner, self._dot, self._lbl_fecha):
            w.bind("<Button-1>", self._clicked)

    def _clicked(self, _=None):
        if self._on_select:
            self._on_select(self.fecha)

    def set_selected(self, selected: bool):
        self.configure(
            border_color=T.PRIMARY if selected else T.CARD_BORDER,
            fg_color=("#EFF6FF", "#1E3A5F") if selected else T.CARD_BG,
        )
        self._dot.configure(
            text="●" if selected else "○",
            text_color=T.PRIMARY if selected else T.TEXT_FAINT,
        )


# ── Vista principal ──────────────────────────────────────────────────────────

class DiarioView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState, on_processed=None):
        super().__init__(master, fg_color="transparent")
        self.state = state
        self.on_processed = on_processed
        self._selected_fecha: str | None = None
        self._rows: dict[str, _DEMRow] = {}
        self._build()
        self.refresh()

    # ── Construcción ────────────────────────────────────────────────────────

    def _build(self):
        SectionTitle(self, text="Vuelo diario").pack(
            anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(self, font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                     text="Sube el DEM de cada vuelo y selecciona cuál procesar.",
                     anchor="w").pack(anchor="w", padx=24, pady=(0, 14))

        # ── Tarjeta: cargar DEM ──────────────────────────────────────────
        up_card = Card(self, title="Cargar DEM diario")
        up_card.pack(fill="x", padx=20, pady=(0, 14))

        up_row = ctk.CTkFrame(up_card, fg_color="transparent")
        up_row.pack(fill="x", padx=18, pady=(0, 16))

        ctk.CTkButton(
            up_row, text="📂  Subir DEM (.tif)", height=38, width=210,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            font=T.FONT_H2, command=self._subir_dem,
        ).pack(side="left")

        ctk.CTkLabel(
            up_row,
            text="Selecciona uno o varios archivos .tif  —  se guardarán en vuelos/<fecha>/dsm.tif",
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
        ).pack(side="left", padx=(16, 0))

        # ── Tarjeta: lista de DEMs ───────────────────────────────────────
        list_card = Card(self, title="DEMs disponibles")
        list_card.pack(fill="x", padx=20, pady=(0, 14))

        # Cabecera de columnas
        hdr = ctk.CTkFrame(list_card, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(0, 6))
        for text, w in [("", 28), ("Fecha", 168), ("Estado", 110), ("Archivo", 0)]:
            ctk.CTkLabel(hdr, text=text, font=T.FONT_SMALL,
                         text_color=T.TEXT_FAINT, width=w, anchor="w").pack(
                side="left", padx=(0, 0 if w == 0 else 0))

        # Separador
        ctk.CTkFrame(list_card, height=1, fg_color=T.CARD_BORDER).pack(
            fill="x", padx=18, pady=(0, 8))

        # Área scrollable
        self._scroll = ctk.CTkScrollableFrame(
            list_card, fg_color="transparent", height=180)
        self._scroll.pack(fill="x", padx=12, pady=(0, 12))

        self._empty_lbl = ctk.CTkLabel(
            self._scroll,
            text="No hay DEMs cargados. Usa el botón «Subir DEM» para agregar vuelos.",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED,
        )

        # Botón refrescar (pequeño, a la derecha del título de la card)
        ctk.CTkButton(
            list_card, text="↻", width=32, height=28,
            fg_color="transparent", border_width=1,
            border_color=T.CARD_BORDER, text_color=T.TEXT_MUTED,
            hover_color=T.HOVER_BG, command=self.refresh,
        ).place(relx=1.0, rely=0.0, anchor="ne", x=-14, y=10)

        # ── Tarjeta: opciones pipeline ───────────────────────────────────
        opts = Card(self, title="Opciones del pipeline")
        opts.pack(fill="x", padx=20, pady=(0, 14))
        col = ctk.CTkFrame(opts, fg_color="transparent")
        col.pack(fill="x", padx=18, pady=(0, 14))

        self.var_sem = ctk.BooleanVar()
        self.var_men = ctk.BooleanVar()
        ctk.CTkCheckBox(col, text="Forzar reporte semanal",
                        variable=self.var_sem).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col, text="Forzar reporte mensual",
                        variable=self.var_men).pack(anchor="w", pady=3)
        ctk.CTkLabel(col, font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                     text="Por defecto, el reporte semanal se genera los lunes y el mensual el día 1."
                     ).pack(anchor="w", pady=(8, 0))

        # ── Barra inferior ───────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_ejec = ctk.CTkButton(
            bar, text="▶  Procesar vuelo seleccionado",
            height=44, width=280, font=T.FONT_H2,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            state="disabled", command=self._ejecutar,
        )
        self.btn_ejec.pack(side="right")

        self.btn_demo = ctk.CTkButton(
            bar, text="Generar serie de 7 días (demo)",
            height=44, width=240,
            fg_color="transparent", border_width=1,
            border_color=T.PRIMARY, text_color=T.PRIMARY,
            hover_color=T.HOVER_BG, command=self._generar_demo,
        )
        self.btn_demo.pack(side="right", padx=(0, 10))

        # Pill de estado del vuelo seleccionado
        self.pill_estado = Pill(bar, "Ningún vuelo seleccionado", color=T.TEXT_MUTED)
        self.pill_estado.pack(side="left")

    # ── Estado / refresco ────────────────────────────────────────────────────

    def refresh(self):
        """Reconstruye la lista de DEMs desde disco."""
        disponibles = self.state.vuelos_disponibles()   # ordenados asc
        procesados  = self.state.vuelos_procesados()

        # Limpiar filas anteriores
        for w in list(self._rows.values()):
            w.destroy()
        self._rows.clear()
        self._empty_lbl.pack_forget()

        if not disponibles:
            self._empty_lbl.pack(pady=20)
            self._selected_fecha = None
            self._actualizar_pill()
            return

        # Renderizar desc (más reciente arriba)
        for fecha in reversed(disponibles):
            row = _DEMRow(
                self._scroll, fecha=fecha,
                procesado=(fecha in procesados),
                selected=(fecha == self._selected_fecha),
                on_select=self._seleccionar,
            )
            row.pack(fill="x", pady=(0, 6))
            self._rows[fecha] = row

        # Auto-seleccionar el más reciente pendiente si no hay selección
        if self._selected_fecha not in disponibles:
            pendientes = [f for f in reversed(disponibles) if f not in procesados]
            self._selected_fecha = pendientes[0] if pendientes else disponibles[-1]
            if self._selected_fecha in self._rows:
                self._rows[self._selected_fecha].set_selected(True)

        self._actualizar_pill()

    def _seleccionar(self, fecha: str):
        """Actualiza la selección visual y la fecha activa."""
        if self._selected_fecha and self._selected_fecha in self._rows:
            self._rows[self._selected_fecha].set_selected(False)
        self._selected_fecha = fecha
        if fecha in self._rows:
            self._rows[fecha].set_selected(True)
        self._actualizar_pill()

    def _actualizar_pill(self):
        if not self._selected_fecha:
            self.pill_estado.configure(text="Ningún vuelo seleccionado",
                                       fg_color=T.TEXT_MUTED)
            self.btn_ejec.configure(state="disabled")
            return

        procesados = self.state.vuelos_procesados()
        if self._selected_fecha in procesados:
            self.pill_estado.configure(
                text=f"{self._selected_fecha}  ·  Ya procesado (re-ejecutará)",
                fg_color=T.WARNING)
        else:
            self.pill_estado.configure(
                text=f"{self._selected_fecha}  ·  Listo para procesar",
                fg_color=T.SUCCESS)
        self.btn_ejec.configure(state="normal")

    # ── Acciones ─────────────────────────────────────────────────────────────

    def _subir_dem(self):
        """Abre diálogo de archivos, pide fecha por cada TIF y lo importa."""
        rutas = filedialog.askopenfilenames(
            title="Seleccionar DEM(s) .tif",
            filetypes=[("GeoTIFF", "*.tif *.tiff"), ("Todos", "*.*")],
        )
        if not rutas:
            return

        importados = []
        for ruta in rutas:
            nombre = ruta.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            dlg = _DateAskDialog(self.winfo_toplevel(), nombre)
            self.wait_window(dlg)
            if dlg.result is None:
                continue  # usuario canceló este archivo
            try:
                self.state.import_dem(ruta, dlg.result)
                importados.append(dlg.result)
            except Exception as exc:
                messagebox.showerror(
                    "Error al importar",
                    f"No se pudo copiar el archivo:\n{exc}",
                )

        if importados:
            self.refresh()
            # Auto-seleccionar el último importado
            ultimo = sorted(importados)[-1]
            if ultimo in self._rows:
                self._seleccionar(ultimo)
            messagebox.showinfo(
                "DEMs importados",
                f"Se importaron {len(importados)} archivo(s):\n"
                + "\n".join(f"  · vuelos/{f}/dsm.tif" for f in sorted(importados)),
            )

    def _ejecutar(self):
        fecha = self._selected_fecha
        if not fecha:
            return
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
            on_done=lambda ok: (ok and self._post_procesado()),
        )

    def _post_procesado(self):
        self.refresh()
        if self.on_processed:
            self.on_processed()

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
