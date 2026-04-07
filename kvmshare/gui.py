"""
KVMShare — GUI de disposición de pantallas
Permite configurar la posición relativa del Mac respecto a este PC.
"""

import tkinter as tk
from tkinter import messagebox

from .config import Config

# (row, col) en la cuadrícula 3×3 con el PC en el centro (1,1)
_POS_GRID = {
    "above": (0, 1),
    "left":  (1, 0),
    "right": (1, 2),
    "below": (2, 1),
}

_POS_LABEL = {
    "above": "Arriba",
    "left":  "Izquierda",
    "right": "Derecha",
    "below": "Abajo",
}

# Colores (estilo oscuro)
_BG        = "#1e1e2e"
_CARD      = "#313244"
_CARD_SEL  = "#89b4fa"
_FG        = "#cdd6f4"
_FG_SEL    = "#1e1e2e"
_FG_DIM    = "#a6adc8"
_ACCENT    = "#89b4fa"
_BTN_SAVE  = "#a6e3a1"
_BTN_SAVE_FG = "#1e1e2e"


class LayoutGUI:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.cfg = Config.from_file(config_path)

        self.root = tk.Tk()
        self.root.title("KVMShare — Pantallas")
        self.root.resizable(False, False)
        self.root.configure(bg=_BG)
        self._build()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        root = self.root

        # ── Title ──────────────────────────────────────────────────────
        tk.Label(root, text="KVMShare", bg=_BG, fg=_ACCENT,
                 font=("Helvetica", 20, "bold")).pack(pady=(22, 2))
        tk.Label(root, text="Elige dónde está el Mac respecto a este PC",
                 bg=_BG, fg=_FG_DIM, font=("Helvetica", 10)).pack(pady=(0, 18))

        # ── Screen grid ────────────────────────────────────────────────
        grid = tk.Frame(root, bg=_BG)
        grid.pack(padx=30)

        # Corner spacers
        for r, c in [(0, 0), (0, 2), (2, 0), (2, 2)]:
            tk.Label(grid, bg=_BG, width=13, height=5).grid(row=r, column=c, padx=5, pady=5)

        # "Este PC" fixed at center
        pc_frame = tk.Frame(grid, bg=_CARD, width=120, height=80, relief="solid", bd=1)
        pc_frame.grid(row=1, column=1, padx=5, pady=5)
        pc_frame.pack_propagate(False)
        tk.Label(pc_frame, text="Este PC", bg=_CARD, fg=_FG,
                 font=("Helvetica", 10, "bold")).place(relx=0.5, rely=0.4, anchor="center")
        tk.Label(pc_frame, text="Servidor", bg=_CARD, fg=_FG_DIM,
                 font=("Helvetica", 8)).place(relx=0.5, rely=0.65, anchor="center")

        # Mac buttons
        self._mac_frames: dict[str, tk.Frame] = {}
        for pos, (row, col) in _POS_GRID.items():
            frame = tk.Frame(grid, width=120, height=80, relief="solid", bd=1, cursor="hand2")
            frame.grid(row=row, column=col, padx=5, pady=5)
            frame.pack_propagate(False)
            frame.bind("<Button-1>", lambda e, p=pos: self._select(p))

            lbl_name = tk.Label(frame, text="Mac", font=("Helvetica", 10, "bold"))
            lbl_name.place(relx=0.5, rely=0.4, anchor="center")
            lbl_name.bind("<Button-1>", lambda e, p=pos: self._select(p))

            lbl_pos = tk.Label(frame, font=("Helvetica", 8))
            lbl_pos.place(relx=0.5, rely=0.65, anchor="center")
            lbl_pos.bind("<Button-1>", lambda e, p=pos: self._select(p))

            self._mac_frames[pos] = frame

        # ── Status ─────────────────────────────────────────────────────
        self._status_var = tk.StringVar()
        tk.Label(root, textvariable=self._status_var,
                 bg=_BG, fg=_FG_DIM, font=("Helvetica", 9)).pack(pady=(16, 6))

        # ── Save button ────────────────────────────────────────────────
        tk.Button(
            root, text="  Guardar  ", command=self._save,
            bg=_BTN_SAVE, fg=_BTN_SAVE_FG,
            font=("Helvetica", 10, "bold"),
            relief="flat", padx=20, pady=8, cursor="hand2",
            activebackground="#94e2b8", activeforeground=_BTN_SAVE_FG,
        ).pack(pady=(0, 24))

        self._refresh()

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _select(self, position: str):
        self.cfg.remote_position = position
        self._refresh()

    def _refresh(self):
        sel = self.cfg.remote_position
        self._status_var.set(
            f"Configuración actual: Mac a la {_POS_LABEL.get(sel, sel).lower()} de este PC"
        )
        for pos, frame in self._mac_frames.items():
            selected = pos == sel
            bg = _CARD_SEL if selected else _CARD
            fg = _FG_SEL if selected else _FG
            fg_dim = _FG_SEL if selected else _FG_DIM
            frame.configure(bg=bg)
            for child in frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=bg)
                    # Distinguish title vs subtitle by font size
                    if child.cget("font") and "bold" in str(child.cget("font")):
                        child.configure(fg=fg)
                    else:
                        child.configure(fg=fg_dim, text=_POS_LABEL[pos])

    def _save(self):
        try:
            self.cfg.save(self.config_path)
            sel = self.cfg.remote_position
            self._status_var.set(
                f"✓ Guardado — Mac a la {_POS_LABEL.get(sel, sel).lower()}"
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar: {exc}")

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        self.root.mainloop()
