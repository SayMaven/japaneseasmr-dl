import ctypes
import sys
import tkinter as tk
from i18n import t


def apply_dark_titlebar(window):
    """Menerapkan Dark Titlebar pada Windows 10/11 agar titlebar jendela utama ikut berwarna gelap."""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        value = ctypes.c_int(2)
        set_attr = ctypes.windll.dwmapi.DwmSetWindowAttribute
        if set_attr(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)) != 0:
            set_attr(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


class InAppModal:
    """Modal Dialog In-App yang muncul melayang elegan di tengah jendela aplikasi tanpa menutupi background."""
    @staticmethod
    def show(parent, title, message, dialog_type="info", confirm_text="OK", cancel_text="Batal"):
        result = [False]
        wait_var = tk.BooleanVar(parent, value=False)

        type_configs = {
            "info": {"bg": "#50fa7b", "fg": "#1e1e2e", "symbol": "i", "title": title or "Selesai", "title_color": "#50fa7b", "border": "#50fa7b"},
            "warning": {"bg": "#f1fa8c", "fg": "#1e1e2e", "symbol": "!", "title": title or "Peringatan", "title_color": "#f1fa8c", "border": "#f1fa8c"},
            "error": {"bg": "#ff5555", "fg": "#ffffff", "symbol": "✕", "title": title or "Error", "title_color": "#ff5555", "border": "#ff5555"},
            "question": {"bg": "#8be9fd", "fg": "#1e1e2e", "symbol": "?", "title": title or "Konfirmasi", "title_color": "#8be9fd", "border": "#bd93f9"},
        }
        cfg = type_configs.get(dialog_type, type_configs["info"])

        # Card Dialog Melayang di Tengah Jendela (Tanpa Frame Hitam Fullscreen)
        outer_card = tk.Frame(parent, bg=cfg["border"], bd=2)
        outer_card.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(outer_card, bg="#282a36", padx=26, pady=22)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        # Header (Canvas Badge + Judul)
        header = tk.Frame(card, bg="#282a36")
        header.pack(fill="x", pady=(0, 14))

        badge = tk.Canvas(header, width=30, height=30, bg="#282a36", highlightthickness=0)
        badge.pack(side="left", padx=(0, 12))
        badge.create_oval(2, 2, 28, 28, fill=cfg["bg"], outline=cfg["bg"])
        badge.create_text(15, 15, text=cfg["symbol"], fill=cfg["fg"], font=("Segoe UI", 12, "bold"))

        lbl_title = tk.Label(header, text=cfg["title"], font=("Segoe UI", 12, "bold"), bg="#282a36", fg=cfg["title_color"])
        lbl_title.pack(side="left", anchor="center")

        # Message Text
        msg_frame = tk.Frame(card, bg="#282a36")
        msg_frame.pack(fill="both", expand=True, pady=(0, 20))

        lbl_msg = tk.Label(
            msg_frame,
            text=message,
            font=("Segoe UI", 10),
            bg="#282a36",
            fg="#f8f8f2",
            wraplength=420,
            justify="left",
            anchor="w",
        )
        lbl_msg.pack(fill="x")

        # Action Buttons
        btn_frame = tk.Frame(card, bg="#282a36")
        btn_frame.pack(fill="x")

        def _close(val):
            if outer_card.winfo_exists():
                result[0] = val
                outer_card.destroy()
                wait_var.set(True)

        if dialog_type == "question":
            btn_cancel = tk.Button(
                btn_frame,
                text=cancel_text,
                font=("Segoe UI", 9),
                bg="#44475a",
                fg="#f8f8f2",
                activebackground="#6272a4",
                activeforeground="#ffffff",
                bd=0,
                padx=18,
                pady=6,
                cursor="hand2",
                command=lambda: _close(False),
            )
            btn_cancel.pack(side="right", padx=(10, 0))

            btn_ok = tk.Button(
                btn_frame,
                text=confirm_text,
                font=("Segoe UI", 9, "bold"),
                bg="#bd93f9",
                fg="#1e1e2e",
                activebackground="#ff79c6",
                bd=0,
                padx=18,
                pady=6,
                cursor="hand2",
                command=lambda: _close(True),
            )
            btn_ok.pack(side="right")
            btn_ok.focus_set()
        else:
            btn_ok = tk.Button(
                btn_frame,
                text=confirm_text,
                font=("Segoe UI", 9, "bold"),
                bg="#bd93f9",
                fg="#1e1e2e",
                activebackground="#ff79c6",
                bd=0,
                padx=24,
                pady=6,
                cursor="hand2",
                command=lambda: _close(True),
            )
            btn_ok.pack(side="right")
            btn_ok.focus_set()

        parent.bind("<Return>", lambda e: _close(True) if outer_card.winfo_exists() else None)
        parent.bind("<Escape>", lambda e: _close(False) if outer_card.winfo_exists() else None)

        outer_card.lift()
        parent.wait_variable(wait_var)
        return result[0]


def show_dark_info(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="info", confirm_text=t("btn_ok"))


def show_dark_warning(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="warning", confirm_text=t("btn_understand"))


def show_dark_error(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="error", confirm_text=t("btn_close"))


def ask_dark_yesno(parent, title, message, confirm_text=None, cancel_text=None):
    c_text = confirm_text or t("btn_yes")
    can_text = cancel_text or t("btn_no")
    return InAppModal.show(parent, title, message, dialog_type="question", confirm_text=c_text, cancel_text=can_text)

