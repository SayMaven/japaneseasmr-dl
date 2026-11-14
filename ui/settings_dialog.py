import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser
import customtkinter as ctk
from PIL import Image, ImageTk

from config_manager import (
    clear_all_history,
    clear_cover_cache,
    clear_temp_cache,
    get_audio_codec,
    get_audio_format,
    get_bin_executable,
    get_cache_size_info,
    get_download_dir,
    get_ytdlp_version,
    load_config,
    load_history,
    save_config,
    set_audio_format,
    set_download_dir,
    update_ytdlp_engine,
)
from i18n import get_active_language, get_available_languages, set_active_language, t
from ui.dialogs import (
    apply_dark_titlebar,
    ask_dark_yesno,
    show_dark_error,
    show_dark_info,
    show_dark_warning,
)
from ui.theme import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BG_APP,
    BORDER_ACTIVE,
    BORDER_SUBTLE,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CAPTION,
    FONT_CODE,
    FONT_SUBTITLE,
    FONT_TITLE,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    STATUS_DANGER,
    STATUS_INFO,
    STATUS_SUCCESS,
    STATUS_WARNING,
    SURFACE_CARD,
    SURFACE_ELEVATED,
    SURFACE_INPUT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class SettingsDialog(ctk.CTkToplevel):
    """Dialog Pengaturan Modern dengan Sidebar Navigasi Vertikal dan Scrollable Content Panel."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Pengaturan - JapaneseASMR Downloader")
        self.geometry("900x640")
        self.minsize(820, 540)
        self.configure(fg_color=BG_APP)
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
            cx = px + (pw - 900) // 2
            cy = py + (ph - 640) // 2
            self.geometry(f"+{max(0, cx)}+{max(0, cy)}")
        except Exception:
            pass

        self.cfg = load_config()

        # Variable States
        self.var_language = tk.StringVar(value=self.cfg.get("language", "auto"))
        self.var_download_dir = tk.StringVar(value=self.cfg.get("download_dir", get_download_dir()))
        self.var_detailed_name = tk.BooleanVar(value=self.cfg.get("use_detailed_filename", False))
        self.var_notify_popup = tk.BooleanVar(value=self.cfg.get("notify_popup", True))
        self.var_auto_clipboard = tk.BooleanVar(value=self.cfg.get("auto_clipboard", False))
        self.var_connections = tk.IntVar(value=self.cfg.get("connections", 16))
        self.var_ytdlp_channel = tk.StringVar(value=self.cfg.get("ytdlp_channel", "stable"))
        self.var_audio_format = tk.StringVar(value=self.cfg.get("audio_format", get_audio_format()))

        self.nav_buttons = {}
        self.current_tab = "general"

        self._build_ui()
        self._show_tab("general")

    def _build_ui(self):
        self.title(t("settings_title"))

        # 1. Header Bar Dialog (Top)
        header_bar = ctk.CTkFrame(self, fg_color=SURFACE_CARD, height=50, corner_radius=0)
        header_bar.pack(fill="x", side="top")

        lbl_header = ctk.CTkLabel(
            header_bar,
            text=f"⚙  {t('settings_header')}",
            font=FONT_SUBTITLE,
            text_color=TEXT_PRIMARY,
        )
        lbl_header.pack(side="left", padx=20, pady=12)

        # 2. Footer Bar Dialog (Bottom)
        footer_bar = ctk.CTkFrame(self, fg_color=SURFACE_CARD, height=56, corner_radius=0)
        footer_bar.pack(fill="x", side="bottom")

        btn_save = ctk.CTkButton(
            footer_bar,
            text=t("btn_save_settings"),
            font=FONT_BODY_BOLD,
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
            text_color="#ffffff",
            corner_radius=RADIUS_MD,
            height=36,
            width=140,
            command=self._save_settings,
        )
        btn_save.pack(side="right", padx=16, pady=10)

        btn_cancel = ctk.CTkButton(
            footer_bar,
            text=t("btn_cancel"),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_MD,
            height=36,
            width=90,
            command=self._on_dialog_close,
        )
        btn_cancel.pack(side="right", padx=(0, 8), pady=10)

        # 3. Main Body: Sidebar (Kiri) & Scrollable Content Panel (Kanan)
        body_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        body_frame.pack(fill="both", expand=True)

        # Sidebar Kiri
        self.sidebar = ctk.CTkFrame(body_frame, fg_color=SURFACE_CARD, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        lbl_menu = ctk.CTkLabel(
            self.sidebar,
            text=t("lbl_category"),
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        lbl_menu.pack(fill="x", padx=16, pady=(16, 8))

        tabs = [
            ("general", t("tab_settings_general")),
            ("download", t("tab_settings_download")),
            ("cache", t("tab_settings_cache")),
            ("about", t("tab_settings_about")),
        ]

        for tab_id, label_text in tabs:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {label_text}",
                font=FONT_BODY_BOLD,
                anchor="w",
                corner_radius=RADIUS_MD,
                height=38,
                fg_color="transparent",
                hover_color=SURFACE_ELEVATED,
                text_color=TEXT_SECONDARY,
                command=lambda tid=tab_id: self._show_tab(tid),
            )
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[tab_id] = btn

        # Content Panel Kanan (Scrollable Frame)
        self.content_container = ctk.CTkScrollableFrame(body_frame, fg_color="transparent")
        self.content_container.pack(side="right", fill="both", expand=True, padx=20, pady=16)

    def _show_tab(self, tab_name):
        self.current_tab = tab_name

        for t_id, btn in self.nav_buttons.items():
            if t_id == tab_name:
                btn.configure(fg_color=ACCENT_PRIMARY, text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY)

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
        lbl_title = ctk.CTkLabel(
            self.content_container,
            text=t("lbl_settings_general_title"),
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 14))

        # Card: Bahasa
        card_lang = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_lang.pack(fill="x", pady=(0, 12))

        p_lang = ctk.CTkFrame(card_lang, fg_color="transparent")
        p_lang.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_lang, text=t("lbl_language"), font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(p_lang, text=t("lbl_language_desc"), font=FONT_CAPTION, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(2, 8))

        lang_options = get_available_languages()
        disp_map = {code: disp for code, disp in lang_options}
        code_map = {disp: code for code, disp in lang_options}

        cur_code = self.var_language.get()
        cur_disp = disp_map.get(cur_code, lang_options[0][1])

        def _on_lang_changed(choice):
            self.var_language.set(code_map.get(choice, "auto"))

        self.cbo_lang = ctk.CTkOptionMenu(
            p_lang,
            values=[disp for _, disp in lang_options],
            command=_on_lang_changed,
            font=FONT_BODY,
            corner_radius=RADIUS_MD,
            fg_color=SURFACE_INPUT,
            button_color=BORDER_SUBTLE,
            button_hover_color=ACCENT_PRIMARY,
            height=32,
        )
        self.cbo_lang.set(cur_disp)
        self.cbo_lang.pack(anchor="w")

        # Card: Folder Download
        card_dir = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_dir.pack(fill="x", pady=(0, 12))

        p_dir = ctk.CTkFrame(card_dir, fg_color="transparent")
        p_dir.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_dir, text=t("lbl_storage_folder"), font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(p_dir, text=t("lbl_storage_folder_desc"), font=FONT_CAPTION, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(2, 8))

        dir_row = ctk.CTkFrame(p_dir, fg_color="transparent")
        dir_row.pack(fill="x")

        self.entry_dir = ctk.CTkEntry(
            dir_row,
            textvariable=self.var_download_dir,
            font=FONT_CODE,
            corner_radius=RADIUS_MD,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
            height=34,
        )
        self.entry_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(
            dir_row,
            text=t("btn_browse"),
            font=FONT_BODY_BOLD,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_MD,
            height=34,
            width=90,
            command=self._browse_dir,
        )
        btn_browse.pack(side="right")

        # Card: Opsi Otomatisasi (Switches)
        card_opts = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_opts.pack(fill="x", pady=(0, 12))

        p_opts = ctk.CTkFrame(card_opts, fg_color="transparent")
        p_opts.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_opts, text="Preferensi Otomatisasi", font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", pady=(0, 8))

        self.chk_detailed = ctk.CTkSwitch(
            p_opts,
            text=t("chk_detailed_name"),
            variable=self.var_detailed_name,
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            fg_color=SURFACE_INPUT,
            progress_color=ACCENT_PRIMARY,
        )
        self.chk_detailed.pack(fill="x", pady=4)

        self.chk_notify = ctk.CTkSwitch(
            p_opts,
            text=t("chk_notify_popup"),
            variable=self.var_notify_popup,
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            fg_color=SURFACE_INPUT,
            progress_color=ACCENT_PRIMARY,
        )
        self.chk_notify.pack(fill="x", pady=4)

        self.chk_clipboard = ctk.CTkSwitch(
            p_opts,
            text=t("chk_auto_clipboard"),
            variable=self.var_auto_clipboard,
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            fg_color=SURFACE_INPUT,
            progress_color=ACCENT_PRIMARY,
        )
        self.chk_clipboard.pack(fill="x", pady=4)

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.var_download_dir.get())
        if d:
            self.var_download_dir.set(os.path.abspath(d))

    # ==================== TAB 2: DOWNLOAD & ENGINE ====================
    def _render_download_tab(self):
        lbl_title = ctk.CTkLabel(
            self.content_container,
            text=t("lbl_settings_download_title"),
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 14))

        # Card: Format Audio
        card_fmt = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_fmt.pack(fill="x", pady=(0, 12))

        p_fmt = ctk.CTkFrame(card_fmt, fg_color="transparent")
        p_fmt.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_fmt, text=t("lbl_audio_format"), font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(p_fmt, text=t("lbl_audio_format_desc"), font=FONT_CAPTION, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(2, 8))

        fmt_options = [
            ("auto", t("fmt_auto")),
            ("m4a", t("fmt_m4a")),
            ("mp3", t("fmt_mp3")),
            ("flac", t("fmt_flac")),
            ("wav", t("fmt_wav")),
        ]
        fmt_disp_map = {k: v for k, v in fmt_options}
        fmt_code_map = {v: k for k, v in fmt_options}

        def _on_fmt_changed(choice):
            self.var_audio_format.set(fmt_code_map.get(choice, "auto"))

        cur_fmt = self.var_audio_format.get()
        cbo_fmt = ctk.CTkOptionMenu(
            p_fmt,
            values=[v for _, v in fmt_options],
            command=_on_fmt_changed,
            font=FONT_BODY,
            corner_radius=RADIUS_MD,
            fg_color=SURFACE_INPUT,
            button_color=BORDER_SUBTLE,
            button_hover_color=ACCENT_PRIMARY,
            height=32,
        )
        cbo_fmt.set(fmt_disp_map.get(cur_fmt, fmt_options[0][1]))
        cbo_fmt.pack(anchor="w")

        # Card: Koneksi Paralel (Aria2c)
        card_conn = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_conn.pack(fill="x", pady=(0, 12))

        p_conn = ctk.CTkFrame(card_conn, fg_color="transparent")
        p_conn.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_conn, text=t("lbl_aria2_connections"), font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(p_conn, text=t("lbl_aria2_connections_desc"), font=FONT_CAPTION, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(2, 8))

        conn_options = ["4", "8", "16", "24", "32"]
        cbo_conn = ctk.CTkOptionMenu(
            p_conn,
            values=conn_options,
            command=lambda v: self.var_connections.set(int(v)),
            font=FONT_BODY,
            corner_radius=RADIUS_MD,
            fg_color=SURFACE_INPUT,
            button_color=BORDER_SUBTLE,
            button_hover_color=ACCENT_PRIMARY,
            height=32,
            width=100,
        )
        cbo_conn.set(str(self.var_connections.get()))
        cbo_conn.pack(anchor="w")

        # Card: Status & Pembaruan yt-dlp
        card_upd = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_upd.pack(fill="x", pady=(0, 12))

        p_upd = ctk.CTkFrame(card_upd, fg_color="transparent")
        p_upd.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_upd, text=t("lbl_ytdlp_engine"), font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")

        ver = get_ytdlp_version()
        ctk.CTkLabel(p_upd, text=f"Versi yt-dlp Terpasang: {ver}", font=FONT_CODE, text_color=STATUS_INFO, anchor="w").pack(fill="x", pady=(4, 8))

        upd_action_row = ctk.CTkFrame(p_upd, fg_color="transparent")
        upd_action_row.pack(fill="x")

        self.btn_update_ytdlp = ctk.CTkButton(
            upd_action_row,
            text=t("btn_update_ytdlp"),
            font=FONT_BODY_BOLD,
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
            text_color="#ffffff",
            corner_radius=RADIUS_MD,
            height=32,
            width=140,
            command=self._do_update_ytdlp,
        )
        self.btn_update_ytdlp.pack(side="left", padx=(0, 10))

        self.lbl_ytdlp_status = ctk.CTkLabel(
            upd_action_row,
            text="Siap memeriksa pembaruan",
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
        )
        self.lbl_ytdlp_status.pack(side="left")

    def _do_update_ytdlp(self):
        self.btn_update_ytdlp.configure(state="disabled")
        self.lbl_ytdlp_status.configure(text="Sedang mengunduh rilis terbaru...", text_color=STATUS_INFO)

        def _worker():
            channel = self.var_ytdlp_channel.get()
            success, status_code, msg = update_ytdlp_engine(channel=channel)

            def _apply():
                self.btn_update_ytdlp.configure(state="normal")
                if success:
                    ver = get_ytdlp_version()
                    self.lbl_ytdlp_status.configure(text=f"Sukses diperbarui ke: {ver}", text_color=STATUS_SUCCESS)
                    show_dark_info(self, "Pembaruan Berhasil", f"Engine yt-dlp berhasil diperbarui!\n\nVersi aktif: {ver}")
                elif status_code == "already_latest":
                    self.lbl_ytdlp_status.configure(text="Sudah menggunakan versi terbaru", text_color=TEXT_SECONDARY)
                    show_dark_info(self, "Info Pembaruan", msg)
                else:
                    self.lbl_ytdlp_status.configure(text="Pembaruan gagal", text_color=STATUS_DANGER)
                    show_dark_error(self, "Pembaruan Gagal", f"Gagal memperbarui engine yt-dlp.\n\nError: {msg}")

            self.after(0, _apply)

        threading.Thread(target=_worker, daemon=True).start()

    # ==================== TAB 3: CACHE & DATA ====================
    def _render_cache_tab(self):
        lbl_title = ctk.CTkLabel(
            self.content_container,
            text=t("lbl_settings_cache_title"),
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 14))

        info = get_cache_size_info()
        histories = load_history()

        # Card: Statistik Cache
        card_stats = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_stats.pack(fill="x", pady=(0, 12))

        p_stats = ctk.CTkFrame(card_stats, fg_color="transparent")
        p_stats.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_stats, text="Ukuran Cache & Data Tersimpan", font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", pady=(0, 8))

        c_count = info.get("covers_count", 0)
        c_size = info.get("covers_size", "0 MB")
        t_count = info.get("temp_count", 0)
        t_size = info.get("temp_size", "0 MB")

        ctk.CTkLabel(p_stats, text=f"• Cache Thumbnail Cover: {c_count} file ({c_size})", font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=2)
        ctk.CTkLabel(p_stats, text=f"• Cache Berkas Sementara: {t_count} file ({t_size})", font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=2)
        ctk.CTkLabel(p_stats, text=f"• Total Riwayat Karya: {len(histories)} entri", font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=2)

        # Card: Tombol Pembersihan
        card_actions = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_actions.pack(fill="x", pady=(0, 12))

        p_act = ctk.CTkFrame(card_actions, fg_color="transparent")
        p_act.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_act, text="Tindakan Pemeliharaan", font=FONT_SUBTITLE, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", pady=(0, 10))

        btn_c_covers = ctk.CTkButton(
            p_act,
            text=t("btn_clear_covers"),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_MD,
            height=32,
            command=self._do_clear_covers,
        )
        btn_c_covers.pack(fill="x", pady=4)

        btn_c_temp = ctk.CTkButton(
            p_act,
            text=t("btn_clear_temp"),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_MD,
            height=32,
            command=self._do_clear_temp,
        )
        btn_c_temp.pack(fill="x", pady=4)

        btn_c_hist = ctk.CTkButton(
            p_act,
            text=t("btn_clear_all_history"),
            font=FONT_BODY,
            fg_color=STATUS_DANGER,
            hover_color="#ef4444",
            text_color="#ffffff",
            corner_radius=RADIUS_MD,
            height=32,
            command=self._do_clear_history,
        )
        btn_c_hist.pack(fill="x", pady=(4, 0))

    def _do_clear_covers(self):
        c, s = clear_cover_cache()
        show_dark_info(self, "Cache Dibersihkan", f"Berhasil membersihkan {c} file cover ({s:.2f} MB).")
        self._show_tab("cache")

    def _do_clear_temp(self):
        c, s = clear_temp_cache()
        show_dark_info(self, "Cache Dibersihkan", f"Berhasil membersihkan {c} file temp ({s:.2f} MB).")
        self._show_tab("cache")

    def _do_clear_history(self):
        ans = ask_dark_yesno(
            self,
            "Konfirmasi Hapus",
            "Apakah Anda yakin ingin menghapus SEMUA riwayat unduhan?\n\n(Catatan: Berkas audio di folder unduhan TIDAK akan dihapus, hanya daftar riwayat yang dibersihkan).",
        )
        if ans:
            c = clear_all_history()
            show_dark_info(self, "Riwayat Dihapus", f"Berhasil menghapus {c} catatan riwayat.")
            self.parent._load_history_view()
            self._show_tab("cache")

    # ==================== TAB 4: TENTANG ====================
    def _render_about_tab(self):
        card_about = ctk.CTkFrame(self.content_container, corner_radius=RADIUS_LG, fg_color=SURFACE_CARD, border_width=1, border_color=BORDER_SUBTLE)
        card_about.pack(fill="x", pady=(0, 12))

        p_abt = ctk.CTkFrame(card_about, fg_color="transparent")
        p_abt.pack(fill="x", padx=20, pady=20)

        # App Logo & Header
        if hasattr(self.parent, "_icon_png_path") and self.parent._icon_png_path and os.path.exists(self.parent._icon_png_path):
            try:
                with Image.open(self.parent._icon_png_path) as p_img:
                    resized = p_img.resize((64, 64), Image.Resampling.LANCZOS)
                    self._about_logo_img = ImageTk.PhotoImage(resized)
                    lbl_logo = tk.Label(p_abt, image=self._about_logo_img, bg=SURFACE_CARD)
                    lbl_logo.pack(pady=(0, 8))
            except Exception:
                pass

        ctk.CTkLabel(p_abt, text="JapaneseASMR Downloader & Audio Player", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(pady=(0, 2))
        ctk.CTkLabel(p_abt, text="Versi 1.1.1 • Windows Pure Desktop GUI", font=FONT_CAPTION, text_color=STATUS_INFO).pack(pady=(0, 12))

        ctk.CTkLabel(
            p_abt,
            text="Aplikasi utilitas pengunduh dan pemutar audio native untuk karya suara ASMR Jepang. Dilengkapi audio player Windows Media Foundation, manajemen chapter CUE, dan metadata resolusi tinggi.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            wraplength=480,
            justify="center",
        ).pack(pady=(0, 16))

        # Links Row
        links_row = ctk.CTkFrame(p_abt, fg_color="transparent")
        links_row.pack(pady=(0, 8))

        ctk.CTkButton(
            links_row,
            text="🌐 Repositori GitHub",
            font=FONT_BODY_BOLD,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_MD,
            height=32,
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl"),
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            links_row,
            text="🐛 Lapor Masalah (Issues)",
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_SECONDARY,
            corner_radius=RADIUS_MD,
            height=32,
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl/issues"),
        ).pack(side="left", padx=6)

    # ==================== SIMPAN & KELUAR ====================
    def _save_settings(self):
        new_lang = self.var_language.get()
        old_lang = get_active_language()

        self.cfg["language"] = new_lang
        self.cfg["download_dir"] = self.var_download_dir.get()
        self.cfg["use_detailed_filename"] = self.var_detailed_name.get()
        self.cfg["notify_popup"] = self.var_notify_popup.get()
        self.cfg["auto_clipboard"] = self.var_auto_clipboard.get()
        self.cfg["connections"] = self.var_connections.get()
        self.cfg["ytdlp_channel"] = self.var_ytdlp_channel.get()
        self.cfg["audio_format"] = self.var_audio_format.get()

        save_config(self.cfg)
        set_download_dir(self.var_download_dir.get())
        set_audio_format(self.var_audio_format.get())

        if hasattr(self.parent, "opt_detailed_name"):
            self.parent.opt_detailed_name.set(self.var_detailed_name.get())
        if hasattr(self.parent, "var_auto_clipboard"):
            self.parent.var_auto_clipboard.set(self.var_auto_clipboard.get())

        if new_lang != old_lang:
            set_active_language(new_lang)
            if hasattr(self.parent, "retranslate_ui"):
                self.parent.retranslate_ui()

        show_dark_info(self, "Pengaturan Disimpan", t("msg_saved_success"))
        self._on_dialog_close()

    def _on_dialog_close(self):
        if hasattr(self, "parent") and self.parent:
            self.parent._settings_dialog = None
        self.destroy()
