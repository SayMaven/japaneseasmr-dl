import html
import io
import json
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.request
import webbrowser
from PIL import Image, ImageTk

from config_manager import (
    add_to_history,
    cache_cover_image,
    clear_all_history,
    clear_cover_cache,
    clear_temp_cache,
    discover_all_audio_tracks,
    get_bin_executable,
    get_cache_size_info,
    get_download_dir,
    get_ytdlp_version,
    load_config,
    load_history,
    resolve_audio_url,
    save_config,
    set_download_dir,
    update_ytdlp_engine,
)

REFERER = "https://japaneseasmr.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Regex Progress Parsing untuk yt-dlp & aria2c
RE_YTDLP_PROGRESS = re.compile(
    r'\[download\]\s+([\d\.]+)%\s+of\s+~?\s*([\d\.]+[kMGTP]?i?B)(?:\s+at\s+([\d\.]+[kMGTP]?i?B/s))?(?:\s+ETA\s+([\d:]+))?',
    re.IGNORECASE,
)
RE_ARIA2_PROGRESS = re.compile(
    r'\[#\w+\s+([\d\.]+[kMGTP]?i?B)/([\d\.]+[kMGTP]?i?B)\s*\(([\d\.]+)%\).*?DL:([\d\.]+[kMGTP]?i?B).*?ETA:([\w\d]+)\]',
    re.IGNORECASE,
)
RE_FRAG_PROGRESS = re.compile(
    r'\[download\]\s+Downloading\s+(?:item|fragment)\s+(\d+)\s+of\s+(\d+)',
    re.IGNORECASE,
)

import ctypes


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
    InAppModal.show(parent, title, message, dialog_type="info", confirm_text="OK")


def show_dark_warning(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="warning", confirm_text="Mengerti")


def show_dark_error(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="error", confirm_text="Tutup")


def ask_dark_yesno(parent, title, message, confirm_text="Ya", cancel_text="Batal"):
    return InAppModal.show(parent, title, message, dialog_type="question", confirm_text=confirm_text, cancel_text=cancel_text)


class SettingsDialog(tk.Toplevel):
    """Dialog Pengaturan Modern dengan Sidebar Navigasi Vertikal (Kiri) dan Panel Konten (Kanan)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Pengaturan - JapaneseASMR Downloader")
        self.geometry("740x520")
        self.minsize(700, 480)
        self.configure(bg="#1e1e2e")
        self.transient(parent)
        apply_dark_titlebar(self)

        self.parent._settings_dialog = self
        self.protocol("WM_DELETE_WINDOW", self._on_dialog_close)

        # Set Window Icon pada dialog
        if hasattr(parent, "_icon_ico_path") and parent._icon_ico_path and os.path.exists(parent._icon_ico_path):
            try:
                self.iconbitmap(default=parent._icon_ico_path)
            except Exception:
                pass

        # Posisikan dialog di tengah window parent
        try:
            parent.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_x()
            py = parent.winfo_y()
            cx = px + (pw - 740) // 2
            cy = py + (ph - 520) // 2
            self.geometry(f"+{max(0, cx)}+{max(0, cy)}")
        except Exception:
            pass

        self.cfg = load_config()

        # Variable States
        self.var_download_dir = tk.StringVar(value=self.cfg.get("download_dir", get_download_dir()))
        self.var_detailed_name = tk.BooleanVar(value=self.cfg.get("use_detailed_filename", False))
        self.var_notify_popup = tk.BooleanVar(value=self.cfg.get("notify_popup", True))
        self.var_auto_clipboard = tk.BooleanVar(value=self.cfg.get("auto_clipboard", False))
        self.var_connections = tk.IntVar(value=self.cfg.get("connections", 16))
        self.var_ytdlp_channel = tk.StringVar(value=self.cfg.get("ytdlp_channel", "stable"))

        self.nav_buttons = {}
        self.current_tab = "general"

        self._build_ui()
        self._show_tab("general")

    def _build_ui(self):
        # 1. Header Bar Dialog
        header_bar = tk.Frame(self, bg="#282a36", height=45)
        header_bar.pack(fill="x", side="top")

        lbl_header = tk.Label(
            header_bar,
            text="Pengaturan Aplikasi",
            font=("Segoe UI", 12, "bold"),
            bg="#282a36",
            fg="#f8f8f2",
            padx=16,
            pady=10,
        )
        lbl_header.pack(side="left")

        # 2. Main Body: Sidebar (Kiri) & Content Panel (Kanan)
        body_frame = tk.Frame(self, bg="#1e1e2e")
        body_frame.pack(fill="both", expand=True)

        # Sidebar Kiri
        self.sidebar = tk.Frame(body_frame, bg="#181825", width=180)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        lbl_menu = tk.Label(
            self.sidebar,
            text="KATEGORI",
            font=("Segoe UI", 8, "bold"),
            bg="#181825",
            fg="#6272a4",
            anchor="w",
            padx=16,
            pady=12,
        )
        lbl_menu.pack(fill="x")

        # Tab Navigation Items
        tabs = [
            ("general", "Umum"),
            ("download", "Unduhan & Jaringan"),
            ("cache", "Penyimpanan & Cache"),
            ("about", "Tentang Aplikasi"),
        ]

        for tab_id, label_text in tabs:
            btn = tk.Button(
                self.sidebar,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg="#181825",
                fg="#a6adc8",
                activebackground="#282a36",
                activeforeground="#f8f8f2",
                anchor="w",
                bd=0,
                padx=16,
                pady=10,
                cursor="hand2",
                command=lambda t=tab_id: self._show_tab(t),
            )
            btn.pack(fill="x")
            self.nav_buttons[tab_id] = btn

        # Content Panel Kanan
        self.content_container = tk.Frame(body_frame, bg="#1e1e2e", padx=24, pady=16)
        self.content_container.pack(side="right", fill="both", expand=True)

        # 3. Footer Bar Dialog (Batal & Simpan)
        footer_bar = tk.Frame(self, bg="#181825", height=52)
        footer_bar.pack(fill="x", side="bottom")

        btn_save = tk.Button(
            footer_bar,
            text="Simpan Pengaturan",
            font=("Segoe UI", 9, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            activebackground="#8be9fd",
            bd=0,
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._save_settings,
        )
        btn_save.pack(side="right", padx=16, pady=10)

        btn_cancel = tk.Button(
            footer_bar,
            text="Batal",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            activebackground="#6272a4",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        )
        btn_cancel.pack(side="right", padx=(0, 8), pady=10)

    def _show_tab(self, tab_name):
        self.current_tab = tab_name

        # Update styling sidebar buttons
        for t_id, btn in self.nav_buttons.items():
            if t_id == tab_name:
                btn.config(bg="#282a36", fg="#bd93f9")
            else:
                btn.config(bg="#181825", fg="#a6adc8")

        # Clear existing content
        for child in self.content_container.winfo_children():
            child.destroy()

        if tab_name == "general":
            self._render_general_tab()
        elif tab_name == "download":
            self._render_download_tab()
        elif tab_name == "cache":
            self._render_cache_tab()
        elif tab_name == "about":
            self._render_about_tab()

    # ==================== TAB 1: UMUM ====================
    def _render_general_tab(self):
        lbl_title = tk.Label(
            self.content_container,
            text="Pengaturan Umum",
            font=("Segoe UI", 12, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 14))

        # Folder Simpan
        lbl_dir = tk.Label(
            self.content_container,
            text="Lokasi Folder Penyimpanan Download:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
            anchor="w",
        )
        lbl_dir.pack(fill="x", pady=(4, 2))

        dir_box = tk.Frame(self.content_container, bg="#1e1e2e")
        dir_box.pack(fill="x", pady=(0, 14))

        ent_dir = tk.Entry(
            dir_box,
            textvariable=self.var_download_dir,
            font=("Segoe UI", 9),
            bg="#282a36",
            fg="#f8f8f2",
            insertbackground="#f8f8f2",
            bd=1,
            relief="solid",
        )
        ent_dir.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        btn_browse = tk.Button(
            dir_box,
            text="Browse...",
            font=("Segoe UI", 9),
            bg="#6272a4",
            fg="#f8f8f2",
            activebackground="#bd93f9",
            bd=0,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._browse_dir,
        )
        btn_browse.pack(side="right")

        # Separator
        sep1 = tk.Frame(self.content_container, bg="#313244", height=1)
        sep1.pack(fill="x", pady=8)

        # Format Penamaan File
        lbl_name_opt = tk.Label(
            self.content_container,
            text="Format & Perilaku:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
            anchor="w",
        )
        lbl_name_opt.pack(fill="x", pady=(4, 6))

        chk_name = tk.Checkbutton(
            self.content_container,
            text="Gunakan Judul Asli Karya sebagai Nama File MP3 (contoh: [RJ01673437] Judul.mp3)",
            variable=self.var_detailed_name,
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#f8f8f2",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#50fa7b",
            anchor="w",
        )
        chk_name.pack(fill="x", pady=4)

        chk_notify = tk.Checkbutton(
            self.content_container,
            text="Tampilkan Kotak Dialog Notifikasi Pop-up saat Semua Unduhan Selesai",
            variable=self.var_notify_popup,
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#f8f8f2",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#50fa7b",
            anchor="w",
        )
        chk_notify.pack(fill="x", pady=4)

        chk_clip = tk.Checkbutton(
            self.content_container,
            text="Deteksi Otomatis Kode RJ dari Clipboard saat Tombol Tempel Ditekan",
            variable=self.var_auto_clipboard,
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#f8f8f2",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#50fa7b",
            anchor="w",
        )
        chk_clip.pack(fill="x", pady=4)

    def _browse_dir(self):
        new_d = filedialog.askdirectory(initialdir=self.var_download_dir.get(), title="Pilih Folder Download")
        if new_d:
            self.var_download_dir.set(new_d)

    # ==================== TAB 2: UNDUHAN ====================
    def _render_download_tab(self):
        lbl_title = tk.Label(
            self.content_container,
            text="Pengaturan Unduhan & Jaringan",
            font=("Segoe UI", 12, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 14))

        # Jumlah Koneksi Paralel
        lbl_conn = tk.Label(
            self.content_container,
            text="Jumlah Koneksi Simultan per Track (Aria2c Multi-thread):",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
            anchor="w",
        )
        lbl_conn.pack(fill="x", pady=(4, 2))

        conn_box = tk.Frame(self.content_container, bg="#1e1e2e")
        conn_box.pack(fill="x", pady=(0, 10))

        spn_conn = ttk.Spinbox(
            conn_box,
            from_=1,
            to=32,
            textvariable=self.var_connections,
            font=("Segoe UI", 9),
            width=8,
        )
        spn_conn.pack(side="left", padx=(0, 10))

        lbl_conn_hint = tk.Label(
            conn_box,
            text="Koneksi paralel (Default: 16). Semakin tinggi koneksi, unduhan semakin cepat.",
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#6272a4",
        )
        lbl_conn_hint.pack(side="left")

        # Separator
        sep1 = tk.Frame(self.content_container, bg="#313244", height=1)
        sep1.pack(fill="x", pady=10)

        # Pembaruan Engine yt-dlp Section
        lbl_upd_head = tk.Label(
            self.content_container,
            text="Pembaruan Engine yt-dlp:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
            anchor="w",
        )
        lbl_upd_head.pack(fill="x", pady=(0, 6))

        ytdlp_card = tk.Frame(self.content_container, bg="#282a36", padx=14, pady=10)
        ytdlp_card.pack(fill="x", pady=(0, 10))

        # Cek versi yt-dlp secara non-blocking di background agar UI tidak freeze
        init_ver_text = getattr(self, "_cached_ytdlp_ver", None) or "Memuat versi..."
        self.lbl_ytdlp_ver = tk.Label(
            ytdlp_card,
            text=f"Versi Terpasang: {init_ver_text}",
            font=("Segoe UI", 9, "bold"),
            bg="#282a36",
            fg="#50fa7b",
            anchor="w",
        )
        self.lbl_ytdlp_ver.pack(fill="x", pady=(0, 6))

        def _async_load_ver():
            ver = get_ytdlp_version()
            self._cached_ytdlp_ver = ver
            if self.winfo_exists() and hasattr(self, "lbl_ytdlp_ver") and self.lbl_ytdlp_ver.winfo_exists():
                self.after(0, lambda: self.lbl_ytdlp_ver.config(text=f"Versi Terpasang: {ver}"))

        threading.Thread(target=_async_load_ver, daemon=True).start()

        # Channel Selector (Stable vs Nightly)
        chan_row = tk.Frame(ytdlp_card, bg="#282a36")
        chan_row.pack(fill="x", pady=(0, 8))

        lbl_chan = tk.Label(
            chan_row,
            text="Channel Rilis:",
            font=("Segoe UI", 8, "bold"),
            bg="#282a36",
            fg="#cdd6f4",
        )
        lbl_chan.pack(side="left", padx=(0, 12))

        rb_stable = tk.Radiobutton(
            chan_row,
            text="Stable (Rilis Stabil)",
            variable=self.var_ytdlp_channel,
            value="stable",
            font=("Segoe UI", 8),
            bg="#282a36",
            fg="#f8f8f2",
            selectcolor="#181825",
            activebackground="#282a36",
            activeforeground="#50fa7b",
        )
        rb_stable.pack(side="left", padx=(0, 12))

        rb_nightly = tk.Radiobutton(
            chan_row,
            text="Nightly (Rilis Harian / Fitur Terbaru)",
            variable=self.var_ytdlp_channel,
            value="nightly",
            font=("Segoe UI", 8),
            bg="#282a36",
            fg="#f8f8f2",
            selectcolor="#181825",
            activebackground="#282a36",
            activeforeground="#bd93f9",
        )
        rb_nightly.pack(side="left")

        # Tombol Update & Status
        upd_action_row = tk.Frame(ytdlp_card, bg="#282a36")
        upd_action_row.pack(fill="x")

        self.btn_update_ytdlp = tk.Button(
            upd_action_row,
            text="Perbarui yt-dlp Sekarang",
            font=("Segoe UI", 8, "bold"),
            bg="#bd93f9",
            fg="#1e1e2e",
            activebackground="#ff79c6",
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._do_update_ytdlp,
        )
        self.btn_update_ytdlp.pack(side="left", padx=(0, 10))

        self.lbl_ytdlp_status = tk.Label(
            upd_action_row,
            text="Siap memeriksa pembaruan",
            font=("Segoe UI", 8),
            bg="#282a36",
            fg="#a6adc8",
        )
        self.lbl_ytdlp_status.pack(side="left")

    def _do_update_ytdlp(self):
        """Menjalankan proses update yt-dlp di background thread."""
        channel = self.var_ytdlp_channel.get()
        self.btn_update_ytdlp.config(state="disabled")
        self.lbl_ytdlp_status.config(text=f"Sedang memperbarui yt-dlp ({channel})...", fg="#bd93f9")

        def run_upd():
            success, msg = update_ytdlp_engine(channel=channel)
            new_ver = get_ytdlp_version()

            def done():
                self.btn_update_ytdlp.config(state="normal")
                self.lbl_ytdlp_ver.config(text=f"Versi Terpasang: {new_ver}")
                if success:
                    self.lbl_ytdlp_status.config(text=f"Sukses! Versi {new_ver}", fg="#50fa7b")
                    show_dark_info(
                        self,
                        "Pembaruan yt-dlp Selesai",
                        f"Proses pembaruan yt-dlp (Channel: {channel}) telah selesai.\n\nVersi saat ini: {new_ver}\n\nLog output:\n{msg}",
                    )
                else:
                    self.lbl_ytdlp_status.config(text="Gagal memperbarui", fg="#ff5555")
                    show_dark_error(
                        self,
                        "Pembaruan Gagal",
                        f"Gagal memperbarui yt-dlp:\n\n{msg}",
                    )

            self.after(0, done)

        threading.Thread(target=run_upd, daemon=True).start()

    # ==================== TAB 3: CACHE & DATA ====================
    def _render_cache_tab(self):
        lbl_title = tk.Label(
            self.content_container,
            text="Penyimpanan Cache & Data",
            font=("Segoe UI", 12, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 14))

        stats = get_cache_size_info()
        histories = load_history()

        # Kartu Statistik Cache
        card_cache = tk.Frame(self.content_container, bg="#282a36", padx=14, pady=12)
        card_cache.pack(fill="x", pady=(0, 14))

        self.lbl_cover_stat = tk.Label(
            card_cache,
            text=f"Cache Cover Art     : {stats['covers_count']} file ({stats['covers_size']})",
            font=("Segoe UI", 9),
            bg="#282a36",
            fg="#f8f8f2",
            anchor="w",
        )
        self.lbl_cover_stat.pack(fill="x", pady=2)

        self.lbl_temp_stat = tk.Label(
            card_cache,
            text=f"File Sementara/Part  : {stats['temp_count']} file ({stats['temp_size']})",
            font=("Segoe UI", 9),
            bg="#282a36",
            fg="#f8f8f2",
            anchor="w",
        )
        self.lbl_temp_stat.pack(fill="x", pady=2)

        self.lbl_hist_stat = tk.Label(
            card_cache,
            text=f"Riwayat Unduhan      : {len(histories)} karya tersimpan",
            font=("Segoe UI", 9),
            bg="#282a36",
            fg="#f8f8f2",
            anchor="w",
        )
        self.lbl_hist_stat.pack(fill="x", pady=2)

        # Tombol Aksi Pembersihan
        btn_box = tk.Frame(self.content_container, bg="#1e1e2e")
        btn_box.pack(fill="x", pady=4)

        btn_clear_covers = tk.Button(
            btn_box,
            text="Bersihkan Cache Cover",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#8be9fd",
            activebackground="#6272a4",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._do_clear_covers,
        )
        btn_clear_covers.pack(side="left", padx=(0, 8))

        btn_clear_temp = tk.Button(
            btn_box,
            text="Bersihkan File Sampah",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#50fa7b",
            activebackground="#6272a4",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._do_clear_temp,
        )
        btn_clear_temp.pack(side="left", padx=(0, 8))

        btn_clear_hist = tk.Button(
            btn_box,
            text="Hapus Semua Riwayat",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#ff5555",
            activebackground="#6272a4",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._do_clear_history,
        )
        btn_clear_hist.pack(side="left")

    def _do_clear_covers(self):
        clear_cover_cache()
        stats = get_cache_size_info()
        self.lbl_cover_stat.config(text=f"Cache Cover Art     : {stats['covers_count']} file ({stats['covers_size']})")
        show_dark_info(self, "Berhasil", "Cache gambar cover art telah dibersihkan!")

    def _do_clear_temp(self):
        clear_temp_cache()
        stats = get_cache_size_info()
        self.lbl_temp_stat.config(text=f"File Sementara/Part  : {stats['temp_count']} file ({stats['temp_size']})")
        show_dark_info(self, "Berhasil", "Semua file sementara/temp telah dibersihkan!")

    def _do_clear_history(self):
        if ask_dark_yesno(self, "Konfirmasi", "Apakah Anda yakin ingin menghapus seluruh riwayat unduhan? (File MP3 di folder simpan tidak akan terhapus)."):
            clear_all_history()
            self.lbl_hist_stat.config(text="Riwayat Unduhan      : 0 karya tersimpan")
            self.parent._load_history_view()
            show_dark_info(self, "Berhasil", "Seluruh riwayat unduhan telah dikosongkan!")

    # ==================== TAB 4: ABOUT ====================
    def _render_about_tab(self):
        card_about = tk.Frame(self.content_container, bg="#1e1e2e")
        card_about.pack(fill="both", expand=True)

        # Header About
        top_row = tk.Frame(card_about, bg="#1e1e2e")
        top_row.pack(fill="x", pady=(0, 10))

        # Render Icon App jika ada
        if hasattr(self.parent, "_icon_png_path") and self.parent._icon_png_path and os.path.exists(self.parent._icon_png_path):
            try:
                with Image.open(self.parent._icon_png_path) as p_img:
                    resized = p_img.resize((64, 64), Image.Resampling.LANCZOS)
                    self._about_logo_img = ImageTk.PhotoImage(resized)
                    lbl_logo = tk.Label(top_row, image=self._about_logo_img, bg="#1e1e2e")
                    lbl_logo.pack(side="left", padx=(0, 14))
            except Exception:
                pass

        title_box = tk.Frame(top_row, bg="#1e1e2e")
        title_box.pack(side="left", fill="x")

        lbl_app_name = tk.Label(
            title_box,
            text="JapaneseASMR Downloader",
            font=("Segoe UI", 14, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
            anchor="w",
        )
        lbl_app_name.pack(fill="x")

        lbl_version = tk.Label(
            title_box,
            text="Versi 1.0.1 (Release Build) • Windows Edition",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#bd93f9",
            anchor="w",
        )
        lbl_version.pack(fill="x")

        lbl_desc = tk.Label(
            card_about,
            text="Aplikasi desktop all-in-one untuk mengunduh audio JapaneseASMR, menggabungkan multi-track & omake/EX secara otomatis, menyematkan cover art JPEG & metadata DLsite lengkap, serta dilengkapi pemutar audio bawaan.",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#cdd6f4",
            wraplength=480,
            justify="left",
            anchor="w",
        )
        lbl_desc.pack(fill="x", pady=(4, 12))

        # Developer & Tech Credits Card
        credit_card = tk.Frame(card_about, bg="#282a36", padx=14, pady=10)
        credit_card.pack(fill="x", pady=(0, 14))

        tk.Label(credit_card, text="Pengembang : SayMaven", font=("Segoe UI", 9, "bold"), bg="#282a36", fg="#f8f8f2", anchor="w").pack(fill="x", pady=1)
        tk.Label(credit_card, text="Teknologi   : Python 3.14, Tkinter, FFmpeg, yt-dlp, Aria2c, Nuitka C Engine", font=("Segoe UI", 8), bg="#282a36", fg="#a6adc8", anchor="w").pack(fill="x", pady=1)
        tk.Label(credit_card, text="Lisensi     : Open Source Software (Free for Personal Use)", font=("Segoe UI", 8), bg="#282a36", fg="#a6adc8", anchor="w").pack(fill="x", pady=1)

        # Action Link Buttons
        link_box = tk.Frame(card_about, bg="#1e1e2e")
        link_box.pack(fill="x")

        btn_gh = tk.Button(
            link_box,
            text="Buka Repository GitHub",
            font=("Segoe UI", 9, "bold"),
            bg="#6272a4",
            fg="#f8f8f2",
            activebackground="#bd93f9",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl"),
        )
        btn_gh.pack(side="left", padx=(0, 10))

        btn_issue = tk.Button(
            link_box,
            text="Laporkan Bug & Fitur",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#8be9fd",
            activebackground="#6272a4",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl/issues"),
        )
        btn_issue.pack(side="left")

    def _do_clear_covers(self):
        clear_cover_cache()
        stats = get_cache_size_info()
        self.lbl_cover_stat.config(text=f"🖼️ Cache Cover Art     : {stats['covers_count']} gambar ({stats['covers_size']})")
        show_dark_info(self, "Berhasil", "Cache gambar cover art telah dibersihkan!")

    def _do_clear_temp(self):
        clear_temp_cache()
        stats = get_cache_size_info()
        self.lbl_temp_stat.config(text=f"🧹 File Sementara/Part  : {stats['temp_count']} file ({stats['temp_size']})")
        show_dark_info(self, "Berhasil", "Semua file sementara/temp telah dibersihkan!")

    def _do_clear_history(self):
        if ask_dark_yesno(self, "Konfirmasi", "Apakah Anda yakin ingin menghapus seluruh riwayat unduhan? (File MP3 di folder simpan tidak akan terhapus)."):
            clear_all_history()
            self.lbl_hist_stat.config(text="📜 Riwayat Unduhan      : 0 karya tersimpan")
            self.parent._load_history_view()
            show_dark_info(self, "Berhasil", "Seluruh riwayat unduhan telah dikosongkan!")

    # ==================== TAB 4: ABOUT ====================
    def _render_about_tab(self):
        card_about = tk.Frame(self.content_container, bg="#1e1e2e")
        card_about.pack(fill="both", expand=True)

        # Header About
        top_row = tk.Frame(card_about, bg="#1e1e2e")
        top_row.pack(fill="x", pady=(0, 10))

        # Render Icon App jika ada
        if hasattr(self.parent, "_icon_png_path") and self.parent._icon_png_path and os.path.exists(self.parent._icon_png_path):
            try:
                with Image.open(self.parent._icon_png_path) as p_img:
                    resized = p_img.resize((64, 64), Image.Resampling.LANCZOS)
                    self._about_logo_img = ImageTk.PhotoImage(resized)
                    lbl_logo = tk.Label(top_row, image=self._about_logo_img, bg="#1e1e2e")
                    lbl_logo.pack(side="left", padx=(0, 14))
            except Exception:
                pass

        title_box = tk.Frame(top_row, bg="#1e1e2e")
        title_box.pack(side="left", fill="x")

        lbl_app_name = tk.Label(
            title_box,
            text="JapaneseASMR Downloader",
            font=("Segoe UI", 14, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
            anchor="w",
        )
        lbl_app_name.pack(fill="x")

        lbl_version = tk.Label(
            title_box,
            text="Versi 1.0.1 (Release Build) • Windows Edition",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#bd93f9",
            anchor="w",
        )
        lbl_version.pack(fill="x")

        lbl_desc = tk.Label(
            card_about,
            text="Aplikasi desktop all-in-one untuk mengunduh audio JapaneseASMR, menggabungkan multi-track & omake/EX secara otomatis, menyematkan cover art JPEG & metadata DLsite lengkap, serta dilengkapi pemutar audio bawaan.",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#cdd6f4",
            wraplength=480,
            justify="left",
            anchor="w",
        )
        lbl_desc.pack(fill="x", pady=(4, 12))

        # Developer & Tech Credits Card
        credit_card = tk.Frame(card_about, bg="#282a36", padx=14, pady=10)
        credit_card.pack(fill="x", pady=(0, 14))

        tk.Label(credit_card, text="👤 Pengembang : SayMaven", font=("Segoe UI", 9, "bold"), bg="#282a36", fg="#f8f8f2", anchor="w").pack(fill="x", pady=1)
        tk.Label(credit_card, text="⚙️ Teknologi   : Python 3.14, Tkinter, FFmpeg, yt-dlp, Aria2c, Nuitka C Engine", font=("Segoe UI", 8), bg="#282a36", fg="#a6adc8", anchor="w").pack(fill="x", pady=1)
        tk.Label(credit_card, text="📜 Lisensi     : Open Source Software (Free for Personal Use)", font=("Segoe UI", 8), bg="#282a36", fg="#a6adc8", anchor="w").pack(fill="x", pady=1)

        # Action Link Buttons
        link_box = tk.Frame(card_about, bg="#1e1e2e")
        link_box.pack(fill="x")

        btn_gh = tk.Button(
            link_box,
            text="🌐 Buka Repository GitHub",
            font=("Segoe UI", 9, "bold"),
            bg="#6272a4",
            fg="#f8f8f2",
            activebackground="#bd93f9",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl"),
        )
        btn_gh.pack(side="left", padx=(0, 10))

        btn_issue = tk.Button(
            link_box,
            text="🐛 Laporkan Bug / Fitur",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#8be9fd",
            activebackground="#6272a4",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl/issues"),
        )
        btn_issue.pack(side="left")

    # ==================== SIMPAN PENGATURAN ====================
    def _save_settings(self):
        new_dir = self.var_download_dir.get().strip()
        if not new_dir:
            show_dark_warning(self, "Peringatan", "Lokasi folder download tidak boleh kosong.")
            return

        self.cfg["download_dir"] = new_dir
        self.cfg["use_detailed_filename"] = self.var_detailed_name.get()
        self.cfg["notify_popup"] = self.var_notify_popup.get()
        self.cfg["auto_clipboard"] = self.var_auto_clipboard.get()
        self.cfg["connections"] = max(1, min(32, self.var_connections.get()))
        self.cfg["ytdlp_channel"] = self.var_ytdlp_channel.get()

        save_config(self.cfg)
        set_download_dir(new_dir)

        # Sinkronisasi ke GUI utama
        self.parent.opt_detailed_name.set(self.cfg["use_detailed_filename"])
        self.parent.lbl_current_dir.config(text=f"Lokasi Simpan: {os.path.abspath(new_dir)}")

        show_dark_info(self, "Tersimpan", "Semua pengaturan berhasil disimpan dan diterapkan!")
        self._on_dialog_close()

    def _on_dialog_close(self):
        if hasattr(self, "parent") and self.parent:
            self.parent._settings_dialog = None
        self.destroy()


def sanitize_filename(name):
    """Membersihkan karakter yang dilarang pada sistem file Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().rstrip(".")
    return clean if clean else "audio"


def fetch_dlsite_metadata(rj_id):
    """Mengambil metadata karya (Judul, CV, Circle, Genre, Rating) langsung dari DLsite resmi."""
    clean_id = rj_id.strip().upper()
    info = {
        "title": clean_id,
        "cv": "-",
        "circle": "-",
        "genre": "-",
        "age_rating": "-",
        "cover_url": f"https://pic.weeabo0.xyz/{clean_id}_img_main.jpg",
    }
    urls = [
        f"https://www.dlsite.com/maniax/work/=/product_id/{clean_id}.html",
        f"https://www.dlsite.com/home/work/=/product_id/{clean_id}.html",
        f"https://www.dlsite.com/girls/work/=/product_id/{clean_id}.html",
        f"https://www.dlsite.com/pro/work/=/product_id/{clean_id}.html",
    ]

    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Cookie": "adultchecked=1; locale=ja_JP",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                page_html = resp.read().decode("utf-8", errors="ignore")

            # 1. Ambil Judul
            title_match = re.search(r'<meta itemprop="name" content="(.*?)">', page_html)
            if not title_match:
                title_match = re.search(r'id=["\']work_name["\'][^>]*>(.*?)</h1>', page_html, re.DOTALL)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', page_html, re.DOTALL)
            if title_match:
                raw_title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
                raw_title = re.sub(r"\s*\[[^\]]+\]\s*\|\s*DLsite.*$", "", raw_title)
                raw_title = raw_title.replace(" | DLsite", "").replace(" - DLsite", "").strip()
                info["title"] = html.unescape(raw_title)

            # 2. Ambil Circle / Maker
            maker_match = re.search(r'<th>\s*(?:サークル名|ブランド名|メーカー名|著者)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if maker_match:
                makers = re.findall(r'<a[^>]*>(.*?)</a>', maker_match.group(1), re.DOTALL)
                clean_makers = [re.sub(r'<[^>]+>', '', m).strip() for m in makers if re.sub(r'<[^>]+>', '', m).strip()]
                if clean_makers:
                    info["circle"] = html.unescape(", ".join(clean_makers))

            if info["circle"] == "-":
                brand_match = re.search(r'<div itemprop="brand"[^>]*>.*?<meta itemprop="name" content="(.*?)">', page_html, re.DOTALL)
                if not brand_match:
                    brand_match = re.search(r'"position":\s*3,\s*"name":\s*"([^"]+)"', page_html)
                if not brand_match:
                    # Ambil dari tag <title> ... [Circle] | DLsite ...
                    t_match = re.search(r'\[(.*?)\]\s*\|\s*DLsite', page_html)
                    if t_match:
                        brand_match = t_match

                if brand_match:
                    raw_brand = html.unescape(brand_match.group(1).strip())
                    if "/" in raw_brand:
                        parts = raw_brand.split("/", 1)
                        info["circle"] = parts[0].strip()
                        if info["cv"] == "-":
                            info["cv"] = parts[1].strip()
                    else:
                        info["circle"] = raw_brand

            # 3. Ambil CV / Voice Actor dari Tabel
            cv_match = re.search(r'<th>\s*(?:声優|キャラクターボイス|ボイス|キャスト)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if cv_match:
                cvs = re.findall(r'<a[^>]*>(.*?)</a>', cv_match.group(1), re.DOTALL)
                clean_cvs = [re.sub(r'<[^>]+>', '', c).strip() for c in cvs if re.sub(r'<[^>]+>', '', c).strip()]
                if clean_cvs:
                    info["cv"] = html.unescape(", ".join(clean_cvs))
                else:
                    raw_cv_td = re.sub(r'<[^>]+>', '', cv_match.group(1)).strip()
                    if raw_cv_td:
                        info["cv"] = html.unescape(raw_cv_td)

            # 4. Fallback CV dari Judul / Deskripsi / Teks Halaman jika belum terisi
            if info["cv"] == "-":
                desc_match = re.search(r'<meta itemprop="description" content="(.*?)">', page_html, re.DOTALL)
                desc_text = html.unescape(desc_match.group(1)) if desc_match else ""
                combined_text = f"{info['title']} {desc_text}"

                cv_patterns = [
                    r'(?:CV|声優|キャラクターボイス|ボイス|キャスト|CV\.|CV：|CV:)\s*[：:\s【\[（(「『]*([^\n\r,、/】\]）)」』\s]{2,30})',
                    r'【(?:CV|声優|ボイス)\s*[：:\s]*([^\n\r,、/】\]）)\s]+)】',
                    r'\((?:CV|声優|ボイス)\s*[：:\s]*([^\n\r,、/】\]）)\s]+)\)',
                ]
                valid_cvs = []
                for pat in cv_patterns:
                    matches = re.findall(pat, combined_text, re.IGNORECASE)
                    for m in matches:
                        clean_m = m.strip()
                        if 1 < len(clean_m) < 30 and not clean_m.startswith("http") and clean_m not in valid_cvs:
                            valid_cvs.append(clean_m)
                if valid_cvs:
                    info["cv"] = ", ".join(valid_cvs)

            # 5. Ambil Genre / Tag dari Tabel atau Meta Keywords DLsite
            genre_match = re.search(r'<th>\s*(?:ジャンル|タグ)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if genre_match:
                g_links = re.findall(r'<a[^>]*>(.*?)</a>', genre_match.group(1), re.DOTALL)
                clean_genres = [re.sub(r'<[^>]+>', '', g).strip() for g in g_links if re.sub(r'<[^>]+>', '', g).strip()]
                if clean_genres:
                    info["genre"] = html.unescape(", ".join(clean_genres))
                else:
                    raw_g = re.sub(r'<[^>]+>', '', genre_match.group(1)).strip()
                    if raw_g:
                        info["genre"] = html.unescape(", ".join([x.strip() for x in raw_g.splitlines() if x.strip()]))

            # Fallback Genre dari meta keywords
            if info["genre"] == "-":
                kw_match = re.search(r'<meta name="keywords" content="(.*?)">', page_html)
                if kw_match:
                    raw_kws = [k.strip() for k in html.unescape(kw_match.group(1)).split(",") if k.strip()]
                    ignore_list = ["DLsite", "同人", "ダウンロード", "R18", "同人誌", "ゲーム", "音声", info.get("circle", "")]
                    filtered_kws = [k for k in raw_kws if k not in ignore_list and not k.startswith("RJ")]
                    if filtered_kws:
                        info["genre"] = ", ".join(filtered_kws[:12])

            # 6. Ambil Rating Usia (年齢指定)
            age_match = re.search(r'<th>\s*(?:年齢指定|レーティング)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if age_match:
                clean_age = re.sub(r'<[^>]+>', '', age_match.group(1)).strip()
                if clean_age:
                    info["age_rating"] = html.unescape(clean_age)
            elif "maniax" in url or "r18" in page_html.lower() or "18禁" in page_html:
                info["age_rating"] = "R18"
            else:
                info["age_rating"] = "全年齢"

            if info["title"] and info["title"] != clean_id:
                break
        except Exception:
            continue

    return info


class JapaneseASMRApp(tk.Tk):
    def __init__(self):
        # Set Explicit AppUserModelID agar Taskbar Windows menampilkan ikon custom
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SayMaven.JapaneseASMR.Downloader.App")
            except Exception:
                pass

        super().__init__()
        self.title("JapaneseASMR Downloader")
        self.geometry("1060x820")
        self.minsize(940, 720)
        self.configure(bg="#1e1e2e")
        apply_dark_titlebar(self)

        # Config & State
        self.config = load_config()
        self.is_downloading = False
        self.stop_requested = False
        self.current_process = None
        self.queue_items = []
        self.current_preview_image = None
        self.placeholder_text = "RJ01673437"
        self.opt_detailed_name = tk.BooleanVar(value=self.config.get("use_detailed_filename", False))

        # Audio Player State (Windows Native MCI Engine)
        self.current_playing_file = None
        self.current_playing_meta = {}
        self.is_playing = False
        self.is_paused = False
        self.player_duration_ms = 0
        self.is_user_dragging_slider = False
        self.is_looping = False
        self.playlist_items = []
        self.current_track_index = -1
        self.player_preview_image = None

        # Set Window & Taskbar Icon
        self._settings_dialog = None
        self._setup_app_icons()

        self._init_styles()
        self._build_ui()
        self._load_history_view()
        self._refresh_playlist_view()

        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        # Re-apply icon setelah window di-render sempurna oleh Windows DWM
        if sys.platform == "win32":
            self.after(150, self._apply_win32_taskbar_icon)

    def _setup_app_icons(self):
        candidate_roots = [
            os.path.dirname(os.path.abspath(__file__)),
            os.path.dirname(os.path.abspath(sys.executable)),
            os.getcwd(),
        ]
        if hasattr(sys, "_MEIPASS"):
            candidate_roots.insert(0, sys._MEIPASS)

        self._icon_ico_path = None
        self._icon_png_path = None
        for root in candidate_roots:
            p_ico = os.path.join(root, "assets", "icon.ico")
            p_png = os.path.join(root, "assets", "icon.png")
            if os.path.exists(p_ico) and not self._icon_ico_path:
                self._icon_ico_path = p_ico
            if os.path.exists(p_png) and not self._icon_png_path:
                self._icon_png_path = p_png

        # 1. Pasang via Tkinter standard
        if self._icon_ico_path and os.path.exists(self._icon_ico_path):
            try:
                self.iconbitmap(default=self._icon_ico_path)
            except Exception:
                try:
                    self.iconbitmap(self._icon_ico_path)
                except Exception:
                    pass

        if self._icon_png_path and os.path.exists(self._icon_png_path):
            try:
                with Image.open(self._icon_png_path) as pil_img:
                    self._app_icon_img = ImageTk.PhotoImage(pil_img)
                    self.iconphoto(True, self._app_icon_img)
            except Exception:
                pass

        self._apply_win32_taskbar_icon()

    def _apply_win32_taskbar_icon(self):
        """Memaksa Windows Taskbar & Alt-Tab menggunakan icon custom via Win32 SendMessage WM_SETICON."""
        if sys.platform != "win32" or not self._icon_ico_path or not os.path.exists(self._icon_ico_path):
            return
        try:
            self.update_idletasks()
            GA_ROOT = 2
            hwnd = ctypes.windll.user32.GetAncestor(self.winfo_id(), GA_ROOT)
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()

            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1

            # Load icon 48x48 / 32x32 untuk taskbar & 16x16 untuk titlebar
            hicon_big = ctypes.windll.user32.LoadImageW(
                None, self._icon_ico_path, IMAGE_ICON, 48, 48, LR_LOADFROMFILE
            )
            if not hicon_big:
                hicon_big = ctypes.windll.user32.LoadImageW(
                    None, self._icon_ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE
                )
            hicon_small = ctypes.windll.user32.LoadImageW(
                None, self._icon_ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
            )

            if hicon_big:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
            if hicon_small:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
        except Exception:
            pass

    def _init_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Notebook Tabs Styling
        self.style.configure(
            "TNotebook",
            background="#1e1e2e",
            borderwidth=0,
        )
        self.style.configure(
            "TNotebook.Tab",
            background="#282a36",
            foreground="#f8f8f2",
            font=("Segoe UI", 10, "bold"),
            padding=[16, 6],
            borderwidth=0,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#bd93f9")],
            foreground=[("selected", "#1e1e2e")],
        )

        # Treeview Styling
        self.style.configure(
            "Treeview",
            background="#282a36",
            foreground="#f8f8f2",
            fieldbackground="#282a36",
            rowheight=28,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            background="#44475a",
            foreground="#f8f8f2",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#bd93f9")],
            foreground=[("selected", "#1e1e2e")],
        )

        # Progressbar Styling
        self.style.configure(
            "Neon.Horizontal.TProgressbar",
            troughcolor="#181825",
            background="#50fa7b",
            darkcolor="#50fa7b",
            lightcolor="#50fa7b",
            bordercolor="#282a36",
            thickness=12,
        )

    def _build_ui(self):
        # Header Banner
        header_frame = tk.Frame(self, bg="#282a36", height=65)
        header_frame.pack(fill="x", side="top")

        title_label = tk.Label(
            header_frame,
            text="JapaneseASMR Downloader",
            font=("Segoe UI", 15, "bold"),
            bg="#282a36",
            fg="#50fa7b",
        )
        title_label.pack(side="left", padx=20, pady=12)

        # Directory Selector, Open Folder, & Settings Buttons
        dir_controls = tk.Frame(header_frame, bg="#282a36")
        dir_controls.pack(side="right", padx=20, pady=10)

        change_dir_btn = tk.Button(
            dir_controls,
            text="Ganti Folder",
            font=("Segoe UI", 9, "bold"),
            bg="#bd93f9",
            fg="#1e1e2e",
            activebackground="#ff79c6",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._change_download_dir,
        )
        change_dir_btn.pack(side="left", padx=(0, 8))

        open_folder_btn = tk.Button(
            dir_controls,
            text="Buka Folder",
            font=("Segoe UI", 9, "bold"),
            bg="#44475a",
            fg="#8be9fd",
            activebackground="#6272a4",
            activeforeground="#ffffff",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._open_downloads_folder,
        )
        open_folder_btn.pack(side="left", padx=(0, 8))

        settings_btn = tk.Button(
            dir_controls,
            text="Pengaturan",
            font=("Segoe UI", 9, "bold"),
            bg="#6272a4",
            fg="#f8f8f2",
            activebackground="#bd93f9",
            activeforeground="#1e1e2e",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._open_settings_dialog,
        )
        settings_btn.pack(side="left")

        # Bar status folder simpan
        dir_bar = tk.Frame(self, bg="#181825", height=26)
        dir_bar.pack(fill="x", side="top")
        self.lbl_current_dir = tk.Label(
            dir_bar,
            text=f"Lokasi Simpan: {os.path.abspath(get_download_dir())}",
            font=("Segoe UI", 8),
            bg="#181825",
            fg="#a6adc8",
            anchor="w",
        )
        self.lbl_current_dir.pack(fill="x", padx=15, pady=2)

        # Notebook (3 Tab: Antrean, Riwayat, Pemutar Audio)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        # Tab 1: Download & Antrean
        self.tab_queue = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(self.tab_queue, text=" Antrean Download ")

        # Tab 2: Riwayat Unduhan
        self.tab_history = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(self.tab_history, text=" Riwayat Unduhan ")

        # Tab 3: Pemutar Audio Bawaan
        self.tab_player = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(self.tab_player, text=" Pemutar Audio ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_queue_tab()
        self._build_history_tab()
        self._build_player_tab()

    def _on_tab_changed(self, event):
        selected_tab = self.notebook.select()
        if selected_tab == str(self.tab_history):
            self._load_history_view()
        elif selected_tab == str(self.tab_player):
            self._refresh_playlist_view()

    def _build_queue_tab(self):
        container = self.tab_queue

        # Layout 2 Kolom: Kiri (Input & Tabel), Kanan (Cover & Info Detail)
        main_container = tk.Frame(container, bg="#1e1e2e")
        main_container.pack(fill="both", expand=True)

        left_panel = tk.Frame(main_container, bg="#1e1e2e")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # 1. Baris Input & Tombol Tambah
        input_frame = tk.LabelFrame(
            left_panel,
            text=" Input Kode RJ / URL ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        input_frame.pack(fill="x", pady=(0, 10), ipady=5)

        input_inner = tk.Frame(input_frame, bg="#1e1e2e")
        input_inner.pack(fill="x", padx=10, pady=(6, 4))

        self.id_entry = tk.Entry(
            input_inner,
            font=("Consolas", 11),
            bg="#282a36",
            fg="#6272a4",
            insertbackground="#50fa7b",
            bd=1,
            relief="solid",
        )
        self.id_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)
        self.id_entry.insert(0, self.placeholder_text)

        def _on_entry_focus_in(event):
            if self.id_entry.get() == self.placeholder_text:
                self.id_entry.delete(0, "end")
                self.id_entry.config(fg="#50fa7b")

        def _on_entry_focus_out(event):
            if not self.id_entry.get().strip():
                self.id_entry.insert(0, self.placeholder_text)
                self.id_entry.config(fg="#6272a4")

        self.id_entry.bind("<FocusIn>", _on_entry_focus_in)
        self.id_entry.bind("<FocusOut>", _on_entry_focus_out)
        self.id_entry.bind("<Return>", lambda e: self._add_to_queue())

        paste_btn = tk.Button(
            input_inner,
            text="Tempel",
            font=("Segoe UI", 9, "bold"),
            bg="#44475a",
            fg="#8be9fd",
            activebackground="#6272a4",
            activeforeground="#ffffff",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._paste_from_clipboard,
        )
        paste_btn.pack(side="left", padx=(0, 8))

        add_btn = tk.Button(
            input_inner,
            text="Tambah ke Antrean",
            font=("Segoe UI", 9, "bold"),
            bg="#bd93f9",
            fg="#1e1e2e",
            activebackground="#ff79c6",
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._add_to_queue,
        )
        add_btn.pack(side="right")

        # Opsi Checkbox Nama File (Diletakkan rapi di bawah baris input)
        opts_frame = tk.Frame(input_frame, bg="#1e1e2e")
        opts_frame.pack(fill="x", padx=10, pady=(2, 4))

        chk_name = tk.Checkbutton(
            opts_frame,
            text="Gunakan Judul Asli Karya sebagai Nama File MP3",
            variable=self.opt_detailed_name,
            command=self._save_options,
            bg="#1e1e2e",
            fg="#f8f8f2",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#50fa7b",
            font=("Segoe UI", 9),
            bd=0,
        )
        chk_name.pack(side="left")

        # 2. Tabel Antrean
        queue_frame = tk.LabelFrame(
            left_panel,
            text=" Daftar Antrean Download ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        queue_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("no", "rjid", "title", "status")
        self.tree = ttk.Treeview(queue_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("no", text="#", anchor="center")
        self.tree.heading("rjid", text="Kode RJ", anchor="center")
        self.tree.heading("title", text="Judul / Keterangan", anchor="w")
        self.tree.heading("status", text="Status", anchor="center")

        self.tree.column("no", width=35, anchor="center")
        self.tree.column("rjid", width=110, anchor="center")
        self.tree.column("title", width=260, anchor="w")
        self.tree.column("status", width=110, anchor="center")

        tree_scroll = ttk.Scrollbar(queue_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        tree_scroll.pack(side="right", fill="y", pady=5, padx=(0, 5))
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Action Buttons
        btn_action_frame = tk.Frame(left_panel, bg="#1e1e2e")
        btn_action_frame.pack(fill="x", pady=(0, 10))

        self.start_btn = tk.Button(
            btn_action_frame,
            text="Mulai Download",
            font=("Segoe UI", 10, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            activebackground="#8be9fd",
            bd=0,
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._start_download_thread,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_action_frame,
            text="Berhenti",
            font=("Segoe UI", 10, "bold"),
            bg="#ff5555",
            fg="#ffffff",
            activebackground="#ff6e6e",
            bd=0,
            padx=16,
            pady=6,
            state="disabled",
            cursor="hand2",
            command=self._stop_downloads,
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        clear_btn = tk.Button(
            btn_action_frame,
            text="Bersihkan Antrean",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            activebackground="#6272a4",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._clear_queue,
        )
        clear_btn.pack(side="right")

        # Progress Bar Container (Di antara Tombol Aksi dan Log Konsol)
        progress_container = tk.Frame(left_panel, bg="#1e1e2e")
        progress_container.pack(fill="x", pady=(0, 10))

        progress_header = tk.Frame(progress_container, bg="#1e1e2e")
        progress_header.pack(fill="x", pady=(0, 4))

        self.lbl_progress_status = tk.Label(
            progress_header,
            text="Status: Siap",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#a6adc8",
        )
        self.lbl_progress_status.pack(side="left")

        self.lbl_progress_pct = tk.Label(
            progress_header,
            text="0%",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
        )
        self.lbl_progress_pct.pack(side="right")

        self.progress_bar = ttk.Progressbar(
            progress_container,
            orient="horizontal",
            mode="determinate",
            style="Neon.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar["value"] = 0

        # Progress Detail Bar: Kecepatan, Estimasi Sisa Waktu, dan Ukuran Data
        progress_detail = tk.Frame(progress_container, bg="#1e1e2e")
        progress_detail.pack(fill="x", pady=(4, 0))

        self.lbl_progress_speed = tk.Label(
            progress_detail,
            text="Kecepatan: -",
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#8be9fd",
        )
        self.lbl_progress_speed.pack(side="left")

        self.lbl_progress_eta = tk.Label(
            progress_detail,
            text="Sisa Waktu: -",
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#bd93f9",
        )
        self.lbl_progress_eta.pack(side="left", padx=(16, 0))

        self.lbl_progress_size = tk.Label(
            progress_detail,
            text="Ukuran: - / -",
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#a6adc8",
        )
        self.lbl_progress_size.pack(side="right")

        # Log Console
        log_frame = tk.LabelFrame(
            left_panel,
            text=" Status & Log Konsol ",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        log_frame.pack(fill="x", pady=(0, 5))

        self.log_text = tk.Text(
            log_frame,
            height=5,
            bg="#181825",
            fg="#a6adc8",
            font=("Consolas", 9),
            bd=0,
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Panel Kanan: Preview Thumbnail & Info Card
        right_panel = tk.LabelFrame(
            main_container,
            text=" Informasi Karya & Preview ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=330,
        )
        right_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        right_panel.pack_propagate(False)

        # Canvas Cover
        self.cover_canvas = tk.Canvas(
            right_panel,
            bg="#282a36",
            width=290,
            height=195,
            bd=0,
            highlightthickness=1,
            highlightbackground="#44475a",
        )
        self.cover_canvas.pack(pady=8, padx=10)
        self.cover_canvas.create_text(
            145, 97, text="Tidak ada cover", fill="#6272a4", font=("Segoe UI", 10)
        )

        # Info Labels
        info_inner = tk.Frame(right_panel, bg="#1e1e2e")
        info_inner.pack(fill="both", expand=True, padx=12, pady=3)

        self.lbl_q_id = self._create_info_row(info_inner, "Kode RJ", "-")
        self.lbl_q_title = self._create_info_row(info_inner, "Judul", "-")
        self.lbl_q_cv = self._create_info_row(info_inner, "CV / Seiyuu", "-")
        self.lbl_q_circle = self._create_info_row(info_inner, "Circle / Maker", "-")
        self.lbl_q_rating = self._create_info_row(info_inner, "Rating Usia", "-")
        self.lbl_q_genre = self._create_info_row(info_inner, "Genre / Tag", "-")

    def _build_history_tab(self):
        container = self.tab_history

        # Layout 2 Kolom: Kiri (Tabel Riwayat), Kanan (Detail & Cover)
        left_h_panel = tk.Frame(container, bg="#1e1e2e")
        left_h_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # Header Riwayat & Tombol Refresh
        h_header = tk.Frame(left_h_panel, bg="#1e1e2e")
        h_header.pack(fill="x", pady=(0, 6))

        lbl_h_header = tk.Label(
            h_header,
            text="Riwayat Karya Terunduh",
            font=("Segoe UI", 11, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
        )
        lbl_h_header.pack(side="left")

        refresh_btn = tk.Button(
            h_header,
            text="Segarkan",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            bd=0,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._load_history_view,
        )
        refresh_btn.pack(side="right")

        # Banner Statistik Penyimpanan
        stats_frame = tk.Frame(left_h_panel, bg="#282a36", bd=1, relief="solid")
        stats_frame.pack(fill="x", pady=(0, 8))

        self.lbl_hist_stats = tk.Label(
            stats_frame,
            text="Memuat statistik koleksi...",
            font=("Segoe UI", 9, "bold"),
            bg="#282a36",
            fg="#8be9fd",
            padx=10,
            pady=5,
            anchor="w",
        )
        self.lbl_hist_stats.pack(fill="x")

        # Tabel Riwayat Treeview
        cols = ("date", "rjid", "title", "size")
        self.hist_tree = ttk.Treeview(left_h_panel, columns=cols, show="headings", selectmode="browse")
        self.hist_tree.heading("date", text="Tanggal Unduh", anchor="center")
        self.hist_tree.heading("rjid", text="Kode RJ", anchor="center")
        self.hist_tree.heading("title", text="Judul Karya", anchor="w")
        self.hist_tree.heading("size", text="Ukuran", anchor="center")

        self.hist_tree.column("date", width=140, anchor="center")
        self.hist_tree.column("rjid", width=110, anchor="center")
        self.hist_tree.column("title", width=280, anchor="w")
        self.hist_tree.column("size", width=80, anchor="center")

        h_scroll = ttk.Scrollbar(left_h_panel, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=h_scroll.set)

        self.hist_tree.pack(side="left", fill="both", expand=True)
        h_scroll.pack(side="right", fill="y")
        self.hist_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        # Panel Kanan Riwayat (Detail & Cover)
        right_h_panel = tk.LabelFrame(
            container,
            text=" Detail Riwayat Koleksi ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=330,
        )
        right_h_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        right_h_panel.pack_propagate(False)

        # Tombol Buka File di Riwayat
        h_actions = tk.Frame(right_h_panel, bg="#1e1e2e")
        h_actions.pack(fill="x", padx=12, pady=10, side="bottom")

        self.btn_play_file = tk.Button(
            h_actions,
            text="Putar di Player Bawaan",
            font=("Segoe UI", 9, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            bd=0,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self._play_history_in_player,
        )
        self.btn_play_file.pack(fill="x", pady=(0, 6))

        self.btn_del_history = tk.Button(
            h_actions,
            text="Hapus Riwayat",
            font=("Segoe UI", 8),
            bg="#44475a",
            fg="#ff5555",
            activebackground="#6272a4",
            activeforeground="#ff5555",
            bd=0,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=lambda: self._delete_history_item(),
        )
        self.btn_del_history.pack(fill="x")

        # Canvas Cover
        self.hist_canvas = tk.Canvas(
            right_h_panel,
            bg="#282a36",
            width=290,
            height=195,
            bd=0,
            highlightthickness=1,
            highlightbackground="#44475a",
        )
        self.hist_canvas.pack(pady=8, padx=10)
        self.hist_canvas.create_text(145, 97, text="Pilih item riwayat", fill="#6272a4", font=("Segoe UI", 10))

        h_info_inner = tk.Frame(right_h_panel, bg="#1e1e2e")
        h_info_inner.pack(fill="both", expand=True, padx=12, pady=3)

        self.lbl_h_id = self._create_info_row(h_info_inner, "Kode RJ", "-")
        self.lbl_h_title = self._create_info_row(h_info_inner, "Judul", "-")
        self.lbl_h_cv = self._create_info_row(h_info_inner, "CV / Seiyuu", "-")
        self.lbl_h_circle = self._create_info_row(h_info_inner, "Circle / Maker", "-")
        self.lbl_h_rating = self._create_info_row(h_info_inner, "Rating Usia", "-")
        self.lbl_h_genre = self._create_info_row(h_info_inner, "Genre / Tag", "-")
        self.lbl_h_path = self._create_info_row(h_info_inner, "Status File", "-")

    def _build_player_tab(self):
        container = self.tab_player

        # 1. Panel Kiri: Playlist & Koleksi
        left_p_panel = tk.Frame(container, bg="#1e1e2e")
        left_p_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        p_header = tk.Frame(left_p_panel, bg="#1e1e2e")
        p_header.pack(fill="x", pady=(0, 6))

        lbl_p_title = tk.Label(
            p_header,
            text="Daftar Putar / Koleksi Audio",
            font=("Segoe UI", 11, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
        )
        lbl_p_title.pack(side="left")

        refresh_p_btn = tk.Button(
            p_header,
            text="Segarkan",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            bd=0,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._refresh_playlist_view,
        )
        refresh_p_btn.pack(side="right")

        # Treeview Playlist
        cols = ("rjid", "title", "cv", "size")
        self.player_tree = ttk.Treeview(left_p_panel, columns=cols, show="headings", selectmode="browse")
        self.player_tree.heading("rjid", text="Kode RJ", anchor="center")
        self.player_tree.heading("title", text="Judul Karya", anchor="w")
        self.player_tree.heading("cv", text="CV / Seiyuu", anchor="w")
        self.player_tree.heading("size", text="Ukuran", anchor="center")

        self.player_tree.column("rjid", width=95, anchor="center")
        self.player_tree.column("title", width=220, anchor="w")
        self.player_tree.column("cv", width=120, anchor="w")
        self.player_tree.column("size", width=70, anchor="center")

        p_scroll = ttk.Scrollbar(left_p_panel, orient="vertical", command=self.player_tree.yview)
        self.player_tree.configure(yscrollcommand=p_scroll.set)

        self.player_tree.pack(side="left", fill="both", expand=True)
        p_scroll.pack(side="right", fill="y")
        self.player_tree.bind("<Double-1>", lambda e: self._player_play_selected())
        self.player_tree.bind("<<TreeviewSelect>>", self._on_playlist_select)

        # 2. Panel Kanan: Now Playing Screen & Controls
        right_p_panel = tk.LabelFrame(
            container,
            text=" Sedang Diputar (Now Playing) ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=360,
        )
        right_p_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        right_p_panel.pack_propagate(False)

        # Cover Canvas
        self.player_canvas = tk.Canvas(
            right_p_panel,
            bg="#282a36",
            width=290,
            height=195,
            bd=0,
            highlightthickness=1,
            highlightbackground="#bd93f9",
        )
        self.player_canvas.pack(pady=(10, 8), padx=12)
        self.player_canvas.create_text(
            145, 97, text="Pilih audio dari playlist untuk memutar", fill="#6272a4", font=("Segoe UI", 9), justify="center"
        )

        # Meta Info
        self.lbl_p_now_title = tk.Label(
            right_p_panel,
            text="Belum Ada Audio Diputar",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
            wraplength=320,
            justify="center",
        )
        self.lbl_p_now_title.pack(fill="x", padx=10, pady=(0, 2))

        self.lbl_p_now_sub = tk.Label(
            right_p_panel,
            text="CV: - | Circle: -",
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#a6adc8",
            wraplength=320,
            justify="center",
        )
        self.lbl_p_now_sub.pack(fill="x", padx=10, pady=(0, 8))

        # Timeline Slider & Duration Labels
        timeline_frame = tk.Frame(right_p_panel, bg="#1e1e2e")
        timeline_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.lbl_time_cur = tk.Label(timeline_frame, text="00:00", font=("Consolas", 9), bg="#1e1e2e", fg="#50fa7b")
        self.lbl_time_cur.pack(side="left")

        self.lbl_time_total = tk.Label(timeline_frame, text="00:00", font=("Consolas", 9), bg="#1e1e2e", fg="#a6adc8")
        self.lbl_time_total.pack(side="right")

        self.timeline_slider = ttk.Scale(
            right_p_panel,
            from_=0,
            to=100,
            orient="horizontal",
            command=self._on_slider_change,
        )
        self.timeline_slider.pack(fill="x", padx=12, pady=(0, 8))
        self.timeline_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "is_user_dragging_slider", True))
        self.timeline_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # Control Buttons Row
        ctrl_frame = tk.Frame(right_p_panel, bg="#1e1e2e")
        ctrl_frame.pack(pady=(0, 8))

        btn_prev = tk.Button(
            ctrl_frame,
            text="⏮",
            font=("Segoe UI", 11, "bold"),
            bg="#44475a",
            fg="#f8f8f2",
            activebackground="#6272a4",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._player_prev_track,
        )
        btn_prev.pack(side="left", padx=3)

        self.btn_play_pause = tk.Button(
            ctrl_frame,
            text="▶ Putar",
            font=("Segoe UI", 10, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            activebackground="#8be9fd",
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._player_play_pause_toggle,
        )
        self.btn_play_pause.pack(side="left", padx=3)

        btn_stop = tk.Button(
            ctrl_frame,
            text="■",
            font=("Segoe UI", 11, "bold"),
            bg="#44475a",
            fg="#f8f8f2",
            activebackground="#ff5555",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._player_stop,
        )
        btn_stop.pack(side="left", padx=3)

        btn_next = tk.Button(
            ctrl_frame,
            text="⏭",
            font=("Segoe UI", 11, "bold"),
            bg="#44475a",
            fg="#f8f8f2",
            activebackground="#6272a4",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._player_next_track,
        )
        btn_next.pack(side="left", padx=3)

        self.btn_loop = tk.Button(
            ctrl_frame,
            text="Loop: OFF",
            font=("Segoe UI", 8),
            bg="#44475a",
            fg="#a6adc8",
            activebackground="#6272a4",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._player_toggle_loop,
        )
        self.btn_loop.pack(side="left", padx=3)

        # Volume Slider
        vol_frame = tk.Frame(right_p_panel, bg="#1e1e2e")
        vol_frame.pack(fill="x", padx=15, pady=(2, 0))

        lbl_vol_icon = tk.Label(vol_frame, text="Volume:", font=("Segoe UI", 8, "bold"), bg="#1e1e2e", fg="#bd93f9")
        lbl_vol_icon.pack(side="left", padx=(0, 6))

        self.lbl_vol_val = tk.Label(vol_frame, text="80%", font=("Segoe UI", 8), bg="#1e1e2e", fg="#a6adc8", width=4)
        self.lbl_vol_val.pack(side="right")

        self.vol_slider = ttk.Scale(
            vol_frame,
            from_=0,
            to=100,
            orient="horizontal",
            command=self._player_set_volume,
        )
        self.vol_slider.set(80)
        self.vol_slider.pack(side="left", fill="x", expand=True)

    def _create_info_row(self, parent, label_text, default_value):
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(fill="x", pady=2)

        lbl = tk.Label(
            frame,
            text=f"{label_text}:",
            font=("Segoe UI", 8, "bold"),
            bg="#1e1e2e",
            fg="#bd93f9",
            anchor="w",
        )
        lbl.pack(fill="x")

        val_lbl = tk.Label(
            frame,
            text=default_value,
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#f8f8f2",
            anchor="w",
            wraplength=290,
            justify="left",
        )
        val_lbl.pack(fill="x")
        return val_lbl

    def _save_options(self):
        self.config["use_detailed_filename"] = self.opt_detailed_name.get()
        save_config(self.config)

    def _change_download_dir(self):
        new_dir = filedialog.askdirectory(
            title="Pilih Folder Penyimpanan Download",
            initialdir=os.path.abspath(get_download_dir()),
        )
        if new_dir:
            set_download_dir(new_dir)
            self.lbl_current_dir.config(text=f"📁 Lokasi Simpan: {os.path.abspath(new_dir)}")
            self._log(f"[i] Folder penyimpanan diubah ke: {new_dir}")

    def _log(self, message):
        def append():
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
        self.after(0, append)

    def _open_downloads_folder(self):
        d_dir = get_download_dir()
        os.makedirs(d_dir, exist_ok=True)
        os.startfile(os.path.abspath(d_dir))

    def _open_settings_dialog(self):
        """Membuka jendela dialog Pengaturan Modern tanpa memblokir penutupan aplikasi utama."""
        if self._settings_dialog and self._settings_dialog.winfo_exists():
            self._settings_dialog.lift()
            self._settings_dialog.focus_force()
            return
        self._settings_dialog = SettingsDialog(self)

    def _on_app_close(self):
        """Menutup seluruh aplikasi, modal anak, dan mematikan background player secara bersih."""
        if self._settings_dialog and self._settings_dialog.winfo_exists():
            try:
                self._settings_dialog.destroy()
            except Exception:
                pass
        self._player_stop()
        self.destroy()

    def _add_to_queue(self):
        raw_text = self.id_entry.get().strip()
        if not raw_text or raw_text == self.placeholder_text:
            raw_text = self.placeholder_text

        tokens = re.split(r"[\s,;]+", raw_text)
        new_ids = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            m = re.search(r"(RJ\d+|\d{6,8})", token, re.IGNORECASE)
            if m:
                rjid = m.group(1).upper()
                if not rjid.startswith("RJ"):
                    rjid = f"RJ{rjid}"
                new_ids.append(rjid)
            else:
                new_ids.append(token.upper())

        for rjid in new_ids:
            item_data = {
                "rjid": rjid,
                "title": "Memuat info...",
                "cv": "-",
                "circle": "-",
                "genre": "-",
                "age_rating": "-",
                "status": "Pending",
                "cover_url": f"https://pic.weeabo0.xyz/{rjid}_img_main.jpg",
                "cover_image": None,
            }
            self.queue_items.append(item_data)
            row_id = len(self.queue_items)
            self.tree.insert("", "end", iid=str(row_id - 1), values=(row_id, rjid, "Mengambil info...", "Pending"))

            # Fetch metadata di background
            threading.Thread(target=self._fetch_metadata_for_item, args=(row_id - 1, rjid), daemon=True).start()

        self.id_entry.delete(0, "end")
        self.id_entry.insert(0, self.placeholder_text)
        self.id_entry.config(fg="#6272a4")
        self._log(f"[+] Menambahkan {len(new_ids)} item ke antrean.")

    def _fetch_metadata_for_item(self, index, rj_id):
        meta = fetch_dlsite_metadata(rj_id)
        if index < len(self.queue_items):
            self.queue_items[index]["title"] = meta["title"] if meta["title"] else rj_id
            self.queue_items[index]["cv"] = meta["cv"] if meta["cv"] else "-"
            self.queue_items[index]["circle"] = meta["circle"] if meta["circle"] else "-"
            self.queue_items[index]["genre"] = meta.get("genre", "-")
            self.queue_items[index]["age_rating"] = meta.get("age_rating", "-")

            def update_ui():
                if self.tree.exists(str(index)):
                    self.tree.set(str(index), "title", self.queue_items[index]["title"])
                selected = self.tree.selection()
                if selected and selected[0] == str(index):
                    self._show_info_card(self.queue_items[index])

            self.after(0, update_ui)

            # Cek cache lokal terlebih dahulu
            cache_file = os.path.join(".cache", "covers", f"{rj_id}.jpg")
            if os.path.exists(cache_file):
                try:
                    pil_img = Image.open(cache_file)
                    pil_img.thumbnail((280, 195))
                    self.queue_items[index]["cover_image"] = pil_img
                    def update_img():
                        selected = self.tree.selection()
                        if selected and selected[0] == str(index):
                            self._render_cover_image(pil_img)
                    self.after(0, update_img)
                    return
                except Exception:
                    pass

            # Download cover thumbnail preview jika belum di-cache
            try:
                req = urllib.request.Request(meta["cover_url"], headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    img_data = resp.read()
                pil_img = Image.open(io.BytesIO(img_data))
                pil_img.thumbnail((280, 195))
                self.queue_items[index]["cover_image"] = pil_img

                def update_img():
                    selected = self.tree.selection()
                    if selected and selected[0] == str(index):
                        self._render_cover_image(pil_img)

                self.after(0, update_img)
            except Exception:
                pass

    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < len(self.queue_items):
            item = self.queue_items[idx]
            self._show_info_card(item)
            if item.get("cover_image"):
                self._render_cover_image(item["cover_image"])
            else:
                self.cover_canvas.delete("all")
                self.cover_canvas.create_text(145, 97, text="Memuat cover...", fill="#6272a4", font=("Segoe UI", 10))

    def _show_info_card(self, item):
        self.lbl_q_id.config(text=item["rjid"])
        self.lbl_q_title.config(text=item["title"])
        self.lbl_q_cv.config(text=item["cv"])
        self.lbl_q_circle.config(text=item["circle"])
        
        rating = item.get("age_rating", "-")
        self.lbl_q_rating.config(text=rating, fg="#ff79c6" if "18" in rating else "#50fa7b")
        self.lbl_q_genre.config(text=item.get("genre", "-"))

    def _render_cover_image(self, pil_image):
        self.current_preview_image = ImageTk.PhotoImage(pil_image)
        self.cover_canvas.delete("all")
        self.cover_canvas.create_image(145, 97, image=self.current_preview_image)

    def _clear_queue(self):
        if self.is_downloading:
            show_dark_warning(self, "Peringatan", "Tidak dapat membersihkan antrean saat download sedang berlangsung.")
            return
        self.tree.delete(*self.tree.get_children())
        self.queue_items.clear()
        self.cover_canvas.delete("all")
        self.cover_canvas.create_text(145, 97, text="Tidak ada cover", fill="#6272a4", font=("Segoe UI", 10))
        self.lbl_q_id.config(text="-")
        self.lbl_q_title.config(text="-")
        self.lbl_q_cv.config(text="-")
        self.lbl_q_circle.config(text="-")
        self.lbl_q_rating.config(text="-", fg="#f8f8f2")
        self.lbl_q_genre.config(text="-")
        self._update_progress(0, "Antrean dibersihkan")
        self._log("[i] Antrean dibersihkan.")

    def _log(self, text):
        def _append():
            self.log_text.insert("end", text + "\n")
            self.log_text.see("end")
        self.after(0, _append)

    def _update_progress(self, val_pct, status_text=None, speed=None, eta=None, size_str=None):
        def _apply():
            clamped = max(0, min(100, val_pct))
            self.progress_bar["value"] = clamped
            self.lbl_progress_pct.config(text=f"{int(clamped)}%")
            if status_text:
                self.lbl_progress_status.config(text=f"Status: {status_text}")
            if speed is not None and hasattr(self, "lbl_progress_speed"):
                self.lbl_progress_speed.config(text=speed)
            if eta is not None and hasattr(self, "lbl_progress_eta"):
                self.lbl_progress_eta.config(text=eta)
            if size_str is not None and hasattr(self, "lbl_progress_size"):
                self.lbl_progress_size.config(text=size_str)
        self.after(0, _apply)

    def _paste_from_clipboard(self):
        try:
            clip_text = self.clipboard_get().strip()
            if clip_text:
                self.id_entry.delete(0, "end")
                self.id_entry.insert(0, clip_text)
                self.id_entry.config(fg="#50fa7b")
                self._log(f"[i] Berhasil menempel dari clipboard: {clip_text[:40]}...")
        except Exception as e:
            self._log(f"[!] Gagal membaca clipboard: {e}")

    def _load_history_view(self):
        """Memuat ulang tabel riwayat dari history.json dan menghitung statistik koleksi."""
        self.hist_tree.delete(*self.hist_tree.get_children())
        histories = load_history()
        total_size_bytes = 0
        available_count = 0

        for idx, h in enumerate(histories):
            fpath = h.get("output_path", "")
            if os.path.exists(fpath):
                try:
                    fsize = os.path.getsize(fpath)
                    total_size_bytes += fsize
                    available_count += 1
                except OSError:
                    pass

            self.hist_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    h.get("download_date", "-"),
                    h.get("rjid", "-"),
                    h.get("title", "-"),
                    h.get("file_size", "-"),
                ),
            )

        # Update Banner Statistik
        if total_size_bytes >= 1024 * 1024 * 1024:
            size_str = f"{total_size_bytes / (1024 * 1024 * 1024):.2f} GB"
        else:
            size_str = f"{total_size_bytes / (1024 * 1024):.1f} MB"

        stats_text = (
            f"📊 Total Koleksi: {len(histories)} Karya   |   "
            f"💾 Total Penyimpanan: {size_str}   |   "
            f"✅ File Tersedia di Disk: {available_count}/{len(histories)}"
        )
        if hasattr(self, "lbl_hist_stats"):
            self.lbl_hist_stats.config(text=stats_text)

    def _on_history_select(self, event):
        selected = self.hist_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        histories = load_history()
        if idx < len(histories):
            h = histories[idx]
            self.lbl_h_id.config(text=h.get("rjid", "-"))
            self.lbl_h_title.config(text=h.get("title", "-"))
            self.lbl_h_cv.config(text=h.get("cv", "-"))
            self.lbl_h_circle.config(text=h.get("circle", "-"))
            
            rating = h.get("age_rating", "-")
            self.lbl_h_rating.config(text=rating, fg="#ff79c6" if "18" in rating else "#50fa7b")
            self.lbl_h_genre.config(text=h.get("genre", "-"))

            file_path = h.get("output_path", "")
            self.btn_del_history.config(state="normal")
            if os.path.exists(file_path):
                self.lbl_h_path.config(text="✅ File Tersedia", fg="#50fa7b")
                self.btn_play_file.config(state="normal")
            else:
                self.lbl_h_path.config(text="❌ File Sudah Dihapus / Tidak Ditemukan", fg="#ff5555")
                self.btn_play_file.config(state="disabled")

            # Load Cover Thumbnail (Cache lokal / fallback online)
            rjid = h.get("rjid", "")
            cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg")
            if os.path.exists(cache_file):
                try:
                    pil_img = Image.open(cache_file)
                    pil_img.thumbnail((280, 195))
                    self.hist_preview_image = ImageTk.PhotoImage(pil_img)
                    self.hist_canvas.delete("all")
                    self.hist_canvas.create_image(145, 97, image=self.hist_preview_image)
                    return
                except Exception:
                    pass

            # Fallback download cover jika cache belum ada
            def load_online_cover():
                cover_url = h.get("cover_url", f"https://pic.weeabo0.xyz/{rjid}_img_main.jpg")
                try:
                    req = urllib.request.Request(cover_url, headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((280, 195))
                    os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                    pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                    self.hist_preview_image = ImageTk.PhotoImage(pil_img)
                    self.hist_canvas.delete("all")
                    self.hist_canvas.create_image(145, 97, image=self.hist_preview_image)
                except Exception:
                    pass

            threading.Thread(target=load_online_cover, daemon=True).start()

    def _play_history_in_player(self):
        """Memutar file riwayat terpilih langsung di Tab Pemutar Audio."""
        selected = self.hist_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        histories = load_history()
        if idx < len(histories):
            h = histories[idx]
            file_path = h.get("output_path", "")
            if not os.path.exists(file_path):
                self._open_selected_history_file()
                return

            # Alihkan notebook ke Tab Player
            self.notebook.select(self.tab_player)
            self._refresh_playlist_view()
            self._player_load_and_play(file_path, meta=h)

    def _open_selected_history_file(self):
        selected = self.hist_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        histories = load_history()
        if idx < len(histories):
            h = histories[idx]
            file_path = h.get("output_path", "")
            if os.path.exists(file_path):
                os.startfile(file_path)
            else:
                self.lbl_h_path.config(text="❌ File Sudah Dihapus / Tidak Ditemukan", fg="#ff5555")
                self.btn_play_file.config(state="disabled")
                ans = ask_dark_yesno(
                    self,
                    "File Tidak Ditemukan",
                    f"File audio untuk '{h.get('rjid', '-')}' sudah tidak ditemukan di lokasi penyimpanan (mungkin telah dipindahkan atau dihapus).\n\nLokasi:\n{file_path}\n\nApakah Anda ingin menghapus riwayat ini dari daftar riwayat?",
                    confirm_text="Hapus Catatan",
                    cancel_text="Batal",
                )
                if ans:
                    self._delete_history_item(idx)

    def _delete_history_item(self, idx=None):
        if idx is None:
            selected = self.hist_tree.selection()
            if not selected:
                show_dark_info(self, "Informasi", "Pilih item riwayat yang ingin dihapus terlebih dahulu.")
                return
            idx = int(selected[0])

        histories = load_history()
        if 0 <= idx < len(histories):
            deleted = histories.pop(idx)
            from config_manager import save_history
            save_history(histories)
            self._load_history_view()
            # Reset detail view
            self.hist_canvas.delete("all")
            self.hist_canvas.create_text(145, 97, text="Pilih item riwayat", fill="#6272a4", font=("Segoe UI", 10))
            self.lbl_h_id.config(text="-")
            self.lbl_h_title.config(text="-")
            self.lbl_h_cv.config(text="-")
            self.lbl_h_circle.config(text="-")
            self.lbl_h_rating.config(text="-", fg="#f8f8f2")
            self.lbl_h_genre.config(text="-")
            self.lbl_h_path.config(text="-")
            self.btn_play_file.config(state="disabled")
            self.btn_del_history.config(state="disabled")
            self._log(f"[i] Menghapus riwayat untuk: {deleted.get('rjid', '-')}")

    def _start_download_thread(self):
        if self.is_downloading:
            return
        if not self.queue_items:
            show_dark_info(self, "Informasi", "Silakan tambahkan kode RJ ke antrean terlebih dahulu.")
            return

        self.is_downloading = True
        self.stop_requested = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _stop_downloads(self):
        self.stop_requested = True
        self._log("[!] Menghentikan proses download seketika...")
        self.stop_btn.config(state="disabled")

        # 1. Kill subprocess aktif secara paksa beserta anak-anaknya (yt-dlp, aria2c, ffmpeg)
        if self.current_process and self.current_process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self.current_process.kill()
            except Exception:
                pass
            self.current_process = None

        # 2. Pastikan process aria2c / yt-dlp / ffmpeg yatim dimatikan
        if sys.platform == "win32":
            for p_name in ["aria2c.exe", "yt-dlp.exe", "ffmpeg.exe"]:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", p_name],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except Exception:
                    pass

        # 3. Bersihkan sampah part & temp files di .cache/temp/
        temp_dir = os.path.join(".cache", "temp")
        if os.path.exists(temp_dir):
            for fname in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, fname)
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                except OSError:
                    pass

        self._update_progress(0, "Download Dihentikan")

    def _download_worker(self):
        download_dir = get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        total_items = len(self.queue_items)
        self._update_progress(0, f"Mempersiapkan {total_items} item...")

        for idx, item in enumerate(self.queue_items):
            if self.stop_requested:
                break

            item_step = 100.0 / max(1, total_items)
            base_pct = idx * item_step

            if item["status"] == "Selesai":
                self._update_progress((idx + 1) * item_step, f"[{idx+1}/{total_items}] Selesai (Dilewati)")
                continue

            rjid = item["rjid"]
            title = item.get("title", "")

            # Nama File Output
            if self.opt_detailed_name.get() and title and title != "Memuat info..." and title != rjid:
                clean_title = sanitize_filename(title)
                final_output = os.path.join(download_dir, f"[{rjid}] {clean_title}.mp3")
            else:
                final_output = os.path.join(download_dir, f"{rjid}.mp3")

            # Cek jika file sudah ada
            if os.path.exists(final_output):
                self._log(f"[SKIP] File '{os.path.basename(final_output)}' sudah ada.")
                item["status"] = "Selesai"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Selesai (Ada)"))
                self._update_progress((idx + 1) * item_step, f"[{idx+1}/{total_items}] Selesai (Sudah Ada)")
                continue

            # Update status ke downloading
            item["status"] = "Downloading"
            self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Mengunduh..."))
            self.after(0, lambda i=idx: self.tree.selection_set(str(i)))

            cover_url = item.get("cover_url") or f"https://pic.weeabo0.xyz/{rjid}_img_main.jpg"
            temp_dir = os.path.join(".cache", "temp")
            os.makedirs(temp_dir, exist_ok=True)

            temp_cover = os.path.join(temp_dir, f"temp_{rjid}_cover.jpg")
            temp_files = [temp_cover]

            try:
                self._log(f"\n--- [{idx+1}/{total_items}] Memproses {rjid} ---")

                # 0. Deteksi Semua Track (Multi-track & Omake)
                self._update_progress(base_pct + item_step * 0.05, f"[{idx+1}/{total_items}] Memindai track audio...")
                self._log("[0/3] Mendeteksi jumlah track audio...")
                tracks = discover_all_audio_tracks(rjid, REFERER, USER_AGENT)
                track_names = [t["name"] for t in tracks]
                if len(tracks) > 1:
                    self._log(f"[i] Terdeteksi {len(tracks)} track ({', '.join(track_names)}). Semua akan digabung otomatis!")
                else:
                    self._log(f"[i] Terdeteksi 1 track audio.")

                if self.stop_requested:
                    break

                # 1. Download & Standardize Cover to JPEG (agar terbaca Windows Explorer)
                self._update_progress(base_pct + item_step * 0.15, f"[{idx+1}/{total_items}] Mengunduh cover art...")
                self._log("[1/3] Mengunduh cover art...")
                req = urllib.request.Request(cover_url, headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    img_bytes = resp.read()
                with Image.open(io.BytesIO(img_bytes)) as pil_c:
                    pil_c.convert("RGB").save(temp_cover, "JPEG", quality=92)

                if self.stop_requested:
                    break

                # 2. Download Semua Track Audio
                downloaded_track_files = []
                for t_idx, track_info in enumerate(tracks, start=1):
                    if self.stop_requested:
                        break

                    t_name = track_info["name"]
                    t_url = track_info["url"]
                    t_out_tmpl = os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.%(ext)s")
                    t_final_mp3 = os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp3")

                    temp_files.extend([
                        t_final_mp3,
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}_.mp3"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp4"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.temp.mp4"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.(ext)s.mp3"),
                    ])

                    t_start_ratio = 0.15 + 0.65 * ((t_idx - 1) / len(tracks))
                    t_end_ratio = 0.15 + 0.65 * (t_idx / len(tracks))

                    self._update_progress(
                        base_pct + item_step * t_start_ratio,
                        f"[{idx+1}/{total_items}] Menghubungkan {t_name} [{t_idx}/{len(tracks)}]...",
                        speed="Menghubungkan...",
                        eta="Menghitung...",
                        size_str="Ukuran: Memuat...",
                    )
                    self._log(f"[2/3] Mengunduh {t_name} [{t_idx}/{len(tracks)}]...")

                    conn_val = str(self.config.get("connections", 16))
                    ytdlp_bin = get_bin_executable("yt-dlp")
                    aria2c_bin = get_bin_executable("aria2c")
                    ffmpeg_bin = get_bin_executable("ffmpeg")
                    ffmpeg_dir = os.path.dirname(os.path.abspath(ffmpeg_bin))

                    cmd_ytdlp = [
                        ytdlp_bin,
                        "--newline",
                        "--ffmpeg-location", ffmpeg_dir,
                        "-N", conn_val,
                        "--downloader", aria2c_bin,
                        "--downloader-args", f"aria2c:-s {conn_val} -x {conn_val} -k 1M --summary-interval=1",
                        "--fixup", "never",
                        "--add-header", f"Referer: {REFERER}",
                        "--add-header", f"Origin: {REFERER}",
                        "--user-agent", USER_AGENT,
                        t_url,
                        "-x",
                        "--audio-format", "mp3",
                        "-o", t_out_tmpl,
                    ]
                    self.current_process = subprocess.Popen(
                        cmd_ytdlp,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )

                    # Baca stream output secara real-time untuk update indikator kecepatan, ETA, dan ukuran
                    if self.current_process.stdout:
                        for raw_line in iter(self.current_process.stdout.readline, ""):
                            if self.stop_requested:
                                break
                            line_s = raw_line.strip()
                            if not line_s:
                                continue

                            # 1. Parse format standar yt-dlp
                            m_yt = RE_YTDLP_PROGRESS.search(line_s)
                            if m_yt:
                                pct_val = float(m_yt.group(1))
                                total_sz = m_yt.group(2) or "-"
                                sp = m_yt.group(3) or "-"
                                et = m_yt.group(4) or "-"
                                track_part = t_start_ratio + (t_end_ratio - t_start_ratio) * (pct_val / 100.0)
                                cur_overall = base_pct + item_step * track_part
                                self._update_progress(
                                    cur_overall,
                                    status_text=f"[{idx+1}/{total_items}] Mengunduh {t_name} [{t_idx}/{len(tracks)}]",
                                    speed=f"Kecepatan: {sp}",
                                    eta=f"Sisa Waktu: {et}",
                                    size_str=f"Total: ~{total_sz}",
                                )
                                continue

                            # 2. Parse format summary aria2c
                            m_ar = RE_ARIA2_PROGRESS.search(line_s)
                            if m_ar:
                                cur_sz = m_ar.group(1)
                                tot_sz = m_ar.group(2)
                                pct_val = float(m_ar.group(3))
                                sp = f"{m_ar.group(4)}/s"
                                et = m_ar.group(5)
                                track_part = t_start_ratio + (t_end_ratio - t_start_ratio) * (pct_val / 100.0)
                                cur_overall = base_pct + item_step * track_part
                                self._update_progress(
                                    cur_overall,
                                    status_text=f"[{idx+1}/{total_items}] Mengunduh {t_name} [{t_idx}/{len(tracks)}]",
                                    speed=f"Kecepatan: {sp}",
                                    eta=f"Sisa Waktu: {et}",
                                    size_str=f"Ukuran: {cur_sz} / {tot_sz}",
                                )
                                continue

                            # 3. Parse format fragment HLS
                            m_fr = RE_FRAG_PROGRESS.search(line_s)
                            if m_fr:
                                cur_f = int(m_fr.group(1))
                                tot_f = int(m_fr.group(2))
                                if tot_f > 0:
                                    pct_val = (cur_f / tot_f) * 100.0
                                    track_part = t_start_ratio + (t_end_ratio - t_start_ratio) * (pct_val / 100.0)
                                    cur_overall = base_pct + item_step * track_part
                                    self._update_progress(
                                        cur_overall,
                                        status_text=f"[{idx+1}/{total_items}] Mengunduh {t_name} (Frag {cur_f}/{tot_f})",
                                        speed=None,
                                        eta=None,
                                        size_str=f"Segmen: {cur_f}/{tot_f}",
                                    )
                                    continue

                            # Filter log agar log konsol bersih dari noise [generic], [download], [#a1b2c3], [info], [hlsnative]
                            if line_s.startswith("ERROR:") or line_s.startswith("WARNING:"):
                                self._log(f"  [!] {line_s}")
                            elif not any(line_s.startswith(pfx) for pfx in ["[download]", "[#", "[generic]", "[info]", "[hlsnative]", "[ExtractAudio]", "[Merger]", "Deleting original file"]):
                                self._log(f"  {line_s}")

                    self.current_process.wait()

                    if self.stop_requested:
                        break

                    # Deteksi file audio yang berhasil dibuat
                    possible_files = [
                        t_final_mp3,
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}_.mp3"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.(ext)s.mp3"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp4"),
                    ]
                    actual_file = next((f for f in possible_files if os.path.exists(f) and os.path.getsize(f) > 0), None)

                    if not actual_file:
                        raise FileNotFoundError(f"File audio untuk {t_name} gagal diunduh atau diekstrak.")
                    downloaded_track_files.append(actual_file)

                if self.stop_requested:
                    break

                # 3. Embed Thumbnail & Full Metadata ke MP3 (serta Concatenate jika Multi-track)
                artist_val = item.get("cv", "")
                if not artist_val or artist_val == "-":
                    artist_val = "JapaneseASMR"
                album_val = item.get("circle", "")
                if not album_val or album_val == "-":
                    album_val = rjid
                genre_val = item.get("genre", "")
                if not genre_val or genre_val == "-":
                    genre_val = "ASMR"
                rating_val = item.get("age_rating", "-")

                self._update_progress(base_pct + item_step * 0.90, f"[{idx+1}/{total_items}] Menyematkan cover & metadata ID3...")
                ffmpeg_bin = get_bin_executable("ffmpeg")

                if len(downloaded_track_files) > 1:
                    self._log(f"[3/3] Menggabungkan {len(tracks)} track & menyematkan metadata ID3...")
                    concat_list_file = os.path.join(temp_dir, f"concat_{rjid}.txt")
                    temp_files.append(concat_list_file)
                    with open(concat_list_file, "w", encoding="utf-8") as f_concat:
                        for tf in downloaded_track_files:
                            safe_p = os.path.abspath(tf).replace("\\", "/")
                            f_concat.write(f"file '{safe_p}'\n")

                    cmd_ffmpeg = [
                        ffmpeg_bin,
                        "-hide_banner",
                        "-loglevel", "error",
                        "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", concat_list_file,
                        "-i", temp_cover,
                        "-map", "0:a",
                        "-map", "1:v",
                        "-c:a", "libmp3lame",
                        "-q:a", "2",
                        "-c:v", "mjpeg",
                        "-disposition:v:0", "attached_pic",
                        "-id3v2_version", "3",
                        "-metadata:s:v", "title=Album cover",
                        "-metadata:s:v", "comment=Cover (front)",
                        "-metadata", f"title={title if title else rjid}",
                        "-metadata", f"artist={artist_val}",
                        "-metadata", f"album={album_val}",
                        "-metadata", f"genre={genre_val}",
                        "-metadata", f"comment=Rating: {rating_val} | Tracks: {len(tracks)} Gabungan ({', '.join(track_names)})",
                        final_output,
                    ]
                else:
                    self._log("[3/3] Menyematkan cover art, Genre, Rating & metadata ID3...")
                    cmd_ffmpeg = [
                        ffmpeg_bin,
                        "-hide_banner",
                        "-loglevel", "error",
                        "-y",
                        "-i", downloaded_track_files[0],
                        "-i", temp_cover,
                        "-map", "0:a",
                        "-map", "1:v",
                        "-c:a", "copy",
                        "-c:v", "mjpeg",
                        "-disposition:v:0", "attached_pic",
                        "-id3v2_version", "3",
                        "-metadata:s:v", "title=Album cover",
                        "-metadata:s:v", "comment=Cover (front)",
                        "-metadata", f"title={title if title else rjid}",
                        "-metadata", f"artist={artist_val}",
                        "-metadata", f"album={album_val}",
                        "-metadata", f"genre={genre_val}",
                        "-metadata", f"comment=Rating: {rating_val} | Circle: {album_val} | CV: {artist_val}",
                        final_output,
                    ]

                self.current_process = subprocess.Popen(
                    cmd_ffmpeg,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                self.current_process.wait()

                if self.stop_requested:
                    break

                # Validasi ketat file output
                if self.current_process.returncode != 0 or not os.path.exists(final_output) or os.path.getsize(final_output) == 0:
                    raise RuntimeError(f"Gagal memproses file audio final: {os.path.basename(final_output)}")
                self.current_process.wait()

                if self.stop_requested:
                    break

                # Simpan ke riwayat unduhan & cache cover art
                add_to_history(
                    rjid=rjid,
                    title=title,
                    cv=item.get("cv", "-"),
                    circle=item.get("circle", "-"),
                    genre=item.get("genre", "-"),
                    age_rating=item.get("age_rating", "-"),
                    cover_url=cover_url,
                    output_path=final_output,
                    temp_cover_path=temp_cover,
                )

                item["status"] = "Selesai"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Selesai"))
                self.after(0, self._load_history_view)
                self._update_progress(
                    (idx + 1) * item_step,
                    f"[{idx+1}/{total_items}] Selesai {rjid}",
                    speed="Kecepatan: -",
                    eta="Sisa Waktu: -",
                    size_str="Status: Selesai",
                )
                self._log(f"[✓] SUKSES: Tersimpan di {os.path.basename(final_output)}")

            except Exception as e:
                if self.stop_requested:
                    break
                item["status"] = "Error"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Error"))
                self._log(f"[X] Gagal memproses {rjid}: {e}")

            finally:
                for tf in temp_files:
                    if os.path.exists(tf):
                        try:
                            os.remove(tf)
                        except OSError:
                            pass

        self.is_downloading = False
        self.current_process = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

        if self.stop_requested:
            self._log("[!] Semua proses download telah dihentikan.")
            self._update_progress(
                0,
                "Download Dihentikan",
                speed="Kecepatan: -",
                eta="Sisa Waktu: -",
                size_str="Ukuran: - / -",
            )
            # Kembalikan item yang statusnya masih Downloading ke Pending
            for idx, item in enumerate(self.queue_items):
                if item["status"] == "Downloading":
                    item["status"] = "Pending"
                    self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Pending"))
        else:
            self._update_progress(
                100,
                "Semua proses selesai (100%)",
                speed="Kecepatan: -",
                eta="Sisa Waktu: -",
                size_str="Ukuran: Selesai",
            )
            self._log("\n--- Semua proses download dalam antrean selesai ---")
            self.after(0, lambda: show_dark_info(self, "Selesai", "Semua proses unduhan dalam antrean telah selesai!"))

    # ==========================================
    # PEMUTAR AUDIO BAWAAN (WINDOWS NATIVE MCI)
    # ==========================================
    def _mci_send(self, command):
        if sys.platform != "win32":
            return 0, ""
        buf = ctypes.create_unicode_buffer(256)
        err = ctypes.windll.winmm.mciSendStringW(command, buf, 255, 0)
        return err, buf.value

    def _refresh_playlist_view(self):
        """Memuat ulang daftar audio yang tersedia di riwayat/folder untuk dimainkan."""
        self.player_tree.delete(*self.player_tree.get_children())
        histories = load_history()
        self.playlist_items = []

        for h in histories:
            fpath = h.get("output_path", "")
            if os.path.exists(fpath):
                self.playlist_items.append(h)
                idx = len(self.playlist_items) - 1
                self.player_tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        h.get("rjid", "-"),
                        h.get("title", "-"),
                        h.get("cv", "-"),
                        h.get("file_size", "-"),
                    ),
                )

    def _on_playlist_select(self, event):
        selected = self.player_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.playlist_items):
            item = self.playlist_items[idx]
            self._render_player_cover(item.get("rjid", ""), item.get("cover_url", ""))

    def _player_play_selected(self):
        selected = self.player_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.playlist_items):
            self.current_track_index = idx
            item = self.playlist_items[idx]
            self._player_load_and_play(item.get("output_path", ""), meta=item)

    def _player_load_and_play(self, file_path, meta=None):
        if not os.path.exists(file_path):
            show_dark_warning(self, "File Tidak Ditemukan", f"File audio tidak ditemukan:\n{file_path}")
            return

        self._player_stop()
        short_path = os.path.abspath(file_path)
        self._mci_send("close asmr_player")
        err, _ = self._mci_send(f'open "{short_path}" type mpegvideo alias asmr_player')
        if err != 0:
            show_dark_error(self, "Gagal Memutar", "Format audio tidak dapat diputar oleh sistem MCI.")
            return

        self._mci_send("set asmr_player time format milliseconds")
        _, len_str = self._mci_send("status asmr_player length")
        try:
            self.player_duration_ms = int(len_str)
        except ValueError:
            self.player_duration_ms = 0

        self._mci_send("play asmr_player")
        self.is_playing = True
        self.is_paused = False
        self.current_playing_file = file_path
        self.current_playing_meta = meta or {}

        # Set Volume default
        self._player_set_volume(self.vol_slider.get())

        # Update UI Meta & Controls
        rjid = meta.get("rjid", "-") if meta else "-"
        title = meta.get("title", os.path.basename(file_path)) if meta else os.path.basename(file_path)
        cv = meta.get("cv", "-") if meta else "-"
        circle = meta.get("circle", "-") if meta else "-"

        self.lbl_p_now_title.config(text=f"[{rjid}] {title}")
        self.lbl_p_now_sub.config(text=f"CV: {cv}  |  Circle: {circle}")
        self.lbl_time_total.config(text=self._format_time(self.player_duration_ms))
        self.btn_play_pause.config(text="❚❚ Jeda")

        self._render_player_cover(rjid, meta.get("cover_url", "") if meta else "")
        self._player_schedule_tick()

    def _render_player_cover(self, rjid, cover_url):
        cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg")
        if os.path.exists(cache_file):
            try:
                pil_img = Image.open(cache_file)
                pil_img.thumbnail((290, 195))
                self.player_preview_image = ImageTk.PhotoImage(pil_img)
                self.player_canvas.delete("all")
                self.player_canvas.create_image(145, 97, image=self.player_preview_image)
                return
            except Exception:
                pass

        if cover_url:
            def load_cover():
                try:
                    req = urllib.request.Request(cover_url, headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((290, 195))
                    os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                    pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                    self.player_preview_image = ImageTk.PhotoImage(pil_img)
                    self.player_canvas.delete("all")
                    self.player_canvas.create_image(145, 97, image=self.player_preview_image)
                except Exception:
                    pass
            threading.Thread(target=load_cover, daemon=True).start()

    def _player_play_pause_toggle(self):
        if not self.current_playing_file:
            if self.playlist_items:
                self.current_track_index = 0
                item = self.playlist_items[0]
                self._player_load_and_play(item.get("output_path", ""), meta=item)
            return

        if self.is_playing:
            self._mci_send("pause asmr_player")
            self.is_playing = False
            self.is_paused = True
            self.btn_play_pause.config(text="▶ Putar")
        else:
            self._mci_send("play asmr_player")
            self.is_playing = True
            self.is_paused = False
            self.btn_play_pause.config(text="❚❚ Jeda")
            self._player_schedule_tick()

    def _player_stop(self):
        self._mci_send("stop asmr_player")
        self._mci_send("seek asmr_player to start")
        self.is_playing = False
        self.is_paused = False
        self.btn_play_pause.config(text="▶ Putar")
        self.timeline_slider.set(0)
        self.lbl_time_cur.config(text="00:00")

    def _on_slider_change(self, val):
        if self.is_user_dragging_slider and self.player_duration_ms > 0:
            cur_ms = int(float(val) * self.player_duration_ms / 100.0)
            self.lbl_time_cur.config(text=self._format_time(cur_ms))

    def _on_slider_release(self, event):
        self.is_user_dragging_slider = False
        if not self.current_playing_file or self.player_duration_ms <= 0:
            return
        target_pct = self.timeline_slider.get()
        target_ms = int(float(target_pct) * self.player_duration_ms / 100.0)
        self._mci_send(f"seek asmr_player to {target_ms}")
        if self.is_playing:
            self._mci_send("play asmr_player")

    def _player_set_volume(self, val):
        vol_pct = int(float(val))
        if hasattr(self, "lbl_vol_val"):
            self.lbl_vol_val.config(text=f"{vol_pct}%")
        # MCI volume range: 0 sampai 1000
        mci_vol = int(vol_pct * 10)
        self._mci_send(f"setaudio asmr_player volume to {mci_vol}")

    def _player_prev_track(self):
        if not self.playlist_items:
            return
        if self.current_track_index > 0:
            self.current_track_index -= 1
        else:
            self.current_track_index = len(self.playlist_items) - 1
        item = self.playlist_items[self.current_track_index]
        self._player_load_and_play(item.get("output_path", ""), meta=item)

    def _player_next_track(self):
        if not self.playlist_items:
            return
        if self.current_track_index < len(self.playlist_items) - 1:
            self.current_track_index += 1
        else:
            self.current_track_index = 0
        item = self.playlist_items[self.current_track_index]
        self._player_load_and_play(item.get("output_path", ""), meta=item)

    def _player_toggle_loop(self):
        self.is_looping = not self.is_looping
        if self.is_looping:
            self.btn_loop.config(text="Loop: ON", fg="#50fa7b", bg="#282a36")
        else:
            self.btn_loop.config(text="Loop: OFF", fg="#a6adc8", bg="#44475a")

    def _player_tick(self):
        if not self.is_playing or not self.current_playing_file:
            return

        _, pos_str = self._mci_send("status asmr_player position")
        _, mode_str = self._mci_send("status asmr_player mode")

        try:
            pos_ms = int(pos_str)
        except ValueError:
            pos_ms = 0

        if not self.is_user_dragging_slider and self.player_duration_ms > 0:
            pct = (pos_ms / self.player_duration_ms) * 100.0
            self.timeline_slider.set(pct)
            self.lbl_time_cur.config(text=self._format_time(pos_ms))

        # Cek jika track selesai
        if mode_str == "stopped" or (self.player_duration_ms > 0 and pos_ms >= self.player_duration_ms - 500):
            if self.is_looping:
                self._mci_send("seek asmr_player to start")
                self._mci_send("play asmr_player")
                self._player_schedule_tick()
            else:
                self._player_next_track()
            return

        self._player_schedule_tick()

    def _player_schedule_tick(self):
        if self.is_playing:
            self.after(500, self._player_tick)

    def _format_time(self, ms):
        total_sec = max(0, int(ms / 1000))
        mins = total_sec // 60
        secs = total_sec % 60
        hours = mins // 60
        if hours > 0:
            mins = mins % 60
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"


if __name__ == "__main__":
    app = JapaneseASMRApp()
    app.mainloop()
