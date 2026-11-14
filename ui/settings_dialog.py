import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser
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

class SettingsDialog(tk.Toplevel):
    """Dialog Pengaturan Modern dengan Sidebar Navigasi Vertikal (Kiri) dan Panel Konten (Kanan)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Pengaturan - JapaneseASMR Downloader")
        self.geometry("890x630")
        self.minsize(820, 540)
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
            cx = px + (pw - 890) // 2
            cy = py + (ph - 630) // 2
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
        header_bar = tk.Frame(self, bg="#282a36", height=45)
        header_bar.pack(fill="x", side="top")

        lbl_header = tk.Label(
            header_bar,
            text=t("settings_header"),
            font=("Segoe UI", 12, "bold"),
            bg="#282a36",
            fg="#f8f8f2",
            padx=16,
            pady=10,
        )
        lbl_header.pack(side="left")

        # 2. Footer Bar Dialog (Bottom) - Dikelola lebih dulu agar tombol Simpan/Batal selalu terlihat di bawah
        footer_bar = tk.Frame(self, bg="#181825", height=52)
        footer_bar.pack(fill="x", side="bottom")

        btn_save = tk.Button(
            footer_bar,
            text=t("btn_save_settings"),
            font=("Segoe UI", 9, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            activebackground="#8be9fd",
            bd=0,
            padx=20,
            pady=7,
            cursor="hand2",
            command=self._save_settings,
        )
        btn_save.pack(side="right", padx=16, pady=10)

        btn_cancel = tk.Button(
            footer_bar,
            text=t("btn_cancel"),
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            activebackground="#6272a4",
            bd=0,
            padx=16,
            pady=7,
            cursor="hand2",
            command=self.destroy,
        )
        btn_cancel.pack(side="right", padx=(0, 8), pady=10)

        # 3. Main Body: Sidebar (Kiri) & Scrollable Content Panel (Kanan)
        body_frame = tk.Frame(self, bg="#1e1e2e")
        body_frame.pack(fill="both", expand=True)

        # Sidebar Kiri
        self.sidebar = tk.Frame(body_frame, bg="#181825", width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        lbl_menu = tk.Label(
            self.sidebar,
            text=t("lbl_category"),
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
            ("general", t("tab_settings_general")),
            ("download", t("tab_settings_download")),
            ("cache", t("tab_settings_cache")),
            ("about", t("tab_settings_about")),
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

        # Content Panel Kanan dengan Canvas Scrollable + Scrollbar
        content_wrapper = tk.Frame(body_frame, bg="#1e1e2e")
        content_wrapper.pack(side="right", fill="both", expand=True)

        self.content_canvas = tk.Canvas(content_wrapper, bg="#1e1e2e", highlightthickness=0, bd=0)
        self.content_scrollbar = ttk.Scrollbar(content_wrapper, orient="vertical", command=self.content_canvas.yview)

        self.content_container = tk.Frame(self.content_canvas, bg="#1e1e2e", padx=24, pady=16)
        self.content_window_id = self.content_canvas.create_window((0, 0), window=self.content_container, anchor="nw")

        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)
        self.content_canvas.pack(side="left", fill="both", expand=True)

        def _update_scroll_region(event=None):
            if not self.content_canvas.winfo_exists():
                return
            self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))
            bbox = self.content_canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) > self.content_canvas.winfo_height():
                if not self.content_scrollbar.winfo_ismapped():
                    self.content_scrollbar.pack(side="right", fill="y")
            else:
                if self.content_scrollbar.winfo_ismapped():
                    self.content_scrollbar.pack_forget()

        def _sync_content_width(event):
            if self.content_canvas.winfo_exists():
                self.content_canvas.itemconfig(self.content_window_id, width=event.width)
                _update_scroll_region()

        self.content_container.bind("<Configure>", _update_scroll_region)
        self.content_canvas.bind("<Configure>", _sync_content_width)

        # Mousewheel scroll binding khusus jendela dialog
        def _on_mousewheel(event):
            if self.winfo_exists() and self.content_canvas.winfo_exists():
                bbox = self.content_canvas.bbox("all")
                if bbox and (bbox[3] - bbox[1]) > self.content_canvas.winfo_height():
                    self.content_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.bind("<MouseWheel>", _on_mousewheel)

    def _show_tab(self, tab_name):
        self.current_tab = tab_name

        # Reset scroll ke atas saat beralih tab
        if hasattr(self, "content_canvas") and self.content_canvas.winfo_exists():
            self.content_canvas.yview_moveto(0)

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
            text=t("lbl_settings_general_title"),
            font=("Segoe UI", 12, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 14))

        # Pilihan Bahasa (Language)
        lbl_lang = tk.Label(
            self.content_container,
            text=t("lbl_language"),
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
            anchor="w",
        )
        lbl_lang.pack(fill="x", pady=(2, 2))

        lbl_lang_desc = tk.Label(
            self.content_container,
            text=t("lbl_language_desc"),
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#6272a4",
            anchor="w",
        )
        lbl_lang_desc.pack(fill="x", pady=(0, 6))

        lang_box = tk.Frame(self.content_container, bg="#1e1e2e")
        lang_box.pack(fill="x", pady=(0, 12))

        lang_options = get_available_languages()
        disp_map = {code: disp for code, disp in lang_options}
        code_map = {disp: code for code, disp in lang_options}

        cur_code = self.var_language.get()
        cur_disp = disp_map.get(cur_code, lang_options[0][1])

        self.cbo_lang = ttk.Combobox(
            lang_box,
            values=[disp for _, disp in lang_options],
            state="readonly",
            font=("Segoe UI", 9),
            width=32,
        )
        self.cbo_lang.set(cur_disp)
        self.cbo_lang.pack(side="left")

        def _on_lang_changed(e):
            sel_disp = self.cbo_lang.get()
            self.var_language.set(code_map.get(sel_disp, "auto"))

        self.cbo_lang.bind("<<ComboboxSelected>>", _on_lang_changed)

        sep0 = tk.Frame(self.content_container, bg="#313244", height=1)
        sep0.pack(fill="x", pady=10)

        # Folder Simpan
        lbl_dir = tk.Label(
            self.content_container,
            text=t("lbl_download_dir"),
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

        # Preferensi & Perilaku File
        lbl_name_opt = tk.Label(
            self.content_container,
            text="Preferensi & Perilaku Unduhan:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
            anchor="w",
        )
        lbl_name_opt.pack(fill="x", pady=(4, 6))

        chk_name = tk.Checkbutton(
            self.content_container,
            text="Gunakan Judul Asli Karya sebagai Nama File Audio (contoh: [RJ01673437] Judul)",
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

        # Pilihan Format Audio Output
        lbl_fmt_opt = tk.Label(
            self.content_container,
            text="Format Berkas Audio Output:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
            anchor="w",
        )
        lbl_fmt_opt.pack(fill="x", pady=(8, 2))

        fmt_box = tk.Frame(self.content_container, bg="#1e1e2e")
        fmt_box.pack(fill="x", pady=(0, 6))

        r_auto = tk.Radiobutton(
            fmt_box,
            text="Otomatis / Sesuai Sumber (Rekomendasi - Cepat & Asli, MP3 + CUE Sheet)",
            variable=self.var_audio_format,
            value="auto",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#50fa7b",
            anchor="w",
        )
        r_auto.pack(fill="x", pady=1)

        r_m4a = tk.Radiobutton(
            fmt_box,
            text="M4A (Apple AAC) - Satu Berkas Utuh, Bab Tertanam Tanpa File CUE",
            variable=self.var_audio_format,
            value="m4a",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#f8f8f2",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#f8f8f2",
            anchor="w",
        )
        r_m4a.pack(fill="x", pady=1)

        r_mp3 = tk.Radiobutton(
            fmt_box,
            text="MP3 (LAME CBR 320k) - Format Klasik Kompatibilitas Penuh",
            variable=self.var_audio_format,
            value="mp3",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#f8f8f2",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#f8f8f2",
            anchor="w",
        )
        r_mp3.pack(fill="x", pady=1)

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
            text="Koneksi paralel (Default: 16). Maks. 16 untuk server file tunggal (Aria2c), s/d 32 untuk multi-stream.",
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
            chan_tag = "Nightly" if ver.count(".") >= 3 else "Stable"
            if self.winfo_exists() and hasattr(self, "lbl_ytdlp_ver") and self.lbl_ytdlp_ver.winfo_exists():
                self.after(0, lambda: self.lbl_ytdlp_ver.config(text=f"Versi Terpasang: {ver} ({chan_tag})"))
                if not self.cfg.get("ytdlp_channel"):
                    self.var_ytdlp_channel.set(chan_tag.lower())

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
        self.lbl_ytdlp_status.config(text=f"Sedang memeriksa/memperbarui ({channel.title()})...", fg="#bd93f9")

        def run_upd():
            success, status_code, msg = update_ytdlp_engine(channel=channel)
            new_ver = get_ytdlp_version()
            chan_tag = "Nightly" if new_ver.count(".") >= 3 else "Stable"

            def done():
                self.btn_update_ytdlp.config(state="normal")
                self.lbl_ytdlp_ver.config(text=f"Versi Terpasang: {new_ver} ({chan_tag})")
                if success:
                    # Simpan preferensi channel yang aktif ke config
                    self.cfg["ytdlp_channel"] = channel
                    save_config(self.cfg)

                    if status_code == "already_latest":
                        self.lbl_ytdlp_status.config(text=f"Sudah versi terbaru ({new_ver})", fg="#8be9fd")
                        show_dark_info(
                            self,
                            "Sudah Versi Terbaru",
                            f"yt-dlp sudah menggunakan versi terbaru ({new_ver}) pada channel {channel.title()}.\n\nTidak ada pembaruan baru yang diperlukan.",
                        )
                    else:
                        self.lbl_ytdlp_status.config(text=f"Sukses! Versi {new_ver}", fg="#50fa7b")
                        show_dark_info(
                            self,
                            "Pembaruan Selesai",
                            f"Berhasil memperbarui yt-dlp ke versi {new_ver} (Channel: {channel.title()}).",
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

    # ==================== ACTIONS: CLEAR CACHE & HISTORY ====================
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
            text=t("app_version"),
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#bd93f9",
            anchor="w",
        )
        lbl_version.pack(fill="x")

        lbl_desc = tk.Label(
            card_about,
            text=t("lbl_about_desc"),
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
            show_dark_warning(self, t("msg_error_title"), "Lokasi folder download tidak boleh kosong.")
            return

        lang_val = self.var_language.get()
        self.cfg["language"] = lang_val
        self.cfg["download_dir"] = new_dir
        self.cfg["use_detailed_filename"] = self.var_detailed_name.get()
        self.cfg["notify_popup"] = self.var_notify_popup.get()
        self.cfg["auto_clipboard"] = self.var_auto_clipboard.get()
        self.cfg["connections"] = max(1, min(32, self.var_connections.get()))
        self.cfg["ytdlp_channel"] = self.var_ytdlp_channel.get()
        self.cfg["audio_format"] = self.var_audio_format.get()

        save_config(self.cfg)
        set_active_language(lang_val)
        set_download_dir(new_dir)
        set_audio_format(self.var_audio_format.get())

        # Sinkronisasi ke GUI utama
        self.parent.opt_detailed_name.set(self.cfg["use_detailed_filename"])
        if hasattr(self.parent, "var_auto_clipboard"):
            self.parent.var_auto_clipboard.set(self.cfg["auto_clipboard"])
        self.parent.config = dict(self.cfg)
        self.parent.lbl_current_dir.config(text=t("lbl_save_location", path=os.path.abspath(new_dir)))
        if hasattr(self.parent, "_refresh_playlist_view"):
            self.parent._refresh_playlist_view()

        # Dynamic In-Place UI Re-render seketika!
        if hasattr(self.parent, "retranslate_ui"):
            self.parent.retranslate_ui()

        show_dark_info(self, t("msg_info_title"), t("msg_settings_saved"))
        self._on_dialog_close()

    def _on_dialog_close(self):
        if hasattr(self, "parent") and self.parent:
            self.parent._settings_dialog = None
        self.destroy()
