import ctypes
import sys
import tkinter as tk
import customtkinter as ctk

from i18n import t
from ui.theme import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BORDER_SUBTLE,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SUBTITLE,
    RADIUS_LG,
    RADIUS_MD,
    STATUS_DANGER,
    STATUS_INFO,
    STATUS_SUCCESS,
    STATUS_WARNING,
    SURFACE_CARD,
    SURFACE_ELEVATED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def apply_dark_titlebar(window):
    """Apply modern dark titlebar styling on Windows 10/11 using DWM attributes."""
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
    """Modern CustomTkinter-based in-app modal dialog with card elevation and rounded corners."""
    @staticmethod
    def show(parent, title, message, dialog_type="info", confirm_text="OK", cancel_text="Batal"):
        result = [False]
        wait_var = tk.BooleanVar(parent, value=False)

        type_configs = {
            "info": {
                "bg": STATUS_INFO,
                "symbol": "ℹ",
                "title": title or "Informasi",
                "title_color": STATUS_INFO,
                "border": BORDER_SUBTLE,
            },
            "warning": {
                "bg": STATUS_WARNING,
                "symbol": "⚠",
                "title": title or "Peringatan",
                "title_color": STATUS_WARNING,
                "border": STATUS_WARNING,
            },
            "error": {
                "bg": STATUS_DANGER,
                "symbol": "✕",
                "title": title or "Error",
                "title_color": STATUS_DANGER,
                "border": STATUS_DANGER,
            },
            "question": {
                "bg": ACCENT_PRIMARY,
                "symbol": "?",
                "title": title or "Konfirmasi",
                "title_color": ACCENT_PRIMARY,
                "border": ACCENT_PRIMARY,
            },
        }
        cfg = type_configs.get(dialog_type, type_configs["info"])

        # Centered floating dialog card
        card = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_LG,
            fg_color=SURFACE_ELEVATED,
            border_width=1,
            border_color=cfg["border"],
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(padx=24, pady=20, fill="both", expand=True)

        # Header (Status Badge and Title)
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        badge = ctk.CTkLabel(
            header,
            text=f" {cfg['symbol']} ",
            font=("Segoe UI", 13, "bold"),
            fg_color=cfg["bg"],
            text_color="#151821",
            corner_radius=12,
            width=28,
            height=28,
        )
        badge.pack(side="left", padx=(0, 10))

        lbl_title = ctk.CTkLabel(
            header,
            text=cfg["title"],
            font=FONT_SUBTITLE,
            text_color=cfg["title_color"],
            anchor="w",
        )
        lbl_title.pack(side="left", fill="x", expand=True)

        # Message Text
        lbl_msg = ctk.CTkLabel(
            content,
            text=message,
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            wraplength=440,
            justify="left",
            anchor="w",
        )
        lbl_msg.pack(fill="x", pady=(0, 20))

        # Action Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")

        def _close(val):
            if card.winfo_exists():
                result[0] = val
                card.destroy()
                wait_var.set(True)

        if dialog_type == "question":
            btn_cancel = ctk.CTkButton(
                btn_frame,
                text=cancel_text,
                font=FONT_BODY,
                fg_color=SURFACE_CARD,
                hover_color=BORDER_SUBTLE,
                text_color=TEXT_SECONDARY,
                corner_radius=RADIUS_MD,
                height=32,
                width=90,
                command=lambda: _close(False),
            )
            btn_cancel.pack(side="right", padx=(8, 0))

            btn_ok = ctk.CTkButton(
                btn_frame,
                text=confirm_text,
                font=FONT_BODY_BOLD,
                fg_color=ACCENT_PRIMARY,
                hover_color=ACCENT_HOVER,
                text_color="#ffffff",
                corner_radius=RADIUS_MD,
                height=32,
                width=100,
                command=lambda: _close(True),
            )
            btn_ok.pack(side="right")
            btn_ok.focus_set()
        else:
            btn_ok = ctk.CTkButton(
                btn_frame,
                text=confirm_text,
                font=FONT_BODY_BOLD,
                fg_color=ACCENT_PRIMARY,
                hover_color=ACCENT_HOVER,
                text_color="#ffffff",
                corner_radius=RADIUS_MD,
                height=32,
                width=100,
                command=lambda: _close(True),
            )
            btn_ok.pack(side="right")
            btn_ok.focus_set()

        parent.bind("<Return>", lambda e: _close(True) if card.winfo_exists() else None)
        parent.bind("<Escape>", lambda e: _close(False) if card.winfo_exists() else None)

        card.lift()
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
