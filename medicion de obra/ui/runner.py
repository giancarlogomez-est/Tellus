"""Ventana modal para ejecutar un subproceso y mostrar su salida en vivo."""
from __future__ import annotations

import threading
import customtkinter as ctk

from . import theme as T


class ProcessDialog(ctk.CTkToplevel):
    """Diálogo que ejecuta una función que devuelve un subprocess.Popen
    y va volcando stdout en una caja de texto."""

    def __init__(self, master, titulo: str, popen_factory,
                 on_done=None):
        super().__init__(master)
        self.title(titulo)
        self.geometry("780x520")
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        self._on_done = on_done
        self._proc = None
        self._terminado = False

        ctk.CTkLabel(self, text=titulo, font=T.FONT_H1).pack(
            anchor="w", padx=20, pady=(18, 6))

        self.estado = ctk.CTkLabel(self, text="● Ejecutando…",
                                   font=T.FONT_BODY, text_color=T.WARNING)
        self.estado.pack(anchor="w", padx=20, pady=(0, 10))

        self.txt = ctk.CTkTextbox(self, font=T.FONT_MONO, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.txt.configure(state="disabled")

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=20, pady=(0, 16))
        self.btn_cerrar = ctk.CTkButton(
            botones, text="Cerrar", state="disabled",
            command=self._cerrar, width=120)
        self.btn_cerrar.pack(side="right")

        threading.Thread(target=self._ejecutar,
                         args=(popen_factory,), daemon=True).start()

    def _ejecutar(self, factory):
        try:
            self._proc = factory()
            for line in self._proc.stdout:  # type: ignore[union-attr]
                self._append(line)
            self._proc.wait()
            ok = self._proc.returncode == 0
        except Exception as e:
            self._append(f"\n[ERROR] {e}\n")
            ok = False
        self.after(0, self._finalizar, ok)

    def _append(self, line: str):
        def _do():
            self.txt.configure(state="normal")
            self.txt.insert("end", line)
            self.txt.see("end")
            self.txt.configure(state="disabled")
        self.after(0, _do)

    def _finalizar(self, ok: bool):
        self._terminado = True
        if ok:
            self.estado.configure(text="● Proceso finalizado correctamente",
                                  text_color=T.SUCCESS)
        else:
            self.estado.configure(text="● Proceso terminó con errores",
                                  text_color=T.DANGER)
        self.btn_cerrar.configure(state="normal")
        if self._on_done:
            try:
                self._on_done(ok)
            except Exception:
                pass

    def _cerrar(self):
        if not self._terminado and self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self.destroy()
