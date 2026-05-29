"""Vista 'Vuelo diario': carga DEMs y ejecuta el pipeline."""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

from . import theme as T
from .state import ProjectState
from .widgets import SectionTitle, Card, Pill, StatusBadge, UploadCard
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
                 selected: bool = False, on_select=None, on_delete=None, **kw):
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

        # Botón eliminar (solo para DEMs procesados)
        if procesado and on_delete:
            ctk.CTkButton(
                inner, text="✕", width=28, height=26,
                fg_color="transparent",
                hover_color=("#FEE2E2", "#7F1D1D"),
                text_color=T.DANGER,
                font=(T.FONT_FAMILY, 11, "bold"),
                command=lambda: on_delete(fecha),
            ).pack(side="right", padx=(0, 2))

        # Bind clics en todos los widgets hijos (excepto el botón de borrar)
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

        self._build_insumos_base()

        # ── Tarjeta: cargar DEM (colapsable) ────────────────────────────
        self._dem_collapsed = False
        up_card = Card(self)
        up_card.pack(fill="x", padx=20, pady=(0, 14))

        # Cabecera siempre visible
        up_hdr = ctk.CTkFrame(up_card, fg_color="transparent")
        up_hdr.pack(fill="x", padx=18, pady=(10, 4))

        ctk.CTkLabel(
            up_hdr, text="Cargar DEM diario",
            font=T.FONT_H2, text_color=T.TEXT, anchor="w",
        ).pack(side="left")

        self._dem_toggle_btn = ctk.CTkButton(
            up_hdr, text="▲  Contraer", width=120, height=28,
            font=T.FONT_SMALL,
            fg_color="transparent", hover_color=T.HOVER_BG,
            text_color=T.TEXT_MUTED, border_width=1, border_color=T.CARD_BORDER,
            command=self._toggle_dem_card,
        )
        self._dem_toggle_btn.pack(side="right", padx=(8, 0))

        # Chip compacto de estado (siempre visible)
        self._dem_compact_chip = ctk.CTkLabel(
            up_hdr, text="", font=T.FONT_TINY,
            corner_radius=8, fg_color="transparent",
        )
        self._dem_compact_chip.pack(side="right", padx=(0, 6))

        # Cuerpo colapsable
        self._dem_body = ctk.CTkFrame(up_card, fg_color="transparent")
        self._dem_body.pack(fill="x")

        up_inner = ctk.CTkFrame(self._dem_body, fg_color="transparent")
        up_inner.pack(padx=18, pady=(2, 18))

        self._upload_card_dem = UploadCard(
            up_inner, 0, "DEM Diario",
            "Vuelo fotogramétrico  (GeoTIFF / .tif)",
            on_upload=self._subir_dem,
        )
        self._upload_card_dem.pack(side="left", padx=(0, 20))

        hint = ctk.CTkLabel(
            up_inner,
            text=(
                "Haz clic en la tarjeta para seleccionar\n"
                "uno o varios archivos .tif.\n\n"
                "Cada archivo se guardará en:\n"
                "vuelos/<fecha>/dsm.tif\n\n"
                "Se pedirá la fecha de vuelo\n"
                "para cada archivo."
            ),
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
            justify="left", anchor="nw",
        )
        hint.pack(side="left", anchor="n", pady=8)

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

        # Pill de estado del vuelo seleccionado
        self.pill_estado = Pill(bar, "Ningún vuelo seleccionado", color=T.TEXT_MUTED)
        self.pill_estado.pack(side="left")

    # ── Insumos base del proyecto ────────────────────────────────────────────

    def _build_insumos_base(self):
        self._collapsed_insumos = False
        outer = Card(self, light=True)
        outer.pack(fill="x", padx=20, pady=(0, 16))

        hdr = ctk.CTkFrame(outer, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(10, 4))

        ctk.CTkLabel(
            hdr, text="Insumos base del proyecto",
            font=T.FONT_H2, text_color=T.TEXT, anchor="w",
        ).pack(side="left")

        self._toggle_btn_insumos = ctk.CTkButton(
            hdr, text="▲  Contraer", width=120, height=28,
            font=T.FONT_SMALL,
            fg_color="transparent", hover_color=T.HOVER_BG,
            text_color=T.TEXT_MUTED, border_width=1, border_color=T.CARD_BORDER,
            command=self._toggle_insumos,
        )
        self._toggle_btn_insumos.pack(side="right", padx=(8, 0))

        self._compact_row = ctk.CTkFrame(hdr, fg_color="transparent")
        self._compact_row.pack(side="right", padx=(0, 6))

        self._insumos_body = ctk.CTkFrame(outer, fg_color="transparent")
        self._insumos_body.pack(fill="x")

        ctk.CTkLabel(
            self._insumos_body,
            text=("Haz clic en cada tarjeta para seleccionar el archivo. "
                  "Se copiarán automáticamente a la carpeta baseline/ del proyecto."),
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            wraplength=860,
        ).pack(anchor="w", padx=18, pady=(2, 14))

        cards_row = ctk.CTkFrame(self._insumos_body, fg_color="transparent")
        cards_row.pack(padx=18, pady=(0, 18))

        self._card_dem_ini = UploadCard(
            cards_row, 1, "DEM Inicial",
            "Terreno natural  (GeoTIFF / .tif)",
            on_upload=self._upload_dem_ini,
            icon="📂",
        )
        self._card_dem_ini.grid(row=0, column=0, padx=14, pady=6)

        self._card_eje = UploadCard(
            cards_row, 2, "Eje de la Vía",
            "Geometría del corredor  (DXF)",
            on_upload=self._upload_eje,
            icon="📂",
        )
        self._card_eje.grid(row=0, column=1, padx=14, pady=6)

        self._card_dem_final = UploadCard(
            cards_row, 3, "DEM Final",
            "Volumen objetivo del proyecto  (.tif)",
            on_upload=self._upload_dem_final,
            icon="📂",
        )
        self._card_dem_final.grid(row=0, column=2, padx=14, pady=6)

        ctk.CTkFrame(self._insumos_body, height=1,
                     fg_color=T.CARD_BORDER).pack(fill="x", padx=18, pady=(0, 10))

        ctk.CTkLabel(
            self._insumos_body, text="Estado de los insumos",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_MUTED, anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 4))

        self._status_body = ctk.CTkFrame(self._insumos_body, fg_color="transparent")
        self._status_body.pack(fill="x", padx=18, pady=(0, 14))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        self.btn_calc = ctk.CTkButton(
            btn_row, text="▶  Calcular Volúmenes ΔZ",
            height=44, width=260,
            font=T.FONT_H2,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK,
            command=self._calcular_volumenes,
            state="disabled",
        )
        self.btn_calc.pack(side="right")

    def _toggle_insumos(self):
        self._collapsed_insumos = not self._collapsed_insumos
        if self._collapsed_insumos:
            self._insumos_body.pack_forget()
            self._toggle_btn_insumos.configure(text="▼  Expandir")
        else:
            self._insumos_body.pack(fill="x")
            self._toggle_btn_insumos.configure(text="▲  Contraer")

    def _upload_dem_ini(self):
        path = filedialog.askopenfilename(
            title="Seleccionar DEM Inicial",
            filetypes=[("GeoTIFF", "*.tif *.tiff *.TIF *.TIFF"),
                       ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            dest = self._ensure_baseline() / "dem_baseline.tif"
            shutil.copy2(path, dest)
            self._card_dem_ini.set_loaded(dest)
            self._refresh_insumos_status()
        except Exception as exc:
            messagebox.showerror("Error al copiar archivo", str(exc))

    def _upload_eje(self):
        path = filedialog.askopenfilename(
            title="Seleccionar eje de la vía",
            filetypes=[("AutoCAD DXF", "*.dxf *.DXF"),
                       ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            dest = self._ensure_baseline() / "eje_via.dxf"
            shutil.copy2(path, dest)
            self._card_eje.set_loaded(dest)
            self._refresh_insumos_status()
        except Exception as exc:
            messagebox.showerror("Error al copiar archivo", str(exc))

    def _upload_dem_final(self):
        path = filedialog.askopenfilename(
            title="Seleccionar DEM Final (volumen objetivo)",
            filetypes=[("GeoTIFF", "*.tif *.tiff *.TIF *.TIFF"),
                       ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            dest = self._ensure_baseline() / "dem_final.tif"
            shutil.copy2(path, dest)
            self._card_dem_final.set_loaded(dest)
            self._refresh_insumos_status()
        except Exception as exc:
            messagebox.showerror("Error al copiar archivo", str(exc))

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

    def _dem_final_path(self) -> Path | None:
        return self.state.dem_final_path()

    def _refresh_insumos_status(self):
        for w in self._status_body.winfo_children():
            w.destroy()
        for w in self._compact_row.winfo_children():
            w.destroy()

        dem_ini   = self.state.dem_baseline_path()
        eje       = self._eje_path()
        dem_final = self._dem_final_path()

        items = [
            ("DEM Ini",   "DEM Inicial",   "dem_baseline.tif", dem_ini),
            ("Eje",       "Eje de la Vía", "eje_via.dxf",      eje),
            ("DEM Final", "DEM Final",     "dem_final.tif",     dem_final),
        ]
        all_ok = True
        for short, nombre, archivo, path in items:
            ok = path is not None
            if not ok:
                all_ok = False

            chip_bg = "#E7F7EE" if ok else "#FEE2E2"
            chip_fg = "#10B981" if ok else "#EF4444"
            dot = "●" if ok else "○"
            ctk.CTkLabel(
                self._compact_row,
                text=f"  {dot} {short}  ",
                font=T.FONT_TINY,
                corner_radius=8, fg_color=chip_bg, text_color=chip_fg,
            ).pack(side="left", padx=3)

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
                row,
                text=f"({archivo})" if not ok else str(path),
                font=T.FONT_TINY, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(side="left")

        self.btn_calc.configure(state="normal" if all_ok else "disabled")

    def _calcular_volumenes(self):
        from .runner import ProcessDialog
        ProcessDialog(
            self.winfo_toplevel(),
            titulo="Calculando Volúmenes ΔZ",
            popen_factory=self.state.run_odm,
        )

    # ── Toggle cargar DEM ────────────────────────────────────────────────────

    def _toggle_dem_card(self):
        self._dem_collapsed = not self._dem_collapsed
        if self._dem_collapsed:
            self._dem_body.pack_forget()
            self._dem_toggle_btn.configure(text="▼  Expandir")
        else:
            self._dem_body.pack(fill="x")
            self._dem_toggle_btn.configure(text="▲  Contraer")

    def _update_dem_chip(self, loaded_path):
        if loaded_path is not None:
            self._dem_compact_chip.configure(
                text=f"  ● {loaded_path.name}  ",
                fg_color="#E7F7EE", text_color="#10B981",
            )
        else:
            self._dem_compact_chip.configure(
                text="  ○ Sin DEM  ",
                fg_color="#FEE2E2", text_color="#EF4444",
            )

    # ── Estado / refresco ────────────────────────────────────────────────────

    def refresh(self):
        """Reconstruye la lista de DEMs desde disco."""
        dem_ini   = self.state.dem_baseline_path()
        eje       = self._eje_path()
        dem_final = self._dem_final_path()
        for card in (self._card_dem_ini, self._card_eje, self._card_dem_final):
            card.refresh_theme()
        self._card_dem_ini.set_loaded(dem_ini)
        self._card_eje.set_loaded(eje)
        self._card_dem_final.set_loaded(dem_final)
        self._refresh_insumos_status()

        disponibles = self.state.vuelos_disponibles()   # ordenados asc
        procesados  = self.state.vuelos_procesados()

        # Actualizar card de carga (colores de tema + estado)
        self._upload_card_dem.refresh_theme()
        if disponibles:
            from pathlib import Path
            ultimo = sorted(disponibles)[-1]
            p = self.state.vuelos_dir / ultimo / "dsm.tif"
            loaded = p if p.exists() else None
            self._upload_card_dem.set_loaded(loaded)
            self._update_dem_chip(loaded)
        else:
            self._upload_card_dem.set_loaded(None)
            self._update_dem_chip(None)

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
                on_delete=self._borrar_dem,
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
            self.refresh()   # también actualiza la tarjeta OVNI
            # Auto-seleccionar el último importado
            ultimo = sorted(importados)[-1]
            if ultimo in self._rows:
                self._seleccionar(ultimo)
            messagebox.showinfo(
                "DEMs importados",
                f"Se importaron {len(importados)} archivo(s):\n"
                + "\n".join(f"  · vuelos/{f}/dsm.tif" for f in sorted(importados)),
            )

    def _borrar_dem(self, fecha: str):
        confirmar = messagebox.askyesno(
            "Eliminar DEM procesado",
            f"¿Eliminar la carpeta del vuelo {fecha}?\n\n"
            "Se borrarán el DEM y todos los archivos generados en esa fecha.\n"
            "Esta acción no se puede deshacer.",
            icon="warning",
        )
        if not confirmar:
            return
        try:
            carpeta = self.state.vuelos_dir / fecha
            shutil.rmtree(carpeta)
        except Exception as exc:
            messagebox.showerror("Error al eliminar", str(exc))
            return
        if self._selected_fecha == fecha:
            self._selected_fecha = None
        self.refresh()

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

