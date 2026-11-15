"""
Integrated Settings Tab module (SettingsTabMixin) for JapaneseASMR Downloader.
Provides an integrated settings viewport based on the Tokyo Night design system,
with modern typography, clean aesthetics, zero-lag subtab switching, and asynchronous workers.
"""
import os
import threading
import tkinter as tk
from tkinter import filedialog
import webbrowser
import customtkinter as ctk

from config_manager import (
    clear_all_history,
    clear_cover_cache,
    clear_temp_cache,
    get_audio_format,
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
from ui.dialogs import ask_dark_yesno, show_dark_error, show_dark_info
from ui.icons import get_icon
from ui.theme import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BG_VIEWPORT,
    BORDER_ACTIVE,
    BORDER_SUBTLE,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CAPTION,
    FONT_CODE,
    FONT_SECTION,
    FONT_SUBTITLE,
    FONT_TITLE,
    RADIUS_BUTTON,
    RADIUS_CARD,
    RADIUS_INPUT,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    STATUS_DANGER,
    STATUS_INFO,
    STATUS_SUCCESS,
    SURFACE_CARD,
    SURFACE_ELEVATED,
    SURFACE_INPUT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class SettingsTabMixin:
    """Mixin providing layout, state, and management for the Settings Tab in the primary viewport."""

    def _init_settings_variables(self):
        self.cfg = load_config()
        if not hasattr(self, "var_language"):
            self.var_language = tk.StringVar(value=self.cfg.get("language", "auto"))
        else:
            self.var_language.set(self.cfg.get("language", "auto"))

        if not hasattr(self, "var_download_dir"):
            self.var_download_dir = tk.StringVar(value=self.cfg.get("download_dir", get_download_dir()))
        else:
            self.var_download_dir.set(self.cfg.get("download_dir", get_download_dir()))

        if not hasattr(self, "var_detailed_name"):
            self.var_detailed_name = tk.BooleanVar(value=self.cfg.get("use_detailed_filename", False))
        else:
            self.var_detailed_name.set(self.cfg.get("use_detailed_filename", False))

        if not hasattr(self, "var_notify_popup"):
            self.var_notify_popup = tk.BooleanVar(value=self.cfg.get("notify_popup", True))
        else:
            self.var_notify_popup.set(self.cfg.get("notify_popup", True))

        if not hasattr(self, "var_auto_clipboard"):
            self.var_auto_clipboard = tk.BooleanVar(value=self.cfg.get("auto_clipboard", False))
        else:
            self.var_auto_clipboard.set(self.cfg.get("auto_clipboard", False))

        if not hasattr(self, "var_connections"):
            self.var_connections = tk.IntVar(value=self.cfg.get("connections", 16))
        else:
            self.var_connections.set(self.cfg.get("connections", 16))

        if not hasattr(self, "var_ytdlp_channel"):
            self.var_ytdlp_channel = tk.StringVar(value=self.cfg.get("ytdlp_channel", "stable"))
        else:
            self.var_ytdlp_channel.set(self.cfg.get("ytdlp_channel", "stable"))

        if not hasattr(self, "var_audio_format"):
            self.var_audio_format = tk.StringVar(value=self.cfg.get("audio_format", get_audio_format()))
        else:
            self.var_audio_format.set(self.cfg.get("audio_format", get_audio_format()))

        self.current_settings_subtab = "general"
        self._prev_settings_subtab = "general"
        self._cached_ytdlp_ver = None
        self._is_checking_ytdlp = False
        self._is_checking_cache = False

    def _build_settings_tab(self):
        """Construct the settings tab layout within self.tab_settings with persistent subtab frames."""
        self._init_settings_variables()

        # Primary settings container
        self.tab_settings.configure(fg_color=BG_VIEWPORT)

        # 1. Settings Header Bar
        header_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        header_frame.pack(fill="x", padx=SPACE_XL, pady=(SPACE_LG, SPACE_SM))

        self.lbl_settings_header_title = ctk.CTkLabel(
            header_frame,
            text=t("settings_title"),
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_settings_header_title.pack(anchor="w")

        self.lbl_settings_header_desc = ctk.CTkLabel(
            header_frame,
            text=t("settings_subtitle"),
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.lbl_settings_header_desc.pack(anchor="w", pady=(2, 0))

        # 2. Horizontal Subtab Segmented Bar
        nav_bar = ctk.CTkFrame(
            self.tab_settings,
            fg_color=SURFACE_CARD,
            corner_radius=RADIUS_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
            height=46,
        )
        nav_bar.pack(fill="x", padx=SPACE_XL, pady=(SPACE_SM, SPACE_MD))
        nav_bar.pack_propagate(False)

        subtabs = [
            ("general", t("tab_settings_general"), "settings"),
            ("download", t("tab_settings_download"), "download"),
            ("cache", t("tab_settings_cache"), "trash"),
            ("about", t("tab_settings_about"), "info"),
        ]

        self.settings_subtab_btns = {}
        for sub_id, label, icon_name in subtabs:
            btn = ctk.CTkButton(
                nav_bar,
                text=f" {label}",
                image=get_icon(icon_name, size=(16, 16)),
                font=FONT_BODY_BOLD,
                corner_radius=RADIUS_BUTTON,
                height=34,
                fg_color="transparent",
                hover_color=SURFACE_ELEVATED,
                text_color=TEXT_SECONDARY,
                command=lambda sid=sub_id: self._switch_settings_subtab(sid),
            )
            btn.pack(side="left", padx=SPACE_SM, pady=6)
            self.settings_subtab_btns[sub_id] = btn

        # 3. Sticky Action Bar Footer (Packed at bottom first so it stays anchored)
        footer_frame = ctk.CTkFrame(
            self.tab_settings,
            fg_color=SURFACE_CARD,
            corner_radius=RADIUS_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
            height=60,
        )
        footer_frame.pack(fill="x", side="bottom", padx=SPACE_XL, pady=(0, SPACE_LG))
        footer_frame.pack_propagate(False)

        self.lbl_settings_saved_status = ctk.CTkLabel(
            footer_frame,
            text="",
            font=FONT_BODY,
            text_color=STATUS_SUCCESS,
        )
        self.lbl_settings_saved_status.pack(side="left", padx=SPACE_LG)

        self.btn_settings_save = ctk.CTkButton(
            footer_frame,
            text=f" {t('btn_save_settings')}",
            image=get_icon("save", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
            text_color="#ffffff",
            corner_radius=RADIUS_BUTTON,
            height=38,
            width=160,
            command=self._save_settings_tab,
        )
        self.btn_settings_save.pack(side="right", padx=SPACE_LG, pady=10)

        self.btn_settings_reset = ctk.CTkButton(
            footer_frame,
            text=f" {t('btn_reset_form')}",
            image=get_icon("rotate-ccw", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_SECONDARY,
            corner_radius=RADIUS_BUTTON,
            height=38,
            width=120,
            command=self._reset_settings_form,
        )
        self.btn_settings_reset.pack(side="right", padx=(0, SPACE_SM), pady=10)

        # 4. Subtab content viewport using grid stacking (instant switch with grid_remove())
        self.subtabs_viewport = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.subtabs_viewport.pack(fill="both", expand=True, padx=SPACE_XL, pady=(0, SPACE_SM))
        self.subtabs_viewport.grid_rowconfigure(0, weight=1)
        self.subtabs_viewport.grid_columnconfigure(0, weight=1)

        self.subtab_frames = {}
        for s_id in ["general", "download", "cache", "about"]:
            sf = ctk.CTkScrollableFrame(
                self.subtabs_viewport,
                fg_color="transparent",
                scrollbar_button_color=SURFACE_ELEVATED,
                scrollbar_button_hover_color=BORDER_ACTIVE,
            )
            sf.grid(row=0, column=0, sticky="nsew")
            if s_id != "general":
                sf.grid_remove()
            self.subtab_frames[s_id] = sf

        # Build each subtab ONCE into its persistent scrollable frame
        self._build_subtab_general(self.subtab_frames["general"])
        self._build_subtab_download(self.subtab_frames["download"])
        self._build_subtab_cache(self.subtab_frames["cache"])
        self._build_subtab_about(self.subtab_frames["about"])

        # Display first subtab initially
        self._prev_settings_subtab = "general"
        self._switch_settings_subtab("general")

        # Warm up background version & cache checks asynchronously
        self._refresh_ytdlp_version_async()
        self._refresh_cache_stats()

    def _switch_settings_subtab(self, subtab_name: str):
        """Switch active subtab instantaneously by unmapping inactive frames via grid_remove()."""
        prev = getattr(self, "_prev_settings_subtab", None)
        self.current_settings_subtab = subtab_name
        self._prev_settings_subtab = subtab_name

        # Update button visual state only for affected tabs
        if prev and prev in self.settings_subtab_btns and prev != subtab_name:
            self.settings_subtab_btns[prev].configure(fg_color="transparent", text_color=TEXT_SECONDARY)
        if subtab_name in self.settings_subtab_btns:
            self.settings_subtab_btns[subtab_name].configure(fg_color=ACCENT_PRIMARY, text_color="#ffffff")

        # Map active subtab frame and unmap others
        for sid, frame in self.subtab_frames.items():
            if sid == subtab_name:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_remove()

        # Refresh cache stats when switching to cache subtab
        if subtab_name == "cache":
            self._refresh_cache_stats()

    # ==================== SUBTAB 1: GENERAL ====================
    def _build_subtab_general(self, parent):
        # Card 1: Language
        card_lang = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_lang.pack(fill="x", pady=(0, SPACE_MD))

        p_lang = ctk.CTkFrame(card_lang, fg_color="transparent")
        p_lang.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_lang_title = ctk.CTkLabel(p_lang, text=t("lbl_language"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_lang_title.pack(fill="x")
        self.lbl_set_lang_desc = ctk.CTkLabel(p_lang, text=t("lbl_language_desc"), font=FONT_CAPTION, text_color=TEXT_MUTED, anchor="w")
        self.lbl_set_lang_desc.pack(fill="x", pady=(2, 8))

        lang_options = get_available_languages()
        disp_map = {code: disp for code, disp in lang_options}
        self._lang_code_map = {disp: code for code, disp in lang_options}

        cur_code = self.var_language.get()
        cur_disp = disp_map.get(cur_code, lang_options[0][1])

        def _on_lang_changed(choice):
            self.var_language.set(self._lang_code_map.get(choice, "auto"))

        self.cbo_lang = ctk.CTkOptionMenu(
            p_lang,
            values=[disp for _, disp in lang_options],
            command=_on_lang_changed,
            font=FONT_BODY,
            corner_radius=RADIUS_BUTTON,
            fg_color=SURFACE_INPUT,
            button_color=BORDER_SUBTLE,
            button_hover_color=ACCENT_PRIMARY,
            height=34,
            width=220,
        )
        self.cbo_lang.set(cur_disp)
        self.cbo_lang.pack(anchor="w")

        # Card 2: Storage Directory
        card_dir = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_dir.pack(fill="x", pady=(0, SPACE_MD))

        p_dir = ctk.CTkFrame(card_dir, fg_color="transparent")
        p_dir.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_dir_title = ctk.CTkLabel(p_dir, text=t("lbl_storage_folder"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_dir_title.pack(fill="x")
        self.lbl_set_dir_desc = ctk.CTkLabel(p_dir, text=t("lbl_storage_folder_desc"), font=FONT_CAPTION, text_color=TEXT_MUTED, anchor="w")
        self.lbl_set_dir_desc.pack(fill="x", pady=(2, 8))

        dir_row = ctk.CTkFrame(p_dir, fg_color="transparent")
        dir_row.pack(fill="x")

        self.entry_set_dir = ctk.CTkEntry(
            dir_row,
            textvariable=self.var_download_dir,
            font=FONT_CODE,
            corner_radius=RADIUS_INPUT,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
            height=36,
        )
        self.entry_set_dir.pack(side="left", fill="x", expand=True, padx=(0, SPACE_SM))

        self.btn_set_browse = ctk.CTkButton(
            dir_row,
            text=f" {t('btn_browse')}",
            image=get_icon("folder", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=36,
            width=110,
            command=self._browse_download_dir,
        )
        self.btn_set_browse.pack(side="right")

        # Card 3: Automation & Notification Switches
        card_opts = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_opts.pack(fill="x", pady=(0, SPACE_MD))

        p_opts = ctk.CTkFrame(card_opts, fg_color="transparent")
        p_opts.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_opts_title = ctk.CTkLabel(p_opts, text=t("lbl_settings_automation"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_opts_title.pack(fill="x", pady=(0, 6))

        # Switch 1: Detailed Name
        f_sw1 = ctk.CTkFrame(p_opts, fg_color="transparent")
        f_sw1.pack(fill="x", pady=6)
        self.sw_detailed = ctk.CTkSwitch(
            f_sw1,
            text=t("chk_detailed_name"),
            variable=self.var_detailed_name,
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
            fg_color=SURFACE_INPUT,
            progress_color=ACCENT_PRIMARY,
        )
        self.sw_detailed.pack(anchor="w")
        self.lbl_desc_sw1 = ctk.CTkLabel(
            f_sw1,
            text=t("lbl_detailed_name_desc"),
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.lbl_desc_sw1.pack(anchor="w", padx=(44, 0))

        # Switch 2: Notify Popup
        f_sw2 = ctk.CTkFrame(p_opts, fg_color="transparent")
        f_sw2.pack(fill="x", pady=6)
        self.sw_notify = ctk.CTkSwitch(
            f_sw2,
            text=t("chk_notify_popup"),
            variable=self.var_notify_popup,
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
            fg_color=SURFACE_INPUT,
            progress_color=ACCENT_PRIMARY,
        )
        self.sw_notify.pack(anchor="w")
        self.lbl_desc_sw2 = ctk.CTkLabel(
            f_sw2,
            text=t("lbl_notify_popup_desc"),
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.lbl_desc_sw2.pack(anchor="w", padx=(44, 0))

        # Switch 3: Auto Clipboard
        f_sw3 = ctk.CTkFrame(p_opts, fg_color="transparent")
        f_sw3.pack(fill="x", pady=6)
        self.sw_clip = ctk.CTkSwitch(
            f_sw3,
            text=t("chk_auto_clipboard"),
            variable=self.var_auto_clipboard,
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
            fg_color=SURFACE_INPUT,
            progress_color=ACCENT_PRIMARY,
        )
        self.sw_clip.pack(anchor="w")
        self.lbl_desc_sw3 = ctk.CTkLabel(
            f_sw3,
            text=t("lbl_auto_clipboard_desc"),
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.lbl_desc_sw3.pack(anchor="w", padx=(44, 0))

    def _browse_download_dir(self):
        initial = self.var_download_dir.get() or get_download_dir()
        d = filedialog.askdirectory(initialdir=initial)
        if d:
            abs_d = os.path.abspath(d)
            self.var_download_dir.set(abs_d)
            if hasattr(self, "entry_set_dir") and self.entry_set_dir.winfo_exists():
                self.entry_set_dir.delete(0, "end")
                self.entry_set_dir.insert(0, abs_d)

    # ==================== SUBTAB 2: DOWNLOAD & ENGINE ====================
    def _build_subtab_download(self, parent):
        # Card 1: Audio Format
        card_fmt = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_fmt.pack(fill="x", pady=(0, SPACE_MD))

        p_fmt = ctk.CTkFrame(card_fmt, fg_color="transparent")
        p_fmt.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_fmt_title = ctk.CTkLabel(p_fmt, text=t("lbl_audio_format"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_fmt_title.pack(fill="x")
        self.lbl_set_fmt_desc = ctk.CTkLabel(p_fmt, text=t("lbl_audio_format_desc"), font=FONT_CAPTION, text_color=TEXT_MUTED, anchor="w")
        self.lbl_set_fmt_desc.pack(fill="x", pady=(2, 8))

        fmt_options = [
            ("auto", t("fmt_auto")),
            ("m4a", t("fmt_m4a")),
            ("mp3", t("fmt_mp3")),
            ("flac", t("fmt_flac")),
            ("wav", t("fmt_wav")),
        ]
        self._fmt_disp_map = {k: v for k, v in fmt_options}
        self._fmt_code_map = {v: k for k, v in fmt_options}

        def _on_fmt_changed(choice):
            self.var_audio_format.set(self._fmt_code_map.get(choice, "auto"))

        cur_fmt = self.var_audio_format.get()
        self.cbo_fmt = ctk.CTkOptionMenu(
            p_fmt,
            values=[v for _, v in fmt_options],
            command=_on_fmt_changed,
            font=FONT_BODY,
            corner_radius=RADIUS_BUTTON,
            fg_color=SURFACE_INPUT,
            button_color=BORDER_SUBTLE,
            button_hover_color=ACCENT_PRIMARY,
            height=34,
            width=240,
        )
        self.cbo_fmt.set(self._fmt_disp_map.get(cur_fmt, fmt_options[0][1]))
        self.cbo_fmt.pack(anchor="w")

        # Card 2: Aria2c Multi-connection Options
        card_conn = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_conn.pack(fill="x", pady=(0, SPACE_MD))

        p_conn = ctk.CTkFrame(card_conn, fg_color="transparent")
        p_conn.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_conn_title = ctk.CTkLabel(p_conn, text=t("lbl_aria2_connections"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_conn_title.pack(fill="x")
        self.lbl_set_conn_desc = ctk.CTkLabel(p_conn, text=t("lbl_aria2_connections_desc"), font=FONT_CAPTION, text_color=TEXT_MUTED, anchor="w")
        self.lbl_set_conn_desc.pack(fill="x", pady=(2, 8))

        conn_options = ["4", "8", "16", "24", "32"]
        self.cbo_conn = ctk.CTkOptionMenu(
            p_conn,
            values=conn_options,
            command=lambda v: self.var_connections.set(int(v)),
            font=FONT_BODY,
            corner_radius=RADIUS_BUTTON,
            fg_color=SURFACE_INPUT,
            button_color=BORDER_SUBTLE,
            button_hover_color=ACCENT_PRIMARY,
            height=34,
            width=120,
        )
        self.cbo_conn.set(str(self.var_connections.get()))
        self.cbo_conn.pack(anchor="w")

        # Card 3: yt-dlp Engine Status & Update
        card_upd = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_upd.pack(fill="x", pady=(0, SPACE_MD))

        p_upd = ctk.CTkFrame(card_upd, fg_color="transparent")
        p_upd.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_ytdlp_title = ctk.CTkLabel(p_upd, text=t("lbl_ytdlp_engine"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_ytdlp_title.pack(fill="x")

        self.lbl_ytdlp_ver = ctk.CTkLabel(
            p_upd,
            text=t("lbl_ytdlp_ver_installed", ver=t("lbl_ytdlp_ver_checking")),
            font=FONT_CODE,
            text_color=STATUS_INFO,
            anchor="w",
        )
        self.lbl_ytdlp_ver.pack(fill="x", pady=(4, 8))

        upd_action_row = ctk.CTkFrame(p_upd, fg_color="transparent")
        upd_action_row.pack(fill="x")

        self.btn_update_ytdlp_tab = ctk.CTkButton(
            upd_action_row,
            text=f" {t('btn_update_ytdlp')}",
            image=get_icon("refresh", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
            text_color="#ffffff",
            corner_radius=RADIUS_BUTTON,
            height=34,
            width=160,
            command=self._do_update_ytdlp_tab,
        )
        self.btn_update_ytdlp_tab.pack(side="left", padx=(0, SPACE_MD))

        self.lbl_ytdlp_status_tab = ctk.CTkLabel(
            upd_action_row,
            text=t("status_ytdlp_ready"),
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
        )
        self.lbl_ytdlp_status_tab.pack(side="left")

    def _refresh_ytdlp_version_async(self, force=False):
        """Asynchronously query the yt-dlp binary version in a background worker."""
        if self._cached_ytdlp_ver and not force:
            if hasattr(self, "lbl_ytdlp_ver") and self.lbl_ytdlp_ver.winfo_exists():
                self.lbl_ytdlp_ver.configure(text=t("lbl_ytdlp_ver_installed", ver=self._cached_ytdlp_ver))
            return
        if getattr(self, "_is_checking_ytdlp", False):
            return
        self._is_checking_ytdlp = True
        if hasattr(self, "lbl_ytdlp_ver") and self.lbl_ytdlp_ver.winfo_exists():
            self.lbl_ytdlp_ver.configure(text=t("lbl_ytdlp_ver_installed", ver=t("lbl_ytdlp_ver_checking")))

        def _worker():
            try:
                ver = get_ytdlp_version()
                self._cached_ytdlp_ver = ver
            except Exception:
                self._cached_ytdlp_ver = "Unknown"
            finally:
                self._is_checking_ytdlp = False

        threading.Thread(target=_worker, daemon=True).start()
        self._poll_ytdlp_version()

    def _poll_ytdlp_version(self):
        """Poll the main thread to update the yt-dlp version label."""
        if self._cached_ytdlp_ver:
            if hasattr(self, "lbl_ytdlp_ver") and self.lbl_ytdlp_ver.winfo_exists():
                self.lbl_ytdlp_ver.configure(text=t("lbl_ytdlp_ver_installed", ver=self._cached_ytdlp_ver))
        elif getattr(self, "_is_checking_ytdlp", False):
            self.after(200, self._poll_ytdlp_version)

    def _do_update_ytdlp_tab(self):
        self.btn_update_ytdlp_tab.configure(state="disabled")
        self.lbl_ytdlp_status_tab.configure(text=t("status_ytdlp_updating"), text_color=STATUS_INFO)
        self._ytdlp_update_result = None

        channel = self.var_ytdlp_channel.get() if hasattr(self, "var_ytdlp_channel") else "stable"

        def _worker():
            success, status_code, msg = update_ytdlp_engine(channel=channel)
            ver = get_ytdlp_version() if success else None
            self._ytdlp_update_result = (success, status_code, msg, ver)

        threading.Thread(target=_worker, daemon=True).start()
        self._poll_ytdlp_update()

    def _poll_ytdlp_update(self):
        """Poll the yt-dlp update process status from the main thread."""
        if getattr(self, "_ytdlp_update_result", None) is not None:
            success, status_code, msg, ver = self._ytdlp_update_result
            self._ytdlp_update_result = None
            if hasattr(self, "btn_update_ytdlp_tab") and self.btn_update_ytdlp_tab.winfo_exists():
                self.btn_update_ytdlp_tab.configure(state="normal")
            if success:
                self._cached_ytdlp_ver = ver
                if hasattr(self, "lbl_ytdlp_ver") and self.lbl_ytdlp_ver.winfo_exists():
                    self.lbl_ytdlp_ver.configure(text=t("lbl_ytdlp_ver_installed", ver=ver))
                if hasattr(self, "lbl_ytdlp_status_tab") and self.lbl_ytdlp_status_tab.winfo_exists():
                    self.lbl_ytdlp_status_tab.configure(text=f"Sukses diperbarui ke: {ver}", text_color=STATUS_SUCCESS)
                show_dark_info(self, "Pembaruan Berhasil", f"Engine yt-dlp berhasil diperbarui!\n\nVersi aktif: {ver}")
            elif status_code == "already_latest":
                if hasattr(self, "lbl_ytdlp_status_tab") and self.lbl_ytdlp_status_tab.winfo_exists():
                    self.lbl_ytdlp_status_tab.configure(text=t("status_ytdlp_latest"), text_color=TEXT_SECONDARY)
                show_dark_info(self, "Info Pembaruan", msg)
            else:
                if hasattr(self, "lbl_ytdlp_status_tab") and self.lbl_ytdlp_status_tab.winfo_exists():
                    self.lbl_ytdlp_status_tab.configure(text=t("status_ytdlp_failed"), text_color=STATUS_DANGER)
                show_dark_error(self, "Pembaruan Gagal", f"Gagal memperbarui engine yt-dlp.\n\nError: {msg}")
        else:
            self.after(200, self._poll_ytdlp_update)

    # ==================== SUBTAB 3: CACHE & DATA ====================
    def _build_subtab_cache(self, parent):
        # Card 1: Storage Statistics
        card_stats = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_stats.pack(fill="x", pady=(0, SPACE_MD))

        p_stats = ctk.CTkFrame(card_stats, fg_color="transparent")
        p_stats.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_cache_title = ctk.CTkLabel(p_stats, text=t("lbl_storage_statistics"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_cache_title.pack(fill="x", pady=(0, 8))

        self.lbl_cache_covers = ctk.CTkLabel(p_stats, text=t("lbl_stat_covers", count=0, size="0 MB"), font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w")
        self.lbl_cache_covers.pack(fill="x", pady=3)

        self.lbl_cache_temp = ctk.CTkLabel(p_stats, text=t("lbl_stat_temp", count=0, size="0 MB"), font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w")
        self.lbl_cache_temp.pack(fill="x", pady=3)

        self.lbl_cache_hist = ctk.CTkLabel(p_stats, text=t("lbl_stat_hist", count=0), font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w")
        self.lbl_cache_hist.pack(fill="x", pady=3)

        # Card 2: Maintenance Actions
        card_actions = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_actions.pack(fill="x", pady=(0, SPACE_MD))

        p_act = ctk.CTkFrame(card_actions, fg_color="transparent")
        p_act.pack(fill="x", padx=SPACE_LG, pady=SPACE_LG)

        self.lbl_set_maint_title = ctk.CTkLabel(p_act, text=t("lbl_maintenance_actions"), font=FONT_SECTION, text_color=TEXT_PRIMARY, anchor="w")
        self.lbl_set_maint_title.pack(fill="x", pady=(0, 10))

        self.btn_clear_cov = ctk.CTkButton(
            p_act,
            text=f" {t('btn_clear_covers')}",
            image=get_icon("trash", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=34,
            command=self._do_clear_covers_tab,
        )
        self.btn_clear_cov.pack(fill="x", pady=4)

        self.btn_clear_tmp = ctk.CTkButton(
            p_act,
            text=f" {t('btn_clear_temp')}",
            image=get_icon("trash", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=34,
            command=self._do_clear_temp_tab,
        )
        self.btn_clear_tmp.pack(fill="x", pady=4)

        self.btn_clear_hst = ctk.CTkButton(
            p_act,
            text=f" {t('btn_clear_all_history')}",
            image=get_icon("trash", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=STATUS_DANGER,
            hover_color="#e11d48",
            text_color="#ffffff",
            corner_radius=RADIUS_BUTTON,
            height=34,
            command=self._do_clear_history_tab,
        )
        self.btn_clear_hst.pack(fill="x", pady=(4, 0))

    def _refresh_cache_stats(self):
        """Memuat ukuran cache di latar belakang agar antarmuka tidak membeku."""
        if getattr(self, "_is_checking_cache", False):
            return
        self._is_checking_cache = True
        self._cache_stats_result = None

        def _worker():
            try:
                info = get_cache_size_info()
                histories = load_history()
                c_count = info.get("covers_count", 0)
                c_size = info.get("covers_size", "0 MB")
                t_count = info.get("temp_count", 0)
                t_size = info.get("temp_size", "0 MB")
                h_len = len(histories)
                self._cache_stats_result = (c_count, c_size, t_count, t_size, h_len)
            except Exception:
                pass
            finally:
                self._is_checking_cache = False

        threading.Thread(target=_worker, daemon=True).start()
        self._poll_cache_stats()

    def _poll_cache_stats(self):
        """Polling dari thread utama untuk memperbarui label statistik cache."""
        if getattr(self, "_cache_stats_result", None) is not None:
            c_count, c_size, t_count, t_size, h_len = self._cache_stats_result
            self._cache_stats_result = None
            if hasattr(self, "lbl_cache_covers") and self.lbl_cache_covers.winfo_exists():
                self.lbl_cache_covers.configure(text=t("lbl_stat_covers", count=c_count, size=c_size))
            if hasattr(self, "lbl_cache_temp") and self.lbl_cache_temp.winfo_exists():
                self.lbl_cache_temp.configure(text=t("lbl_stat_temp", count=t_count, size=t_size))
            if hasattr(self, "lbl_cache_hist") and self.lbl_cache_hist.winfo_exists():
                self.lbl_cache_hist.configure(text=t("lbl_stat_hist", count=h_len))
        elif getattr(self, "_is_checking_cache", False):
            self.after(150, self._poll_cache_stats)

    def _do_clear_covers_tab(self):
        c, s = clear_cover_cache()
        show_dark_info(self, "Cache Dibersihkan", f"Berhasil membersihkan {c} file cover ({s:.2f} MB).")
        self._refresh_cache_stats()

    def _do_clear_temp_tab(self):
        c, s = clear_temp_cache()
        show_dark_info(self, "Cache Dibersihkan", f"Berhasil membersihkan {c} file temp ({s:.2f} MB).")
        self._refresh_cache_stats()

    def _do_clear_history_tab(self):
        ans = ask_dark_yesno(
            self,
            "Konfirmasi Hapus",
            "Apakah Anda yakin ingin menghapus SEMUA riwayat unduhan?\n\n(Catatan: Berkas audio di folder unduhan TIDAK akan terhapus).",
        )
        if ans:
            c = clear_all_history()
            show_dark_info(self, "Riwayat Dihapus", f"Berhasil menghapus {c} catatan riwayat.")
            if hasattr(self, "_load_history_view"):
                self._load_history_view()
            self._refresh_cache_stats()

    # ==================== SUBTAB 4: ABOUT ====================
    def _build_subtab_about(self, parent):
        card_about = ctk.CTkFrame(
            parent,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        card_about.pack(fill="x", pady=(0, SPACE_MD))

        p_abt = ctk.CTkFrame(card_about, fg_color="transparent")
        p_abt.pack(fill="x", padx=SPACE_XL, pady=SPACE_XL)

        ctk.CTkLabel(p_abt, text="JapaneseASMR Downloader & Player", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(pady=(0, 2))
        ctk.CTkLabel(p_abt, text="Versi 1.2.0 • Windows Pure Desktop GUI", font=FONT_CAPTION, text_color=STATUS_INFO).pack(pady=(0, 12))

        self.lbl_about_app_desc = ctk.CTkLabel(
            p_abt,
            text=t("about_app_desc"),
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="center",
        )
        self.lbl_about_app_desc.pack(pady=(0, 16))

        links_row = ctk.CTkFrame(p_abt, fg_color="transparent")
        links_row.pack(pady=(0, 8))

        self.btn_github = ctk.CTkButton(
            links_row,
            text=f" {t('btn_github_repo')}",
            image=get_icon("info", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=34,
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl"),
        )
        self.btn_github.pack(side="left", padx=SPACE_SM)

        self.btn_issues = ctk.CTkButton(
            links_row,
            text=f" {t('btn_report_issues')}",
            image=get_icon("info", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_SECONDARY,
            corner_radius=RADIUS_BUTTON,
            height=34,
            command=lambda: webbrowser.open("https://github.com/SayMaven/japaneseasmr-dl/issues"),
        )
        self.btn_issues.pack(side="left", padx=SPACE_SM)

    # ==================== RETRANSLATE SETTINGS TAB ====================
    def retranslate_settings_tab(self):
        """Apply dynamic language translations to all Settings Tab widgets."""
        if hasattr(self, "lbl_settings_header_title"):
            self.lbl_settings_header_title.configure(text=t("settings_title"))
        if hasattr(self, "lbl_settings_header_desc"):
            self.lbl_settings_header_desc.configure(text=t("settings_subtitle"))

        if hasattr(self, "settings_subtab_btns"):
            sub_titles = {
                "general": t("tab_settings_general"),
                "download": t("tab_settings_download"),
                "cache": t("tab_settings_cache"),
                "about": t("tab_settings_about"),
            }
            for sid, label in sub_titles.items():
                if sid in self.settings_subtab_btns:
                    self.settings_subtab_btns[sid].configure(text=f" {label}")

        # General
        if hasattr(self, "lbl_set_lang_title"):
            self.lbl_set_lang_title.configure(text=t("lbl_language"))
        if hasattr(self, "lbl_set_lang_desc"):
            self.lbl_set_lang_desc.configure(text=t("lbl_language_desc"))
        if hasattr(self, "lbl_set_dir_title"):
            self.lbl_set_dir_title.configure(text=t("lbl_storage_folder"))
        if hasattr(self, "lbl_set_dir_desc"):
            self.lbl_set_dir_desc.configure(text=t("lbl_storage_folder_desc"))
        if hasattr(self, "btn_set_browse"):
            self.btn_set_browse.configure(text=f" {t('btn_browse')}")
        if hasattr(self, "lbl_set_opts_title"):
            self.lbl_set_opts_title.configure(text=t("lbl_settings_automation"))
        if hasattr(self, "sw_detailed"):
            self.sw_detailed.configure(text=t("chk_detailed_name"))
        if hasattr(self, "lbl_desc_sw1"):
            self.lbl_desc_sw1.configure(text=t("lbl_detailed_name_desc"))
        if hasattr(self, "sw_notify"):
            self.sw_notify.configure(text=t("chk_notify_popup"))
        if hasattr(self, "lbl_desc_sw2"):
            self.lbl_desc_sw2.configure(text=t("lbl_notify_popup_desc"))
        if hasattr(self, "sw_clip"):
            self.sw_clip.configure(text=t("chk_auto_clipboard"))
        if hasattr(self, "lbl_desc_sw3"):
            self.lbl_desc_sw3.configure(text=t("lbl_auto_clipboard_desc"))

        # Download
        if hasattr(self, "lbl_set_fmt_title"):
            self.lbl_set_fmt_title.configure(text=t("lbl_audio_format"))
        if hasattr(self, "lbl_set_fmt_desc"):
            self.lbl_set_fmt_desc.configure(text=t("lbl_audio_format_desc"))
        if hasattr(self, "lbl_set_conn_title"):
            self.lbl_set_conn_title.configure(text=t("lbl_aria2_connections"))
        if hasattr(self, "lbl_set_conn_desc"):
            self.lbl_set_conn_desc.configure(text=t("lbl_aria2_connections_desc"))
        if hasattr(self, "lbl_set_ytdlp_title"):
            self.lbl_set_ytdlp_title.configure(text=t("lbl_ytdlp_engine"))
        if hasattr(self, "btn_update_ytdlp_tab"):
            self.btn_update_ytdlp_tab.configure(text=f" {t('btn_update_ytdlp')}")
        if hasattr(self, "lbl_ytdlp_ver"):
            ver_text = self._cached_ytdlp_ver if self._cached_ytdlp_ver else t("lbl_ytdlp_ver_checking")
            self.lbl_ytdlp_ver.configure(text=t("lbl_ytdlp_ver_installed", ver=ver_text))
        if hasattr(self, "lbl_ytdlp_status_tab"):
            self.lbl_ytdlp_status_tab.configure(text=t("status_ytdlp_ready"))

        # Cache
        if hasattr(self, "lbl_set_cache_title"):
            self.lbl_set_cache_title.configure(text=t("lbl_storage_statistics"))
        if hasattr(self, "lbl_set_maint_title"):
            self.lbl_set_maint_title.configure(text=t("lbl_maintenance_actions"))
        if hasattr(self, "btn_clear_cov"):
            self.btn_clear_cov.configure(text=f" {t('btn_clear_covers')}")
        if hasattr(self, "btn_clear_tmp"):
            self.btn_clear_tmp.configure(text=f" {t('btn_clear_temp')}")
        if hasattr(self, "btn_clear_hst"):
            self.btn_clear_hst.configure(text=f" {t('btn_clear_all_history')}")
        self._refresh_cache_stats()

        # About
        if hasattr(self, "lbl_about_app_desc"):
            self.lbl_about_app_desc.configure(text=t("about_app_desc"))
        if hasattr(self, "btn_github"):
            self.btn_github.configure(text=f" {t('btn_github_repo')}")
        if hasattr(self, "btn_issues"):
            self.btn_issues.configure(text=f" {t('btn_report_issues')}")

        # Footer
        if hasattr(self, "btn_settings_save"):
            self.btn_settings_save.configure(text=f" {t('btn_save_settings')}")
        if hasattr(self, "btn_settings_reset"):
            self.btn_settings_reset.configure(text=f" {t('btn_reset_form')}")

    # ==================== SAVE & RESET ====================
    def _save_settings_tab(self):
        new_lang = self.var_language.get()
        old_lang = get_active_language()

        raw_dir = self.entry_set_dir.get().strip() if hasattr(self, "entry_set_dir") else self.var_download_dir.get().strip()
        new_dir = os.path.abspath(raw_dir) if raw_dir else os.path.abspath(get_download_dir())

        self.cfg["language"] = new_lang
        self.cfg["download_dir"] = new_dir
        self.cfg["use_detailed_filename"] = self.var_detailed_name.get()
        self.cfg["notify_popup"] = self.var_notify_popup.get()
        self.cfg["auto_clipboard"] = self.var_auto_clipboard.get()
        self.cfg["connections"] = self.var_connections.get()
        self.cfg["ytdlp_channel"] = self.var_ytdlp_channel.get()
        self.cfg["audio_format"] = self.var_audio_format.get()

        save_config(self.cfg)
        set_audio_format(self.var_audio_format.get())

        if hasattr(self, "sync_download_directory"):
            self.sync_download_directory(new_dir)
        else:
            set_download_dir(new_dir)

        if hasattr(self, "opt_detailed_name"):
            self.opt_detailed_name.set(self.var_detailed_name.get())
        if hasattr(self, "var_auto_clipboard"):
            self.var_auto_clipboard.set(self.var_auto_clipboard.get())

        if new_lang != old_lang:
            set_active_language(new_lang)
            if hasattr(self, "retranslate_ui"):
                self.retranslate_ui()
            self.retranslate_settings_tab()

        # Display inline status feedback
        self.lbl_settings_saved_status.configure(text=t("msg_settings_saved"), text_color=STATUS_SUCCESS)
        self.after(3500, lambda: self.lbl_settings_saved_status.configure(text=""))

    def _reset_settings_form(self):
        self._init_settings_variables()

        # Reset OptionMenus
        lang_options = get_available_languages()
        disp_map = {code: disp for code, disp in lang_options}
        if hasattr(self, "cbo_lang"):
            cur_code = self.var_language.get()
            self.cbo_lang.set(disp_map.get(cur_code, lang_options[0][1]))

        if hasattr(self, "cbo_fmt"):
            cur_fmt = self.var_audio_format.get()
            self.cbo_fmt.set(self._fmt_disp_map.get(cur_fmt, "Auto"))

        if hasattr(self, "cbo_conn"):
            self.cbo_conn.set(str(self.var_connections.get()))

        self.lbl_settings_saved_status.configure(text=t("msg_settings_reset"), text_color=TEXT_SECONDARY)
        self.after(3000, lambda: self.lbl_settings_saved_status.configure(text=""))
        lang_options = get_available_languages()
        disp_map = {code: disp for code, disp in lang_options}
        if hasattr(self, "cbo_lang"):
            cur_code = self.var_language.get()
            self.cbo_lang.set(disp_map.get(cur_code, lang_options[0][1]))

        if hasattr(self, "cbo_fmt"):
            cur_fmt = self.var_audio_format.get()
            self.cbo_fmt.set(self._fmt_disp_map.get(cur_fmt, "Auto"))

        if hasattr(self, "cbo_conn"):
            self.cbo_conn.set(str(self.var_connections.get()))

        self.lbl_settings_saved_status.configure(text=t("msg_settings_reset"), text_color=TEXT_SECONDARY)
        self.after(3000, lambda: self.lbl_settings_saved_status.configure(text=""))
