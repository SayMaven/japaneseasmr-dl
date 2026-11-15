import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from PIL import Image, ImageTk

from config_manager import get_download_dir, load_config
from i18n import t
from ui.constants import APP_VERSION
from ui.dialogs import apply_dark_titlebar
from ui.downloader import DownloadWorkerMixin
from ui.icons import get_icon
from ui.player_engine import NativeMFPlayer
from ui.tab_history import HistoryTabMixin
from ui.tab_player import PlayerTabMixin
from ui.tab_queue import QueueTabMixin
from ui.tab_settings import SettingsTabMixin
from ui.theme import (
    ACCENT_PRIMARY,
    BG_SIDEBAR,
    BG_VIEWPORT,
    BORDER_ACTIVE,
    BORDER_SUBTLE,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CAPTION,
    FONT_TITLE,
    RADIUS_BUTTON,
    RADIUS_CARD,
    RADIUS_SIDEBAR,
    SPACE_XS,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SURFACE_CARD,
    SURFACE_ELEVATED,
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
    SettingsTabMixin,
    DownloadWorkerMixin,
):
    """Primary desktop GUI application for JapaneseASMR Downloader and Player."""
    def __init__(self):
        # Set explicit AppUserModelID so Windows Taskbar associates the custom icon
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SayMaven.JapaneseASMR.Downloader.App")
            except Exception:
                pass

        # Initialize CustomTkinter with custom Tokyo Night theme
        ctk.set_appearance_mode("dark")
        theme_json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "theme",
            "tokyo_night.json",
        )
        if os.path.exists(theme_json_path):
            try:
                ctk.set_default_color_theme(theme_json_path)
            except Exception:
                ctk.set_default_color_theme("blue")
        else:
            ctk.set_default_color_theme("blue")

        super().__init__()
        self.title(f"JapaneseASMR Downloader & Player - v{APP_VERSION}")
        # Laptop-friendly responsive window geometry (default 1360x800, minsize 1120x660)
        self.geometry("1360x800")
        self.minsize(1120, 660)
        self.configure(fg_color=BG_VIEWPORT)
        apply_dark_titlebar(self)

        # Configuration and state tracking
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

        # Audio player state (Windows Native MCI & Media Foundation engines)
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

        # Set window and taskbar icons
        self._settings_dialog = None
        self._setup_app_icons()

        self._init_styles()
        self._build_ui()
        self.retranslate_ui()
        self._load_history_view()
        self._refresh_playlist_view()

        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        # Re-apply taskbar icon once window frame is fully initialized by Windows DWM
        if sys.platform == "win32":
            self._icon_after_id = self.after(150, self._apply_win32_taskbar_icon)
        else:
            self._icon_after_id = None

    def _setup_app_icons(self):
        candidate_roots = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            getattr(sys, "_MEIPASS", ""),
        ]

        self._icon_ico_path = None
        self._icon_png_path = None

        for root in candidate_roots:
            if not root:
                continue
            ico_cand = os.path.join(root, "assets", "icon.ico")
            png_cand = os.path.join(root, "assets", "icon.png")
            if os.path.exists(ico_cand) and not self._icon_ico_path:
                self._icon_ico_path = ico_cand
            if os.path.exists(png_cand) and not self._icon_png_path:
                self._icon_png_path = png_cand

        if self._icon_ico_path:
            try:
                self.iconbitmap(default=self._icon_ico_path)
            except Exception:
                pass

        if self._icon_png_path:
            try:
                img = Image.open(self._icon_png_path)
                self._window_icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._window_icon_photo)
            except Exception:
                pass

    def _apply_win32_taskbar_icon(self):
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
        # Master layout: Left navigation sidebar and right content viewport
        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=RADIUS_SIDEBAR,
            fg_color=BG_SIDEBAR,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # 1. Branding header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=SPACE_LG, pady=(SPACE_LG + 2, SPACE_LG))

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
            text=f"Downloader & Player • v{APP_VERSION}",
            font=FONT_CAPTION,
            text_color=ACCENT_PRIMARY,
            anchor="w",
        )
        self.lbl_brand_sub.pack(fill="x", pady=(2, 0))

        # 2. Vertical 4-tab navigation (vector icons)
        self.lbl_nav_header = ctk.CTkLabel(
            self.sidebar,
            text=t("nav_main_header"),
            font=(FONT_BODY[0], 8, "bold"),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.lbl_nav_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_SM, SPACE_XS))

        self.btn_nav_queue = ctk.CTkButton(
            self.sidebar,
            text=f"  {t('tab_queue')}",
            image=get_icon("download", size=(18, 18)),
            font=FONT_BODY_BOLD,
            anchor="w",
            corner_radius=RADIUS_BUTTON,
            height=40,
            fg_color=ACCENT_PRIMARY,
            text_color="#ffffff",
            command=lambda: self._select_page("queue"),
        )
        self.btn_nav_queue.pack(fill="x", padx=SPACE_MD, pady=3)

        self.btn_nav_history = ctk.CTkButton(
            self.sidebar,
            text=f"  {t('tab_history')}",
            image=get_icon("history", size=(18, 18)),
            font=FONT_BODY_BOLD,
            anchor="w",
            corner_radius=RADIUS_BUTTON,
            height=40,
            fg_color="transparent",
            text_color=TEXT_SECONDARY,
            hover_color=SURFACE_ELEVATED,
            command=lambda: self._select_page("history"),
        )
        self.btn_nav_history.pack(fill="x", padx=SPACE_MD, pady=3)

        self.btn_nav_player = ctk.CTkButton(
            self.sidebar,
            text=f"  {t('tab_player')}",
            image=get_icon("music", size=(18, 18)),
            font=FONT_BODY_BOLD,
            anchor="w",
            corner_radius=RADIUS_BUTTON,
            height=40,
            fg_color="transparent",
            text_color=TEXT_SECONDARY,
            hover_color=SURFACE_ELEVATED,
            command=lambda: self._select_page("player"),
        )
        self.btn_nav_player.pack(fill="x", padx=SPACE_MD, pady=3)

        self.btn_nav_settings = ctk.CTkButton(
            self.sidebar,
            text=f"  {t('btn_settings')}",
            image=get_icon("settings", size=(18, 18)),
            font=FONT_BODY_BOLD,
            anchor="w",
            corner_radius=RADIUS_BUTTON,
            height=40,
            fg_color="transparent",
            text_color=TEXT_SECONDARY,
            hover_color=SURFACE_ELEVATED,
            command=lambda: self._select_page("settings"),
        )
        self.btn_nav_settings.pack(fill="x", padx=SPACE_MD, pady=3)

        # Vertical flexible spacer
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # 3. Sidebar footer (active storage directory status)
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(fill="x", padx=SPACE_MD, pady=(0, SPACE_LG), side="bottom")

        dir_card = ctk.CTkFrame(
            footer_frame,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        dir_card.pack(fill="x")

        dir_inner = ctk.CTkFrame(dir_card, fg_color="transparent")
        dir_inner.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)

        cur_dir = os.path.abspath(get_download_dir())
        self.lbl_current_dir = ctk.CTkLabel(
            dir_inner,
            text=t("lbl_save_location", path=cur_dir),
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=190,
            justify="left",
        )
        self.lbl_current_dir.pack(fill="x", pady=(0, 6))

        self.btn_open_folder = ctk.CTkButton(
            dir_inner,
            text=f" {t('btn_open_folder')}",
            image=get_icon("folder", size=(14, 14)),
            font=FONT_CAPTION,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=28,
            anchor="center",
            command=self._open_downloads_folder,
        )
        self.btn_open_folder.pack(fill="x", pady=(0, 4))

        self.btn_change_dir = ctk.CTkButton(
            dir_inner,
            text=f" {t('btn_change_dir')}",
            image=get_icon("folder", size=(14, 14)),
            font=FONT_CAPTION,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=28,
            anchor="center",
            command=self._change_download_dir,
        )
        self.btn_change_dir.pack(fill="x")

        # 4. Primary content viewport
        self.viewport = ctk.CTkFrame(self, fg_color=BG_VIEWPORT, corner_radius=0)
        self.viewport.pack(side="right", fill="both", expand=True)

        self.tab_queue = ctk.CTkFrame(self.viewport, fg_color="transparent")
        self.tab_history = ctk.CTkFrame(self.viewport, fg_color="transparent")
        self.tab_player = ctk.CTkFrame(self.viewport, fg_color="transparent")
        self.tab_settings = ctk.CTkFrame(self.viewport, fg_color="transparent")

        self._build_queue_tab()
        self._build_history_tab()
        self._build_player_tab()
        self._build_settings_tab()

        # Compatibility notebook shim
        self.current_page = "queue"
        class _NotebookShim:
            def __init__(shim_self, app):
                shim_self.app = app
            def select(shim_self, tab=None):
                if tab is not None:
                    shim_self.app._select_page(tab)
                return shim_self.app.current_page
        self.notebook = _NotebookShim(self)

        # Default to queue tab and lock initial geometry
        self._select_page("queue")
        self.geometry("1360x800")

    def _select_page(self, page):
        """Handle instant switching between viewport tabs."""
        tabs = [
            ("queue", self.tab_queue, self.btn_nav_queue),
            ("history", self.tab_history, self.btn_nav_history),
            ("player", self.tab_player, self.btn_nav_player),
            ("settings", self.tab_settings, self.btn_nav_settings),
        ]

        target_name = None
        for name, frame, btn in tabs:
            if page == name or page == frame:
                target_name = name
                break

        if not target_name:
            target_name = "queue"

        self.current_page = target_name

        for name, frame, btn in tabs:
            if name == target_name:
                frame.pack(fill="both", expand=True, padx=SPACE_LG, pady=SPACE_LG)
                btn.configure(fg_color=ACCENT_PRIMARY, text_color="#ffffff")
            else:
                frame.pack_forget()
                btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY)

        if target_name == "history":
            self._load_history_view()
        elif target_name == "player":
            self._refresh_playlist_view()
        elif target_name == "settings":
            if hasattr(self, "var_download_dir"):
                cur_d = os.path.abspath(get_download_dir())
                self.var_download_dir.set(cur_d)
                if hasattr(self, "entry_set_dir") and self.entry_set_dir.winfo_exists():
                    self.entry_set_dir.delete(0, "end")
                    self.entry_set_dir.insert(0, cur_d)

    def open_settings_dialog(self):
        """Navigate directly to the Settings Tab in the primary viewport."""
        self._select_page("settings")

    def sync_download_directory(self, new_dir):
        """Synchronize active download directory across config, footer labels, settings input, and player playlist."""
        if not new_dir:
            return
        abs_d = os.path.abspath(new_dir)
        from config_manager import set_download_dir
        set_download_dir(abs_d)
        if hasattr(self, "lbl_current_dir") and self.lbl_current_dir.winfo_exists():
            self.lbl_current_dir.configure(text=t("lbl_save_location", path=abs_d))
        if hasattr(self, "var_download_dir"):
            self.var_download_dir.set(abs_d)
        if hasattr(self, "entry_set_dir") and self.entry_set_dir.winfo_exists():
            self.entry_set_dir.delete(0, "end")
            self.entry_set_dir.insert(0, abs_d)
        if hasattr(self, "_refresh_playlist_view"):
            self._refresh_playlist_view()

    def retranslate_ui(self):
        """Apply active language translations across all GUI elements in real time."""
        self.title(f"{t('app_title')} - v{APP_VERSION}")

        if hasattr(self, "lbl_nav_header"):
            self.lbl_nav_header.configure(text=t("nav_main_header"))
        if hasattr(self, "btn_nav_queue"):
            self.btn_nav_queue.configure(text=f"  {t('tab_queue')}")
        if hasattr(self, "btn_nav_history"):
            self.btn_nav_history.configure(text=f"  {t('tab_history')}")
        if hasattr(self, "btn_nav_player"):
            self.btn_nav_player.configure(text=f"  {t('tab_player')}")
        if hasattr(self, "btn_nav_settings"):
            self.btn_nav_settings.configure(text=f"  {t('btn_settings')}")

        if hasattr(self, "btn_open_folder"):
            self.btn_open_folder.configure(text=f" {t('btn_open_folder')}")
        if hasattr(self, "btn_change_dir"):
            self.btn_change_dir.configure(text=f" {t('btn_change_dir')}")
        if hasattr(self, "lbl_current_dir"):
            cur_dir = os.path.abspath(get_download_dir())
            self.lbl_current_dir.configure(text=t("lbl_save_location", path=cur_dir))

        # Queue Tab
        if hasattr(self, "lbl_input_title"):
            self.lbl_input_title.configure(text=t("lbl_input_group"))
        if hasattr(self, "paste_btn"):
            self.paste_btn.configure(text=f" {t('btn_paste')}")
        if hasattr(self, "add_btn"):
            self.add_btn.configure(text=f" {t('btn_add_queue')}")
        if hasattr(self, "chk_name"):
            self.chk_name.configure(text=t("chk_detailed_name"))
        if hasattr(self, "lbl_queue_heading"):
            self.lbl_queue_heading.configure(text=t("tab_queue"))
        if hasattr(self, "start_btn") and not self.is_downloading:
            self.start_btn.configure(text=f" {t('btn_start_download')}")
        if hasattr(self, "stop_btn"):
            self.stop_btn.configure(text=f" {t('btn_stop_download')}")
        if hasattr(self, "clear_btn"):
            self.clear_btn.configure(text=f" {t('btn_clear_queue')}")
        if hasattr(self, "lbl_progress_status") and not self.is_downloading:
            self.lbl_progress_status.configure(text=f"{t('col_status')}: {t('status_ready')}")
        if hasattr(self, "lbl_log_header"):
            self.lbl_log_header.configure(text=t("lbl_log_header"))
        if hasattr(self, "lbl_preview_title"):
            self.lbl_preview_title.configure(text=t("lbl_preview_title"))

        if hasattr(self, "tree"):
            self.tree.heading("no", text="#")
            self.tree.heading("rjid", text=t("col_rjid"))
            self.tree.heading("title", text=t("col_title"))
            self.tree.heading("status", text=t("col_status"))

        # History Tab
        if hasattr(self, "lbl_h_header"):
            self.lbl_h_header.configure(text=t("tab_history"))
        if hasattr(self, "refresh_hist_btn"):
            self.refresh_hist_btn.configure(text=f" {t('btn_refresh_playlist')}")
        if hasattr(self, "btn_play_file"):
            self.btn_play_file.configure(text=f" {t('btn_play_selected')}")
        if hasattr(self, "btn_del_history"):
            self.btn_del_history.configure(text=f" {t('btn_clear_history')}")
        if hasattr(self, "hist_tree"):
            self.hist_tree.heading("date", text=t("col_hist_date"))
            self.hist_tree.heading("rjid", text=t("col_hist_rjid"))
            self.hist_tree.heading("title", text=t("col_hist_title"))
            self.hist_tree.heading("size", text=t("col_play_duration"))

        # Player Tab
        if hasattr(self, "lbl_p_title"):
            self.lbl_p_title.configure(text=f"{t('lbl_playlist')} ({len(self.playlist_items)})")
        if hasattr(self, "refresh_p_btn"):
            self.refresh_p_btn.configure(text=f" {t('btn_refresh_playlist')}")
        if hasattr(self, "lbl_now_playing_title"):
            self.lbl_now_playing_title.configure(text=t("lbl_playlist"))
        if hasattr(self, "lbl_chap_title"):
            self.lbl_chap_title.configure(text=t("lbl_chapters"))
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

        # Settings Tab
        if hasattr(self, "retranslate_settings_tab"):
            self.retranslate_settings_tab()

    def _open_downloads_folder(self):
        cur_dir = os.path.abspath(get_download_dir())
        os.makedirs(cur_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(cur_dir)

    def _change_download_dir(self):
        from tkinter import filedialog
        cur_dir = os.path.abspath(get_download_dir())
        d = filedialog.askdirectory(initialdir=cur_dir)
        if d:
            self.sync_download_directory(d)

    def _on_app_close(self):
        """Menutup seluruh aplikasi dan mematikan background player secara bersih."""
        if hasattr(self, "_icon_after_id") and self._icon_after_id:
            try:
                self.after_cancel(self._icon_after_id)
            except Exception:
                pass
        self._player_stop()
        if hasattr(self, "mf_player"):
            try:
                self.mf_player.close()
            except Exception:
                pass
        self.destroy()
