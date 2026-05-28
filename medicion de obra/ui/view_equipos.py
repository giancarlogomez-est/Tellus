"""Vista Equipos y Rendimientos — maquinaria, flotas y análisis de producción."""
from __future__ import annotations

import uuid
from datetime import date

import customtkinter as ctk
import pandas as pd

from . import theme as T
from .state import ProjectState
from .widgets import Card, DataTable, KPICardIcon, SectionTitle, StatusBadge

TIPOS_EQUIPO = [
    "Excavadora", "Bulldozer", "Motoniveladora",
    "Volqueta", "Vibrocompactador",
]
UNIDAD_DEFECTO = {
    "Excavadora":      "m³",
    "Bulldozer":       "m³",
    "Motoniveladora":  "ha",
    "Volqueta":        "m³",
    "Vibrocompactador": "ha",
}


class EquiposView(ctk.CTkFrame):
    def __init__(self, master, state: ProjectState, on_updated=None):
        super().__init__(master, fg_color=T.APP_BG)
        self.state = state
        self.on_updated = on_updated
        self._active_tab = "equipos"
        self._build()

    # ═══════════════════════════════════════════════════════════════════
    # Construcción inicial
    # ═══════════════════════════════════════════════════════════════════
    def _build(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=T.APP_BG)
        self.scroll.pack(fill="both", expand=True)
        self._build_header()
        self.content = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=24, pady=(8, 20))

    def _build_header(self):
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(18, 0))

        SectionTitle(hdr, text="Equipos y Rendimientos",
                     text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(
            hdr, text="Gestión de maquinaria, flotas y análisis de producción",
            font=T.FONT_BODY, text_color=T.TEXT_MUTED, anchor="w",
        ).pack(anchor="w", pady=(2, 12))

        tabs_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        tabs_frame.pack(fill="x")
        self._tab_btns: dict[str, ctk.CTkButton] = {}
        for key, label, icon in [
            ("equipos",      "Equipos",         "🚜"),
            ("flotas",       "Flotas",           "🏗"),
            ("registro",     "Registro Diario",  "📝"),
            ("rendimientos", "Rendimientos",     "📈"),
        ]:
            active = key == self._active_tab
            b = ctk.CTkButton(
                tabs_frame, text=f"{icon}  {label}",
                height=36, corner_radius=8, font=T.FONT_BODY,
                fg_color=T.PRIMARY if active else T.HOVER_BG,
                text_color=T.TEXT_ON_DARK if active else T.TEXT_MUTED,
                hover_color=T.PRIMARY_HOV if active else T.CARD_BORDER,
                command=lambda k=key: self._switch_tab(k),
            )
            b.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = b

        ctk.CTkFrame(hdr, height=1, fg_color=T.CARD_BORDER).pack(
            fill="x", pady=(12, 0))

    # ── Router de tabs ───────────────────────────────────────────────────
    def _switch_tab(self, key: str):
        self._active_tab = key
        for k, b in self._tab_btns.items():
            if k == key:
                b.configure(fg_color=T.PRIMARY, text_color=T.TEXT_ON_DARK,
                            hover_color=T.PRIMARY_HOV)
            else:
                b.configure(fg_color=T.HOVER_BG, text_color=T.TEXT_MUTED,
                            hover_color=T.CARD_BORDER)
        self._render_tab()

    def _render_tab(self):
        for w in self.content.winfo_children():
            w.destroy()
        {
            "equipos":      self._render_equipos,
            "flotas":       self._render_flotas,
            "registro":     self._render_registro,
            "rendimientos": self._render_rendimientos,
        }[self._active_tab]()

    def refresh(self):
        self._render_tab()

    # ═══════════════════════════════════════════════════════════════════
    # TAB 1 — Equipos
    # ═══════════════════════════════════════════════════════════════════
    def _render_equipos(self):
        data = self.state.load_equipos_data()
        equipos = data.get("equipos", [])

        # ── Formulario de alta ─────────────────────────────────────────
        form_card = Card(self.content, title="Agregar nuevo equipo", light=True)
        form_card.pack(fill="x", pady=(12, 8))
        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 14))
        for c in range(5):
            form.grid_columnconfigure(c, weight=1)

        # Fila 0: etiquetas
        for c, txt in enumerate(["Nombre / Código", "Tipo", "Marca",
                                  "Cap. nominal (u/h)", "Unidad producción"]):
            ctk.CTkLabel(form, text=txt, font=T.FONT_SMALL,
                         text_color=T.TEXT_MUTED, anchor="w").grid(
                             row=0, column=c, sticky="w", padx=4, pady=(0, 2))

        # Fila 1: inputs
        e_nombre = ctk.CTkEntry(form, placeholder_text="Ej: CAT 336",
                                fg_color=T.INPUT_BG, text_color=T.TEXT,
                                border_color=T.CARD_BORDER)
        e_nombre.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))

        tipo_var = ctk.StringVar(value="Excavadora")
        ctk.CTkOptionMenu(
            form, values=TIPOS_EQUIPO, variable=tipo_var,
            fg_color=T.INPUT_BG, button_color=T.INPUT_BG,
            button_hover_color=T.INPUT_HOVER, text_color=T.TEXT,
            dropdown_fg_color=T.CARD_BG, dropdown_text_color=T.TEXT,
        ).grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 8))

        e_marca = ctk.CTkEntry(form, placeholder_text="Ej: CAT, Komatsu",
                               fg_color=T.INPUT_BG, text_color=T.TEXT,
                               border_color=T.CARD_BORDER)
        e_marca.grid(row=1, column=2, sticky="ew", padx=4, pady=(0, 8))

        e_cap = ctk.CTkEntry(form, placeholder_text="Ej: 350",
                             fg_color=T.INPUT_BG, text_color=T.TEXT,
                             border_color=T.CARD_BORDER)
        e_cap.grid(row=1, column=3, sticky="ew", padx=4, pady=(0, 8))

        unidad_var = ctk.StringVar(value="m³")
        ctk.CTkOptionMenu(
            form, values=["m³", "ha", "m²", "viajes", "m"],
            variable=unidad_var,
            fg_color=T.INPUT_BG, button_color=T.INPUT_BG,
            button_hover_color=T.INPUT_HOVER, text_color=T.TEXT,
            dropdown_fg_color=T.CARD_BG, dropdown_text_color=T.TEXT,
        ).grid(row=1, column=4, sticky="ew", padx=4, pady=(0, 8))

        def _auto_unidad(*_):
            unidad_var.set(UNIDAD_DEFECTO.get(tipo_var.get(), "m³"))
        tipo_var.trace_add("write", _auto_unidad)

        # Fila 2: mensaje + botón guardar
        msg_var = ctk.StringVar()
        msg_lbl = ctk.CTkLabel(form, textvariable=msg_var, font=T.FONT_SMALL,
                               text_color=T.DANGER, anchor="w")
        msg_lbl.grid(row=2, column=0, columnspan=4, sticky="w", padx=4)

        def _guardar():
            nombre = e_nombre.get().strip()
            if not nombre:
                msg_var.set("El nombre es obligatorio")
                return
            cap_str = e_cap.get().strip()
            try:
                cap = float(cap_str) if cap_str else 0.0
            except ValueError:
                msg_var.set("Capacidad debe ser numérico")
                return
            d = self.state.load_equipos_data()
            d["equipos"].append({
                "id": f"eq_{uuid.uuid4().hex[:8]}",
                "nombre": nombre,
                "tipo": tipo_var.get(),
                "marca": e_marca.get().strip(),
                "capacidad_nominal": cap,
                "unidad_produccion": unidad_var.get(),
            })
            self.state.save_equipos_data(d)
            if self.on_updated:
                self.on_updated()
            self._switch_tab("equipos")

        ctk.CTkButton(
            form, text="+ Agregar equipo", command=_guardar,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK, font=T.FONT_BODY,
            height=34, corner_radius=8,
        ).grid(row=2, column=4, sticky="ew", padx=4)

        # ── Lista de equipos ───────────────────────────────────────────
        list_card = Card(
            self.content,
            title=f"Equipos registrados  ({len(equipos)})",
            light=True,
        )
        list_card.pack(fill="x", pady=(0, 8))

        if not equipos:
            ctk.CTkLabel(list_card,
                         text="Aún no hay equipos. Usa el formulario de arriba.",
                         font=T.FONT_BODY, text_color=T.TEXT_MUTED).pack(pady=18)
            return

        tbl = DataTable(
            list_card,
            columns=["Nombre", "Tipo", "Marca", "Cap. Nominal", "Unidad", ""],
            widths=[160, 130, 110, 110, 80, 50],
        )
        tbl.pack(fill="x", padx=18, pady=(0, 14))
        for eq in equipos:
            cap_val = eq.get("capacidad_nominal", 0)
            cap_str = f"{cap_val:.0f}" if cap_val else "—"
            del_btn = ctk.CTkButton(
                tbl, text="✕", width=30, height=24,
                fg_color=T.DANGER, hover_color=T.DANGER_HOV,
                text_color="white", font=T.FONT_TINY, corner_radius=6,
                command=lambda eid=eq["id"]: self._eliminar_equipo(eid),
            )
            tbl.add_row([eq.get("nombre", ""), eq.get("tipo", ""),
                         eq.get("marca", ""), cap_str,
                         eq.get("unidad_produccion", "m³"), del_btn])

    def _eliminar_equipo(self, equipo_id: str):
        d = self.state.load_equipos_data()
        d["equipos"] = [e for e in d["equipos"] if e["id"] != equipo_id]
        self.state.save_equipos_data(d)
        if self.on_updated:
            self.on_updated()
        self._switch_tab("equipos")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 2 — Flotas
    # ═══════════════════════════════════════════════════════════════════
    def _render_flotas(self):
        data = self.state.load_equipos_data()
        flotas = data.get("flotas", [])
        equipos_map = {e["id"]: e for e in data.get("equipos", [])}
        equipos_list = list(equipos_map.values())

        # ── Formulario de nueva flota ──────────────────────────────────
        form_card = Card(self.content, title="Crear nueva flota", light=True)
        form_card.pack(fill="x", pady=(12, 8))
        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 14))
        form.grid_columnconfigure((0, 1), weight=1)

        for c, (lbl, ph) in enumerate([
            ("Nombre de la flota", "Ej: Flota Frente A"),
            ("Tramo / Frente",     "Ej: K0+000 - K2+500"),
        ]):
            ctk.CTkLabel(form, text=lbl, font=T.FONT_SMALL,
                         text_color=T.TEXT_MUTED, anchor="w").grid(
                             row=0, column=c, sticky="w", padx=4, pady=(0, 2))
        e_nombre = ctk.CTkEntry(form, placeholder_text="Ej: Flota Frente A",
                                fg_color=T.INPUT_BG, text_color=T.TEXT,
                                border_color=T.CARD_BORDER)
        e_nombre.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        e_tramo = ctk.CTkEntry(form, placeholder_text="Ej: K0+000 - K2+500",
                               fg_color=T.INPUT_BG, text_color=T.TEXT,
                               border_color=T.CARD_BORDER)
        e_tramo.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 8))

        chk_vars: dict[str, ctk.BooleanVar] = {}
        if equipos_list:
            ctk.CTkLabel(form, text="Equipos a asignar",
                         font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                         anchor="w").grid(row=2, column=0, columnspan=2,
                                          sticky="w", padx=4, pady=(4, 2))
            chk_frame = ctk.CTkFrame(form, fg_color="transparent")
            chk_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4)
            for idx, eq in enumerate(equipos_list):
                v = ctk.BooleanVar()
                chk_vars[eq["id"]] = v
                ctk.CTkCheckBox(
                    chk_frame,
                    text=f"{eq.get('nombre','')}  ({eq.get('tipo','')})",
                    variable=v, font=T.FONT_BODY, text_color=T.TEXT,
                    fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
                    border_color=T.CARD_BORDER,
                ).grid(row=idx // 3, column=idx % 3,
                       sticky="w", padx=8, pady=2)

        msg_var = ctk.StringVar()
        ctk.CTkLabel(form, textvariable=msg_var, font=T.FONT_SMALL,
                     text_color=T.DANGER, anchor="w").grid(
                         row=4, column=0, sticky="w", padx=4, pady=(4, 0))

        def _guardar_flota():
            nombre = e_nombre.get().strip()
            if not nombre:
                msg_var.set("El nombre es obligatorio")
                return
            d = self.state.load_equipos_data()
            d["flotas"].append({
                "id": f"fl_{uuid.uuid4().hex[:8]}",
                "nombre": nombre,
                "tramo": e_tramo.get().strip(),
                "equipo_ids": [eid for eid, v in chk_vars.items() if v.get()],
            })
            self.state.save_equipos_data(d)
            if self.on_updated:
                self.on_updated()
            self._switch_tab("flotas")

        ctk.CTkButton(
            form, text="+ Crear flota", command=_guardar_flota,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK, font=T.FONT_BODY,
            height=34, corner_radius=8,
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 0))

        # ── Lista de flotas ────────────────────────────────────────────
        list_card = Card(
            self.content, title=f"Flotas registradas  ({len(flotas)})",
            light=True,
        )
        list_card.pack(fill="x", pady=(0, 8))

        if not flotas:
            ctk.CTkLabel(list_card,
                         text="Aún no hay flotas. Crea una arriba.",
                         font=T.FONT_BODY, text_color=T.TEXT_MUTED).pack(pady=18)
        else:
            for flota in flotas:
                row_frame = ctk.CTkFrame(list_card, fg_color=T.HOVER_BG,
                                         corner_radius=8)
                row_frame.pack(fill="x", padx=18, pady=(4, 0))

                top_row = ctk.CTkFrame(row_frame, fg_color="transparent")
                top_row.pack(fill="x", padx=12, pady=(8, 2))
                ctk.CTkLabel(
                    top_row, text=f"🏗  {flota.get('nombre','')}",
                    font=T.FONT_H2, text_color=T.TEXT,
                ).pack(side="left")
                if flota.get("tramo"):
                    ctk.CTkLabel(
                        top_row, text=flota["tramo"],
                        font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                    ).pack(side="left", padx=(10, 0))
                ctk.CTkButton(
                    top_row, text="✕ Eliminar", width=80, height=26,
                    fg_color=T.DANGER, hover_color=T.DANGER_HOV,
                    text_color="white", font=T.FONT_TINY, corner_radius=6,
                    command=lambda fid=flota["id"]: self._eliminar_flota(fid),
                ).pack(side="right")

                chip_row = ctk.CTkFrame(row_frame, fg_color="transparent")
                chip_row.pack(fill="x", padx=12, pady=(0, 8))
                eqs = [equipos_map.get(eid) for eid in flota.get("equipo_ids", [])
                       if equipos_map.get(eid)]
                if eqs:
                    for eq in eqs:
                        ctk.CTkLabel(
                            chip_row,
                            text=f"  {eq.get('nombre','')}  ",
                            font=T.FONT_TINY, corner_radius=6,
                            fg_color=T.CARD_BG, text_color=T.TEXT,
                        ).pack(side="left", padx=(0, 4))
                else:
                    ctk.CTkLabel(chip_row, text="Sin equipos asignados",
                                 font=T.FONT_SMALL,
                                 text_color=T.TEXT_FAINT).pack(side="left")
            ctk.CTkFrame(list_card, height=8,
                         fg_color="transparent").pack()

    def _eliminar_flota(self, flota_id: str):
        d = self.state.load_equipos_data()
        d["flotas"] = [f for f in d["flotas"] if f["id"] != flota_id]
        self.state.save_equipos_data(d)
        if self.on_updated:
            self.on_updated()
        self._switch_tab("flotas")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 3 — Registro Diario
    # ═══════════════════════════════════════════════════════════════════
    def _render_registro(self):
        data = self.state.load_equipos_data()
        equipos_list = data.get("equipos", [])
        flotas = data.get("flotas", [])
        eq_to_flota = {
            eid: fl
            for fl in flotas
            for eid in fl.get("equipo_ids", [])
        }

        # ── Controles de cabecera ──────────────────────────────────────
        ctrl_card = Card(self.content, title="Datos del registro", light=True)
        ctrl_card.pack(fill="x", pady=(12, 8))
        ctrl = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl.pack(fill="x", padx=18, pady=(0, 12))
        ctrl.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(ctrl, text="Fecha (YYYY-MM-DD)", font=T.FONT_SMALL,
                     text_color=T.TEXT_MUTED, anchor="w").grid(
                         row=0, column=0, sticky="w", padx=4, pady=(0, 2))
        fecha_var = ctk.StringVar(value=date.today().isoformat())
        e_fecha = ctk.CTkEntry(ctrl, textvariable=fecha_var,
                               fg_color=T.INPUT_BG, text_color=T.TEXT,
                               border_color=T.CARD_BORDER)
        e_fecha.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))

        ctk.CTkLabel(ctrl, text="Filtrar por flota (opcional)",
                     font=T.FONT_SMALL, text_color=T.TEXT_MUTED,
                     anchor="w").grid(row=0, column=1, sticky="w", padx=4)
        flota_names = ["Todos los equipos"] + [f["nombre"] for f in flotas]
        flota_filter_var = ctk.StringVar(value="Todos los equipos")
        ctk.CTkOptionMenu(
            ctrl, values=flota_names, variable=flota_filter_var,
            fg_color=T.INPUT_BG, button_color=T.INPUT_BG,
            button_hover_color=T.INPUT_HOVER, text_color=T.TEXT,
            dropdown_fg_color=T.CARD_BG, dropdown_text_color=T.TEXT,
        ).grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 8))

        msg_var = ctk.StringVar()
        msg_lbl = ctk.CTkLabel(ctrl, textvariable=msg_var, font=T.FONT_SMALL,
                               text_color=T.DANGER, anchor="w")
        msg_lbl.grid(row=2, column=0, columnspan=3, sticky="w", padx=4)

        # ── Tabla de ingreso por equipo ────────────────────────────────
        entry_card = Card(self.content, title="Producción por equipo", light=True)
        entry_card.pack(fill="x", pady=(0, 8))

        if not equipos_list:
            ctk.CTkLabel(entry_card,
                         text="Registra equipos en la pestaña 'Equipos' primero.",
                         font=T.FONT_BODY, text_color=T.TEXT_MUTED).pack(pady=18)
            return

        tbl_frame = ctk.CTkFrame(entry_card, fg_color="transparent")
        tbl_frame.pack(fill="x", padx=18, pady=(0, 8))
        COL_WIDTHS = [150, 120, 140, 120, 110, 75, 145]
        COL_HDRS = ["Equipo", "Tipo", "Flota",
                    "Horas trabajadas", "Producción",
                    "Unidad", "Rendimiento calc."]
        for c, (hdr, w) in enumerate(zip(COL_HDRS, COL_WIDTHS)):
            tbl_frame.grid_columnconfigure(c, weight=w, uniform="rc")
            ctk.CTkLabel(tbl_frame, text=hdr.upper(), font=T.FONT_TINY,
                         text_color=T.TEXT_MUTED, anchor="w").grid(
                             row=0, column=c, sticky="ew", padx=8, pady=(0, 6))
        ctk.CTkFrame(tbl_frame, height=1, fg_color=T.CARD_BORDER).grid(
            row=1, column=0, columnspan=7, sticky="ew", pady=(0, 2))

        row_entries: list[dict] = []
        for r_idx, eq in enumerate(equipos_list):
            fl = eq_to_flota.get(eq["id"])
            flota_name = fl["nombre"] if fl else "Sin flota"
            for c, (txt, color) in enumerate([
                (eq.get("nombre", ""), T.TEXT),
                (eq.get("tipo", ""),   T.TEXT_MUTED),
                (flota_name,           T.TEXT_MUTED),
            ]):
                ctk.CTkLabel(tbl_frame, text=txt, font=T.FONT_BODY,
                             text_color=color, anchor="w").grid(
                                 row=r_idx + 2, column=c,
                                 sticky="ew", padx=8, pady=4)

            e_horas = ctk.CTkEntry(tbl_frame, placeholder_text="0.0",
                                   fg_color=T.INPUT_BG, text_color=T.TEXT,
                                   border_color=T.CARD_BORDER)
            e_horas.grid(row=r_idx + 2, column=3,
                         padx=8, pady=4, sticky="ew")

            e_prod = ctk.CTkEntry(tbl_frame, placeholder_text="0",
                                  fg_color=T.INPUT_BG, text_color=T.TEXT,
                                  border_color=T.CARD_BORDER)
            e_prod.grid(row=r_idx + 2, column=4,
                        padx=8, pady=4, sticky="ew")

            ctk.CTkLabel(tbl_frame, text=eq.get("unidad_produccion", "m³"),
                         font=T.FONT_BODY, text_color=T.TEXT_MUTED,
                         anchor="w").grid(row=r_idx + 2, column=5,
                                          sticky="ew", padx=8, pady=4)

            rend_lbl = ctk.CTkLabel(tbl_frame, text="—", font=T.FONT_BODY,
                                    text_color=T.TEXT_MUTED, anchor="w")
            rend_lbl.grid(row=r_idx + 2, column=6,
                          sticky="ew", padx=8, pady=4)

            def _upd(event=None, _h=e_horas, _p=e_prod,
                     _r=rend_lbl, _eq=eq):
                try:
                    h = float(_h.get())
                    p = float(_p.get())
                    r = p / h if h > 0 else 0.0
                    u = _eq.get("unidad_produccion", "m³")
                    _r.configure(text=f"{r:.2f} {u}/h",
                                 text_color=T.SUCCESS)
                except (ValueError, ZeroDivisionError):
                    _r.configure(text="—", text_color=T.TEXT_MUTED)

            e_horas.bind("<KeyRelease>", _upd)
            e_prod.bind("<KeyRelease>", _upd)
            row_entries.append({"equipo": eq, "flota": fl,
                                 "e_horas": e_horas, "e_prod": e_prod})

        def _guardar_registro():
            fecha_str = fecha_var.get().strip()
            try:
                date.fromisoformat(fecha_str)
            except ValueError:
                msg_var.set("Fecha inválida — usa formato YYYY-MM-DD")
                msg_lbl.configure(text_color=T.DANGER)
                return

            saved = 0
            for entry in row_entries:
                h_str = entry["e_horas"].get().strip()
                p_str = entry["e_prod"].get().strip()
                if not h_str and not p_str:
                    continue
                try:
                    h = float(h_str) if h_str else 0.0
                    p = float(p_str) if p_str else 0.0
                except ValueError:
                    msg_var.set("Valores numéricos inválidos")
                    msg_lbl.configure(text_color=T.DANGER)
                    return
                eq = entry["equipo"]
                fl = entry["flota"]
                rend = p / h if h > 0 else 0.0
                self.state.save_registro_equipo({
                    "fecha": fecha_str,
                    "equipo_id": eq["id"],
                    "equipo_nombre": eq.get("nombre", ""),
                    "equipo_tipo": eq.get("tipo", ""),
                    "flota_id": fl["id"] if fl else "",
                    "flota_nombre": fl["nombre"] if fl else "Sin flota",
                    "horas_trabajadas": h,
                    "produccion": p,
                    "unidad_produccion": eq.get("unidad_produccion", "m³"),
                    "rendimiento": rend,
                })
                saved += 1

            if saved == 0:
                msg_var.set("Ingresa al menos una fila con datos")
                msg_lbl.configure(text_color=T.DANGER)
                return

            for entry in row_entries:
                entry["e_horas"].delete(0, "end")
                entry["e_prod"].delete(0, "end")
            msg_lbl.configure(text_color=T.SUCCESS)
            msg_var.set(f"✓ {saved} registros guardados para {fecha_str}")
            if self.on_updated:
                self.on_updated()

        ctk.CTkButton(
            entry_card, text="💾  Guardar registro del día",
            command=_guardar_registro,
            fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOV,
            text_color=T.TEXT_ON_DARK, font=T.FONT_BODY,
            height=36, corner_radius=8,
        ).pack(padx=18, pady=(4, 14), anchor="e")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 4 — Rendimientos
    # ═══════════════════════════════════════════════════════════════════
    def _render_rendimientos(self):
        df_raw = self.state.load_registros_equipos()

        # ── KPIs de resumen ────────────────────────────────────────────
        if not df_raw.empty:
            today = df_raw["fecha"].max()
            today_df = df_raw[df_raw["fecha"] == today]
            equipo_count = int(today_df["equipo_nombre"].nunique())
            avg_rend = float(today_df["rendimiento"].mean()) if not today_df.empty else 0.0
            total_rec = len(df_raw)
        else:
            today = None
            equipo_count = 0
            avg_rend = 0.0
            total_rec = 0

        kpi_row = ctk.CTkFrame(self.content, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(12, 8))
        kpi_row.grid_columnconfigure((0, 1, 2), weight=1)
        for col, (icon, chip, lbl, val) in enumerate([
            ("🚜", "blue",   "Equipos activos hoy",  str(equipo_count)),
            ("📈", "green",  "Rend. promedio (hoy)",
             f"{avg_rend:.2f} u/h" if avg_rend else "—"),
            ("📅", "indigo", "Registros totales",    str(total_rec)),
        ]):
            KPICardIcon(kpi_row, icon, chip, lbl, val).grid(
                row=0, column=col, sticky="nsew", padx=4)

        # ── Tabla de análisis ──────────────────────────────────────────
        tbl_card = Card(
            self.content,
            title="Análisis de rendimiento — comparación con día anterior",
            light=True,
        )
        tbl_card.pack(fill="x", pady=(0, 8))

        if df_raw.empty:
            ctk.CTkLabel(
                tbl_card,
                text="Sin registros. Ingresa datos en la pestaña 'Registro Diario'.",
                font=T.FONT_BODY, text_color=T.TEXT_MUTED,
            ).pack(pady=18)
            return

        # Calcular rendimiento del día anterior por equipo
        df = df_raw.sort_values(["equipo_id", "fecha"])
        df["rend_anterior"] = df.groupby("equipo_id")["rendimiento"].shift(1)
        df["variacion_pct"] = (
            (df["rendimiento"] - df["rend_anterior"])
            / df["rend_anterior"].abs().replace(0, float("nan"))
        ) * 100
        display_df = df.sort_values("fecha", ascending=False).head(50)

        tbl = DataTable(
            tbl_card,
            columns=["Equipo", "Tipo", "Flota", "Fecha",
                     "Horas", "Producción", "Rend. hoy",
                     "Rend. ayer", "Variación"],
            widths=[130, 110, 120, 85, 65, 100, 100, 90, 90],
        )
        tbl.pack(fill="x", padx=18, pady=(0, 14))

        for _, r in display_df.iterrows():
            fecha_str = (r["fecha"].strftime("%d/%m/%Y")
                         if pd.notna(r["fecha"]) else "—")
            u = r.get("unidad_produccion", "m³")
            prod_val = r.get("produccion")
            rend_val = r.get("rendimiento")
            rend_ant_val = r.get("rend_anterior")
            horas_val = r.get("horas_trabajadas")

            prod_str = f"{prod_val:,.1f} {u}" if pd.notna(prod_val) else "—"
            rend_str = f"{rend_val:.2f} {u}/h" if pd.notna(rend_val) else "—"
            rend_ant_str = f"{rend_ant_val:.2f}" if pd.notna(rend_ant_val) else "—"
            horas_str = f"{horas_val:.1f} h" if pd.notna(horas_val) else "—"

            var_pct = r.get("variacion_pct")
            if pd.notna(var_pct):
                up = float(var_pct) >= 0
                arrow = "↗" if up else "↘"
                var_lbl = ctk.CTkLabel(
                    tbl, text=f"{arrow} {abs(float(var_pct)):.1f}%",
                    font=T.FONT_BODY,
                    text_color=T.SUCCESS if up else T.DANGER,
                    anchor="w",
                )
            else:
                var_lbl = ctk.CTkLabel(tbl, text="—", font=T.FONT_BODY,
                                       text_color=T.TEXT_MUTED, anchor="w")

            tbl.add_row([
                r.get("equipo_nombre", ""),
                r.get("equipo_tipo", ""),
                r.get("flota_nombre", ""),
                fecha_str, horas_str, prod_str,
                rend_str, rend_ant_str, var_lbl,
            ])

        # ── Tabla de resumen por flota ─────────────────────────────────
        if "flota_nombre" in df_raw.columns and not df_raw.empty:
            sum_card = Card(self.content,
                            title="Resumen de rendimiento por flota",
                            light=True)
            sum_card.pack(fill="x", pady=(0, 8))

            latest_date = df_raw["fecha"].max()
            day_df = df_raw[df_raw["fecha"] == latest_date]
            if not day_df.empty:
                grouped = (
                    day_df.groupby("flota_nombre")
                    .agg(
                        equipos=("equipo_nombre", "nunique"),
                        horas_totales=("horas_trabajadas", "sum"),
                        produccion_total=("produccion", "sum"),
                    )
                    .reset_index()
                )
                s_tbl = DataTable(
                    sum_card,
                    columns=["Flota", "Equipos", "Horas totales",
                             "Producción total", "Rend. flota"],
                    widths=[180, 80, 120, 140, 130],
                )
                s_tbl.pack(fill="x", padx=18, pady=(0, 14))
                for _, row in grouped.iterrows():
                    ht = float(row["horas_totales"])
                    pt = float(row["produccion_total"])
                    rf = pt / ht if ht > 0 else 0.0
                    s_tbl.add_row([
                        row["flota_nombre"],
                        str(int(row["equipos"])),
                        f"{ht:.1f} h",
                        f"{pt:,.1f}",
                        f"{rf:.2f} u/h",
                    ])
                ctk.CTkLabel(
                    sum_card,
                    text=f"Datos del {latest_date.strftime('%d/%m/%Y')}",
                    font=T.FONT_TINY, text_color=T.TEXT_MUTED,
                ).pack(anchor="e", padx=18, pady=(0, 8))
