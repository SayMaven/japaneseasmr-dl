"""
In-App Toast Notification System untuk JapaneseASMR Downloader v1.2.0.
Menampilkan notifikasi mengambang (floating card) non-blocking di pojok kanan bawah
jendela aplikasi dengan desain Tokyo Night modern, auto-dismiss, dan zero emoji.
"""
import tkinter as tk
import customtkinter as ctk
from typing import Optional

from ui.icons import get_icon
from ui.theme import (
    BORDER_ACTIVE,
    BORDER_SUBTLE,
    FONT_BODY_BOLD,
    FONT_CAPTION,
    RADIUS_BUTTON,
    RADIUS_CARD,
    STATUS_DANGER,
    STATUS_INFO,
    STATUS_SUCCESS,
    STATUS_WARNING,
    SURFACE_ELEVATED,
    SURFACE_INPUT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class ToastNotification(ctk.CTkFrame):
    """
    Komponen Toast Notification non-blocking.
    Mengambang di sudut kanan bawah jendela utama tanpa mencuri fokus atau memblokir klik.
    """
    def __init__(
        self,
        parent: ctk.CTk,
        title: str,
        message: str,
        toast_type: str = "success",
        duration_ms: int = 4000,
    ):
        # Jika ada toast lama yang masih tampil di window, bersihkan terlebih dahulu
        old_toast = getattr(parent, "_active_toast", None)
        if old_toast and old_toast.winfo_exists():
            try:
                old_toast.dismiss()
            except Exception:
                pass

        super().__init__(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_ELEVATED,
            border_width=1,
            border_color=BORDER_ACTIVE,
        )
        self.parent = parent
        parent._active_toast = self

        type_configs = {
            "success": {
                "accent": STATUS_SUCCESS,
                "icon": "check",
            },
            "info": {
                "accent": STATUS_INFO,
                "icon": "check",
            },
            "warning": {
                "accent": STATUS_WARNING,
                "icon": "check",
            },
            "error": {
                "accent": STATUS_DANGER,
                "icon": "check",
            },
        }
        cfg = type_configs.get(toast_type, type_configs["success"])

        # Inner container dengan padding
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(padx=14, pady=12, fill="both", expand=True)

        # 1. Indikator Icon di sebelah kiri
        icon_badge = ctk.CTkLabel(
            inner,
            text="",
            image=get_icon(cfg["icon"], size=(20, 20), color=cfg["accent"]),
            width=28,
            height=28,
            fg_color=SURFACE_INPUT,
            corner_radius=14,
        )
        icon_badge.pack(side="left", padx=(0, 12), anchor="center")

        # 2. Text Container (Judul & Pesan)
        text_frame = ctk.CTkFrame(inner, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        lbl_title = ctk.CTkLabel(
            text_frame,
            text=title,
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", anchor="w")

        lbl_msg = ctk.CTkLabel(
            text_frame,
            text=message,
            font=FONT_CAPTION,
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=280,
        )
        lbl_msg.pack(fill="x", anchor="w", pady=(2, 0))

        # 3. Tombol Tutup (✕) Minimalis
        btn_close = ctk.CTkButton(
            inner,
            text="✕",
            font=("Segoe UI", 11, "bold"),
            width=24,
            height=24,
            corner_radius=12,
            fg_color="transparent",
            hover_color=SURFACE_INPUT,
            text_color=TEXT_MUTED,
            command=self.dismiss,
        )
        btn_close.pack(side="right", anchor="n", padx=(4, 0))

        # Tampilkan toast di pojok kanan bawah
        self.place(relx=0.98, rely=0.96, anchor="se")
        self.lift()

        # Timer auto-dismiss
        self._dismiss_job = None
        if duration_ms > 0:
            self._dismiss_job = self.after(duration_ms, self.dismiss)

    def dismiss(self):
        """Menutup dan menghancurkan widget toast secara aman."""
        if self._dismiss_job is not None:
            try:
                self.after_cancel(self._dismiss_job)
            except Exception:
                pass
            self._dismiss_job = None

        if hasattr(self.parent, "_active_toast") and self.parent._active_toast == self:
            self.parent._active_toast = None

        try:
            self.place_forget()
            self.destroy()
        except Exception:
            pass


def show_toast(
    parent: ctk.CTk,
    title: str,
    message: str,
    toast_type: str = "success",
    duration_ms: int = 4000,
) -> Optional[ToastNotification]:
    """
    Fungsi helper utama untuk menampilkan toast notification di jendela parent.
    Aman dipanggil langsung dari thread utama Tkinter.
    """
    if not parent or not parent.winfo_exists():
        return None
    try:
        return ToastNotification(
            parent=parent,
            title=title,
            message=message,
            toast_type=toast_type,
            duration_ms=duration_ms,
        )
    except Exception as e:
        print(f"[ui.toast] Gagal menampilkan toast notification: {e}")
        return None

