import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk

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


class JapaneseASMRApp(
    tk.Tk,
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

        self.title_label = tk.Label(
            header_frame,
            text="JapaneseASMR Downloader",
            font=("Segoe UI", 15, "bold"),
            bg="#282a36",
            fg="#50fa7b",
        )
        self.title_label.pack(side="left", padx=20, pady=12)

        # Directory Selector, Open Folder, & Settings Buttons
        dir_controls = tk.Frame(header_frame, bg="#282a36")
        dir_controls.pack(side="right", padx=20, pady=10)

        self.btn_change_dir = tk.Button(
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
        self.btn_change_dir.pack(side="left", padx=(0, 8))

        self.btn_open_folder = tk.Button(
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
        self.btn_open_folder.pack(side="left", padx=(0, 8))

        self.btn_settings = tk.Button(
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
        self.btn_settings.pack(side="left")

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

    def retranslate_ui(self):
        """Menerapkan terjemahan bahasa aktif ke seluruh elemen GUI seketika (in-place)."""
        # 1. Main Window Title
        self.title(f"{t('app_title')} - v1.1.1")

        # 2. Header
        if hasattr(self, "title_label"):
            self.title_label.config(text=t("app_title"))
        if hasattr(self, "btn_change_dir"):
            self.btn_change_dir.config(text=t("btn_change_dir"))
        if hasattr(self, "btn_open_folder"):
            self.btn_open_folder.config(text=t("btn_open_folder"))
        if hasattr(self, "btn_settings"):
            self.btn_settings.config(text=t("btn_settings"))
        if hasattr(self, "lbl_current_dir"):
            cur_dir = os.path.abspath(get_download_dir())
            self.lbl_current_dir.config(text=t("lbl_save_location", path=cur_dir))

        # 3. Notebook Tabs
        if hasattr(self, "notebook") and hasattr(self, "tab_queue"):
            self.notebook.tab(self.tab_queue, text=f" 📥 {t('tab_queue')} ")
            self.notebook.tab(self.tab_history, text=f" 📜 {t('tab_history')} ")
            self.notebook.tab(self.tab_player, text=f" 🎵 {t('tab_player')} ")

        # 4. Tab 1: Queue
        if hasattr(self, "input_frame"):
            self.input_frame.config(text=f" {t('lbl_input_group')} ")
        if hasattr(self, "paste_btn"):
            self.paste_btn.config(text=t("btn_paste"))
        if hasattr(self, "add_btn"):
            self.add_btn.config(text=t("btn_add_queue"))
        if hasattr(self, "chk_name"):
            self.chk_name.config(text=t("chk_detailed_name"))
        if hasattr(self, "queue_frame"):
            self.queue_frame.config(text=f" {t('tab_queue')} ")
        if hasattr(self, "tree"):
            self.tree.heading("no", text="#")
            self.tree.heading("rjid", text=t("col_rjid"))
            self.tree.heading("title", text=t("col_title"))
            self.tree.heading("status", text=t("col_status"))
        if hasattr(self, "start_btn") and not self.is_downloading:
            self.start_btn.config(text=t("btn_start_download"))
        if hasattr(self, "stop_btn"):
            self.stop_btn.config(text=t("btn_stop_download"))
        if hasattr(self, "clear_btn"):
            self.clear_btn.config(text=t("btn_clear_queue"))
        if hasattr(self, "lbl_progress_status") and not self.is_downloading:
            self.lbl_progress_status.config(text=f"{t('col_status')}: {t('status_ready')}")
        if hasattr(self, "log_frame"):
            self.log_frame.config(text=f" {t('lbl_log_header')} ")
        if hasattr(self, "right_panel"):
            self.right_panel.config(text=f" {t('lbl_preview_title')} ")

        # 5. Tab 2: History
        if hasattr(self, "lbl_h_header"):
            self.lbl_h_header.config(text=t("tab_history"))
        if hasattr(self, "refresh_hist_btn"):
            self.refresh_hist_btn.config(text=t("btn_refresh_playlist"))
        if hasattr(self, "hist_tree"):
            self.hist_tree.heading("date", text=t("col_hist_date"))
            self.hist_tree.heading("rjid", text=t("col_hist_rjid"))
            self.hist_tree.heading("title", text=t("col_hist_title"))
            self.hist_tree.heading("size", text=t("col_play_duration"))
        if hasattr(self, "right_h_panel"):
            self.right_h_panel.config(text=f" {t('lbl_preview_title')} ")
        if hasattr(self, "btn_play_file"):
            self.btn_play_file.config(text=t("btn_play_selected"))
        if hasattr(self, "btn_del_history"):
            self.btn_del_history.config(text=t("btn_clear_history"))

        # 6. Tab 3: Player
        if hasattr(self, "lbl_p_title"):
            self.lbl_p_title.config(text=t("lbl_playlist"))
        if hasattr(self, "refresh_p_btn"):
            self.refresh_p_btn.config(text=t("btn_refresh_playlist"))
        if hasattr(self, "player_tree"):
            self.player_tree.heading("rjid", text=t("col_rjid"))
            self.player_tree.heading("title", text=t("col_play_title"))
            self.player_tree.heading("cv", text=t("col_hist_cv"))
            self.player_tree.heading("size", text=t("col_play_duration"))
        if hasattr(self, "right_p_panel"):
            self.right_p_panel.config(text=f" {t('lbl_playlist')} ")
        if hasattr(self, "btn_play_pause") and not self.is_playing:
            self.btn_play_pause.config(text=f"▶ {t('btn_play')}")
        if hasattr(self, "lbl_vol_icon"):
            self.lbl_vol_icon.config(text="Volume:")
        if hasattr(self, "chap_frame"):
            self.chap_frame.config(text=f" 📑 {t('lbl_chapters')} ")
        if hasattr(self, "chap_tree"):
            self.chap_tree.heading("time", text=t("col_chap_time"))
            self.chap_tree.heading("title", text=t("col_chap_title"))

        # 7. Metadata detail rows
        for lbl, key in getattr(self, "_info_rows", []):
            if key:
                lbl.config(text=f"{t(key)}")


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
