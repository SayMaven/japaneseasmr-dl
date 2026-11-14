import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from PIL import Image, ImageTk

from config_manager import get_download_dir, load_config
from i18n import t
from ui.dialogs import apply_dark_titlebar
from ui.downloader import DownloadWorkerMixin
from ui.player_engine import NativeMFPlayer
from ui.settings_dialog import SettingsDialog
from ui.tab_history import HistoryTabMixin
from ui.tab_player import PlayerTabMixin
from ui.tab_queue import QueueTabMixin
from ui.theme import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BG_APP,
    BORDER_ACTIVE,
    BORDER_SUBTLE,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CAPTION,
    FONT_SUBTITLE,
    FONT_TITLE,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    STATUS_DANGER,
    STATUS_INFO,
    STATUS_SUCCESS,
    SURFACE_CARD,
    SURFACE_ELEVATED,
    SURFACE_INPUT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    configure_ttk_dark_theme,
)


class JapaneseASMRApp(
    ctk.CTk,
    QueueTabMixin,
    HistoryTabMixin,
    PlayerTabMixin,
    DownloadWorkerMixin,
):
    """Aplikasi Desktop Utama JapaneseASMR Downloader & Audio Player."""
    def __init__(self):
        # Set Explicit AppUserModelID agar Taskbar Windows menampilkan ikon custom
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SayMaven.JapaneseASMR.Downloader.App")
            except Exception:
                pass

        # Inisialisasi CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        super().__init__()
        self.title("JapaneseASMR Downloader & Audio Player")
        self.geometry("1160x840")
        self.minsize(980, 720)
        self.configure(fg_color=BG_APP)
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
        self.var_auto_clipboard = tk.BooleanVar(value=self.config.get("auto_clipboard", True))
        self._syncing_chaps = set()

        # Audio Player State (Windows Native MCI & Media Foundation Engine)
        self.mf_player = NativeMFPlayer()
        self.use_mf_player = False
        self.current_playing_file = None
        self.current_playing_meta = {}
        self.is_playing = False
        self.is_paused = False
        self.player_duration_ms = 0
        self.mci_raw_duration_ms = 0
        self.is_user_dragging_slider = False
        self.is_looping = False
        self.playlist_items = []
        self.current_track_index = -1
        self.player_preview_image = None
        self.current_chapters = []
        self.active_chapter_index = -1
        self._chapters_cache = {}

        # Set Window & Taskbar Icon
        self._settings_dialog = None
        self._setup_app_icons()

        self._init_styles()
        self._build_ui()
        self.retranslate_ui()
        self._load_history_view()
        self._refresh_playlist_view()

        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        # Re-apply icon setelah window di-render sempurna oleh Windows DWM
        if sys.platform == "win32":
            self.after(150, self._apply_win32_taskbar_icon)

    def _setup_app_icons(self):
        candidate_roots = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
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

        # Pasang via Tkinter standard
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
        style = ttk.Style(self)
        configure_ttk_dark_theme(style)

    def _build_ui(self):
        # Master Layout: Sidebar Navigasi Kiri (Opsi A) + Content Viewport Kanan
        self.sidebar = ctk.CTkFrame(
            self,
            width=230,
            corner_radius=0,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # 1. Branding Header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(18, 16))

        self.lbl_brand = ctk.CTkLabel(
            brand_frame,
            text="JapaneseASMR",
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_brand.pack(fill="x")

        self.lbl_brand_sub = ctk.CTkLabel(
            brand_frame,
            text="Downloader & Player • v1.1.1",
            font=FONT_CAPTION,
            text_color=ACCENT_PRIMARY,
            anchor="w",
        )
        self.lbl_brand_sub.pack(fill="x")

        # 2. Navigasi Tab Utama
        nav_header = ctk.CTkLabel(
            self.sidebar,
            text="NAVIGASI UTAMA",
            font=("Segoe UI", 8, "bold"),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        nav_header.pack(fill="x", padx=16, pady=(8, 4))

        self.btn_nav_queue = ctk.CTkButton(
            self.sidebar,
            text=f"  📥  {t('tab_queue')}",
            font=FONT_BODY_BOLD,
            anchor="w",
            corner_radius=RADIUS_MD,
            height=40,
            command=lambda: self._select_page("queue"),
        )
        self.btn_nav_queue.pack(fill="x", padx=12, pady=3)

        self.btn_nav_history = ctk.CTkButton(
            self.sidebar,
            text=f"  📜  {t('tab_history')}",
            font=FONT_BODY_BOLD,
            anchor="w",
            corner_radius=RADIUS_MD,
            height=40,
            command=lambda: self._select_page("history"),
        )
        self.btn_nav_history.pack(fill="x", padx=12, pady=3)

        self.btn_nav_player = ctk.CTkButton(
            self.sidebar,
            text=f"  🎵  {t('tab_player')}",
            font=FONT_BODY_BOLD,
            anchor="w",
            corner_radius=RADIUS_MD,
            height=40,
            command=lambda: self._select_page("player"),
        )
        self.btn_nav_player.pack(fill="x", padx=12, pady=3)

        # Spacer di tengah
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # 3. Sidebar Footer (Status Engine, Lokasi & Pengaturan)
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(fill="x", padx=12, pady=(0, 16), side="bottom")

        # Folder Info Box
        dir_card = ctk.CTkFrame(footer_frame, corner_radius=RADIUS_MD, fg_color=SURFACE_INPUT, border_width=1, border_color=BORDER_SUBTLE)
        dir_card.pack(fill="x", pady=(0, 10))

        dir_inner = ctk.CTkFrame(dir_card, fg_color="transparent")
        dir_inner.pack(fill="x", padx=10, pady=8)

        cur_dir = os.path.abspath(get_download_dir())
        self.lbl_current_dir = ctk.CTkLabel(
            dir_inner,
            text=f"📁 {t('lbl_save_location', path=cur_dir)}",
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=180,
            justify="left",
        )
        self.lbl_current_dir.pack(fill="x", pady=(0, 6))

        btn_dir_row = ctk.CTkFrame(dir_inner, fg_color="transparent")
        btn_dir_row.pack(fill="x")

        self.btn_open_folder = ctk.CTkButton(
            btn_dir_row,
            text="Buka",
            font=FONT_CAPTION,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_SM,
            height=26,
            width=80,
            command=self._open_downloads_folder,
        )
        self.btn_open_folder.pack(side="left", padx=(0, 4))

        self.btn_change_dir = ctk.CTkButton(
            btn_dir_row,
            text="Ganti",
            font=FONT_CAPTION,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_SM,
            height=26,
            width=80,
            command=self._change_download_dir,
        )
        self.btn_change_dir.pack(side="left")

        # Tombol Pengaturan Modern
        self.btn_settings = ctk.CTkButton(
            footer_frame,
            text=f"⚙  {t('btn_settings')}",
            font=FONT_BODY_BOLD,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_MD,
            height=36,
            command=self._open_settings_dialog,
        )
        self.btn_settings.pack(fill="x")

        # 4. Viewport Konten Utama (Kanan)
        self.viewport = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        self.viewport.pack(side="right", fill="both", expand=True)

        self.tab_queue = ctk.CTkFrame(self.viewport, fg_color="transparent")
        self.tab_history = ctk.CTkFrame(self.viewport, fg_color="transparent")
        self.tab_player = ctk.CTkFrame(self.viewport, fg_color="transparent")

        self._build_queue_tab()
        self._build_history_tab()
        self._build_player_tab()

        # Notebook shim
        self.current_page = "queue"
        class _NotebookShim:
            def __init__(shim_self, app):
                shim_self.app = app
            def select(shim_self, tab=None):
                if tab is not None:
                    shim_self.app._select_page(tab)
                return shim_self.app.current_page
        self.notebook = _NotebookShim(self)

        # Default ke tab antrean
        self._select_page("queue")

    def _select_page(self, page):
        if page in ("queue", self.tab_queue):
            self.current_page = "queue"
            self.tab_history.pack_forget()
            self.tab_player.pack_forget()
            self.tab_queue.pack(fill="both", expand=True, padx=16, pady=16)

            self.btn_nav_queue.configure(fg_color=ACCENT_PRIMARY, text_color="#ffffff")
            self.btn_nav_history.configure(fg_color="transparent", text_color=TEXT_SECONDARY)
            self.btn_nav_player.configure(fg_color="transparent", text_color=TEXT_SECONDARY)

        elif page in ("history", self.tab_history):
            self.current_page = "history"
            self.tab_queue.pack_forget()
            self.tab_player.pack_forget()
            self.tab_history.pack(fill="both", expand=True, padx=16, pady=16)

            self.btn_nav_queue.configure(fg_color="transparent", text_color=TEXT_SECONDARY)
            self.btn_nav_history.configure(fg_color=ACCENT_PRIMARY, text_color="#ffffff")
            self.btn_nav_player.configure(fg_color="transparent", text_color=TEXT_SECONDARY)
            self._load_history_view()

        elif page in ("player", self.tab_player):
            self.current_page = "player"
            self.tab_queue.pack_forget()
            self.tab_history.pack_forget()
            self.tab_player.pack(fill="both", expand=True, padx=16, pady=16)

            self.btn_nav_queue.configure(fg_color="transparent", text_color=TEXT_SECONDARY)
            self.btn_nav_history.configure(fg_color="transparent", text_color=TEXT_SECONDARY)
            self.btn_nav_player.configure(fg_color=ACCENT_PRIMARY, text_color="#ffffff")
            self._refresh_playlist_view()

    def retranslate_ui(self):
        """Menerapkan terjemahan bahasa aktif ke seluruh elemen GUI seketika."""
        self.title(f"{t('app_title')} - v1.1.1")

        if hasattr(self, "btn_nav_queue"):
            self.btn_nav_queue.configure(text=f"  📥  {t('tab_queue')}")
        if hasattr(self, "btn_nav_history"):
            self.btn_nav_history.configure(text=f"  📜  {t('tab_history')}")
        if hasattr(self, "btn_nav_player"):
            self.btn_nav_player.configure(text=f"  🎵  {t('tab_player')}")

        if hasattr(self, "btn_settings"):
            self.btn_settings.configure(text=f"⚙  {t('btn_settings')}")
        if hasattr(self, "btn_open_folder"):
            self.btn_open_folder.configure(text=t("btn_open_folder"))
        if hasattr(self, "btn_change_dir"):
            self.btn_change_dir.configure(text=t("btn_change_dir"))
        if hasattr(self, "lbl_current_dir"):
            cur_dir = os.path.abspath(get_download_dir())
            self.lbl_current_dir.configure(text=f"📁 {t('lbl_save_location', path=cur_dir)}")

        # Queue Tab
        if hasattr(self, "lbl_input_title"):
            self.lbl_input_title.configure(text=t("lbl_input_group"))
        if hasattr(self, "paste_btn"):
            self.paste_btn.configure(text=f"📋 {t('btn_paste')}")
        if hasattr(self, "add_btn"):
            self.add_btn.configure(text=f"➕ {t('btn_add_queue')}")
        if hasattr(self, "chk_name"):
            self.chk_name.configure(text=t("chk_detailed_name"))
        if hasattr(self, "lbl_queue_heading"):
            self.lbl_queue_heading.configure(text=t("tab_queue"))
        if hasattr(self, "start_btn") and not self.is_downloading:
            self.start_btn.configure(text=f"▶ {t('btn_start_download')}")
        if hasattr(self, "stop_btn"):
            self.stop_btn.configure(text=f"⏹ {t('btn_stop_download')}")
        if hasattr(self, "clear_btn"):
            self.clear_btn.configure(text=f"🗑 {t('btn_clear_queue')}")
        if hasattr(self, "lbl_progress_status") and not self.is_downloading:
            self.lbl_progress_status.configure(text=f"{t('col_status')}: {t('status_ready')}")
        if hasattr(self, "lbl_log_header"):
            self.lbl_log_header.configure(text=f"💻 {t('lbl_log_header')}")
        if hasattr(self, "lbl_preview_title"):
            self.lbl_preview_title.configure(text=f"🖼 {t('lbl_preview_title')}")

        if hasattr(self, "tree"):
            self.tree.heading("no", text="#")
            self.tree.heading("rjid", text=t("col_rjid"))
            self.tree.heading("title", text=t("col_title"))
            self.tree.heading("status", text=t("col_status"))

        # History Tab
        if hasattr(self, "lbl_h_header"):
            self.lbl_h_header.configure(text=f"📜 {t('tab_history')}")
        if hasattr(self, "refresh_hist_btn"):
            self.refresh_hist_btn.configure(text=f"🔄 {t('btn_refresh_playlist')}")
        if hasattr(self, "btn_play_file"):
            self.btn_play_file.configure(text=f"▶ {t('btn_play_selected')}")
        if hasattr(self, "btn_del_history"):
            self.btn_del_history.configure(text=f"🗑 {t('btn_clear_history')}")
        if hasattr(self, "hist_tree"):
            self.hist_tree.heading("date", text=t("col_hist_date"))
            self.hist_tree.heading("rjid", text=t("col_hist_rjid"))
            self.hist_tree.heading("title", text=t("col_hist_title"))
            self.hist_tree.heading("size", text=t("col_play_duration"))

        # Player Tab
        if hasattr(self, "lbl_p_title"):
            self.lbl_p_title.configure(text=f"🎵 {t('lbl_playlist')} ({len(self.playlist_items)})")
        if hasattr(self, "refresh_p_btn"):
            self.refresh_p_btn.configure(text=f"🔄 {t('btn_refresh_playlist')}")
        if hasattr(self, "lbl_now_playing_title"):
            self.lbl_now_playing_title.configure(text=f"🎧 {t('lbl_playlist')}")
        if hasattr(self, "lbl_chap_title"):
            self.lbl_chap_title.configure(text=f"📑 {t('lbl_chapters')}")
        if hasattr(self, "btn_play_pause") and not self.is_playing:
            self.btn_play_pause.configure(text="▶")
        if hasattr(self, "player_tree"):
            self.player_tree.heading("rjid", text=t("col_rjid"))
            self.player_tree.heading("title", text=t("col_play_title"))
            self.player_tree.heading("cv", text=t("col_hist_cv"))
            self.player_tree.heading("size", text=t("col_play_duration"))
        if hasattr(self, "chap_tree"):
            self.chap_tree.heading("time", text=t("col_chap_time"))
            self.chap_tree.heading("title", text=t("col_chap_title"))

        # Detail rows
        for lbl, key in getattr(self, "_info_rows", []):
            if key:
                lbl.configure(text=f"{t(key)}:")

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
        if hasattr(self, "mf_player"):
            try:
                self.mf_player.close()
            except Exception:
                pass
        self.destroy()
