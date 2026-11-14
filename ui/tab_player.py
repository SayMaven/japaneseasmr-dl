import ctypes
import io
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
import customtkinter as ctk

from PIL import Image, ImageTk

from config_manager import (
    extract_chapters_from_audio,
    fetch_japaneseasmr_chapters,
    get_bin_executable,
    get_download_dir,
    get_precise_duration_seconds,
    load_history,
    write_cue_sheet,
)
from dlsite_scraper import resolve_best_cover_url
from i18n import t
from ui.constants import REFERER, USER_AGENT
from ui.dialogs import show_dark_error, show_dark_info, show_dark_warning
from ui.icons import get_icon
from ui.player_engine import (
    NativeMFPlayer,
    format_time,
    get_precise_duration_ms,
    mci_send,
)
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
    RADIUS_BUTTON,
    RADIUS_CARD,
    RADIUS_INPUT,
    RADIUS_PILL,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
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


class PlayerTabMixin:
    """Mixin untuk membangun antarmuka dan logika pemutar audio (Player Tab) v1.2.0."""
    def _build_player_tab(self):
        container = self.tab_player

        # Layout 2 Kolom: Kiri (Playlist & Chapters), Kanan (Now Playing & Controls)
        main_container = ctk.CTkFrame(container, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        left_p_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        left_p_panel.pack(side="left", fill="both", expand=True, padx=(0, SPACE_MD))

        # 1. Playlist Card
        playlist_card = ctk.CTkFrame(
            left_p_panel,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        playlist_card.pack(fill="both", expand=True, pady=(0, SPACE_MD))

        p_header = ctk.CTkFrame(playlist_card, fg_color="transparent")
        p_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM))

        self.lbl_p_title = ctk.CTkLabel(
            p_header,
            text=t("lbl_playlist"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_p_title.pack(side="left")

        self.refresh_p_btn = ctk.CTkButton(
            p_header,
            text=f" {t('btn_refresh_playlist')}",
            image=get_icon("refresh", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=32,
            width=110,
            command=self._refresh_playlist_view,
        )
        self.refresh_p_btn.pack(side="right")

        # Treeview Playlist
        tree_p_container = ctk.CTkFrame(
            playlist_card,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        tree_p_container.pack(fill="both", expand=True, padx=SPACE_LG, pady=(0, SPACE_MD))

        cols = ("rjid", "title", "cv", "size")
        self.player_tree = ttk.Treeview(tree_p_container, columns=cols, show="headings", selectmode="browse", style="Treeview")
        self.player_tree.heading("rjid", text=t("col_rjid"), anchor="center")
        self.player_tree.heading("title", text=t("col_play_title"), anchor="w")
        self.player_tree.heading("cv", text=t("col_hist_cv"), anchor="w")
        self.player_tree.heading("size", text=t("col_play_duration"), anchor="center")

        self.player_tree.column("rjid", width=105, anchor="center")
        self.player_tree.column("title", width=280, anchor="w")
        self.player_tree.column("cv", width=140, anchor="w")
        self.player_tree.column("size", width=85, anchor="center")

        p_scroll = ttk.Scrollbar(tree_p_container, orient="vertical", command=self.player_tree.yview, style="Vertical.TScrollbar")
        self.player_tree.configure(yscrollcommand=p_scroll.set)

        self.player_tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        p_scroll.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.player_tree.bind("<Double-1>", lambda e: self._player_play_selected())
        self.player_tree.bind("<<TreeviewSelect>>", self._on_playlist_select)

        # 2. Chapters Card (Bab Audio)
        self.chap_frame = ctk.CTkFrame(
            left_p_panel,
            height=160,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.chap_frame.pack(fill="x", pady=0)
        self.chap_frame.pack_propagate(False)

        chap_header = ctk.CTkFrame(self.chap_frame, fg_color="transparent")
        chap_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_SM, 4))

        self.lbl_chap_title = ctk.CTkLabel(
            chap_header,
            text=t("lbl_chapters"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_chap_title.pack(side="left")

        chap_tree_container = ctk.CTkFrame(
            self.chap_frame,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        chap_tree_container.pack(fill="both", expand=True, padx=SPACE_LG, pady=(0, SPACE_SM))

        c_cols = ("time", "title")
        self.chap_tree = ttk.Treeview(chap_tree_container, columns=c_cols, show="headings", selectmode="browse", style="Treeview")
        self.chap_tree.heading("time", text=t("col_chap_time"), anchor="center")
        self.chap_tree.heading("title", text=t("col_chap_title"), anchor="w")
        self.chap_tree.column("time", width=90, anchor="center")
        self.chap_tree.column("title", width=380, anchor="w")

        chap_scroll = ttk.Scrollbar(chap_tree_container, orient="vertical", command=self.chap_tree.yview, style="Vertical.TScrollbar")
        self.chap_tree.configure(yscrollcommand=chap_scroll.set)

        self.chap_tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        chap_scroll.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.chap_tree.bind("<Double-1>", self._on_chapter_double_click)

        # 3. Panel Kanan: Now Playing Screen & Controls
        self.right_p_panel = ctk.CTkFrame(
            main_container,
            width=340,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.right_p_panel.pack(side="right", fill="both", pady=0)
        self.right_p_panel.pack_propagate(False)

        np_header = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        np_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM))

        self.lbl_now_playing_title = ctk.CTkLabel(
            np_header,
            text=t("lbl_playlist"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_now_playing_title.pack(side="left")

        # Canvas Cover
        self.player_canvas = tk.Canvas(
            self.right_p_panel,
            bg=SURFACE_INPUT,
            width=290,
            height=185,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_SUBTLE,
        )
        self.player_canvas.pack(pady=4, padx=SPACE_LG)
        self.player_canvas.create_text(
            145, 92, text="Pilih audio untuk memutar", fill=TEXT_MUTED, font=FONT_BODY
        )

        # Track Info (Title, RJID, CV)
        track_info_frame = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        track_info_frame.pack(fill="x", padx=SPACE_LG, pady=(6, 4))

        self.lbl_p_track_title = ctk.CTkLabel(
            track_info_frame,
            text="-",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=290,
            justify="left",
        )
        self.lbl_p_track_title.pack(fill="x")

        self.lbl_p_track_sub = ctk.CTkLabel(
            track_info_frame,
            text="Belum ada track dimuat",
            font=FONT_CAPTION,
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.lbl_p_track_sub.pack(fill="x", pady=(2, 0))

        # Timeline Bar & Durasi
        timeline_frame = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        timeline_frame.pack(fill="x", padx=SPACE_LG, pady=(6, 2))

        self.lbl_time_cur = ctk.CTkLabel(
            timeline_frame,
            text="00:00",
            font=FONT_CODE,
            text_color=STATUS_SUCCESS,
        )
        self.lbl_time_cur.pack(side="left")

        self.lbl_time_total = ctk.CTkLabel(
            timeline_frame,
            text="00:00",
            font=FONT_CODE,
            text_color=TEXT_MUTED,
        )
        self.lbl_time_total.pack(side="right")

        self.timeline_slider = ctk.CTkSlider(
            self.right_p_panel,
            from_=0,
            to=100,
            height=14,
            corner_radius=9999,
            progress_color=ACCENT_PRIMARY,
            button_color=ACCENT_PRIMARY,
            button_hover_color=ACCENT_HOVER,
            fg_color=SURFACE_INPUT,
            command=self._on_slider_change,
        )
        self.timeline_slider.pack(fill="x", padx=SPACE_LG, pady=(2, 6))
        self.timeline_slider.set(0)
        self.timeline_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "is_user_dragging_slider", True))
        self.timeline_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # Control Buttons Row (Modern Round Controls - Zero Emoji)
        ctrl_frame = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        ctrl_frame.pack(pady=(4, 6))

        self.btn_prev = ctk.CTkButton(
            ctrl_frame,
            text="",
            image=get_icon("skip-back", size=(18, 18)),
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            width=40,
            height=40,
            corner_radius=20,
            command=self._player_prev_track,
        )
        self.btn_prev.pack(side="left", padx=4)

        self.btn_play_pause = ctk.CTkButton(
            ctrl_frame,
            text="",
            image=get_icon("play", size=(22, 22)),
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
            width=52,
            height=52,
            corner_radius=26,
            command=self._player_play_pause_toggle,
        )
        self.btn_play_pause.pack(side="left", padx=8)

        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="",
            image=get_icon("stop", size=(16, 16)),
            fg_color=SURFACE_ELEVATED,
            hover_color=STATUS_DANGER,
            width=40,
            height=40,
            corner_radius=20,
            command=self._player_stop,
        )
        self.btn_stop.pack(side="left", padx=4)

        self.btn_next = ctk.CTkButton(
            ctrl_frame,
            text="",
            image=get_icon("skip-forward", size=(18, 18)),
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            width=40,
            height=40,
            corner_radius=20,
            command=self._player_next_track,
        )
        self.btn_next.pack(side="left", padx=4)

        # Loop Toggle & Volume Control
        opt_row = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        opt_row.pack(fill="x", padx=SPACE_LG, pady=(4, 6))

        self.btn_loop = ctk.CTkButton(
            opt_row,
            text=" Loop: OFF",
            image=get_icon("repeat", size=(14, 14)),
            font=FONT_CAPTION,
            fg_color=SURFACE_INPUT,
            hover_color=SURFACE_ELEVATED,
            text_color=TEXT_MUTED,
            height=30,
            width=95,
            corner_radius=RADIUS_BUTTON,
            command=self._player_toggle_loop,
        )
        self.btn_loop.pack(side="left")

        # Volume Slider with Vector Icon
        vol_frame = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        vol_frame.pack(fill="x", padx=SPACE_LG, pady=(4, SPACE_MD))

        self.lbl_vol_icon = ctk.CTkLabel(
            vol_frame,
            text=" Volume:",
            image=get_icon("volume", size=(16, 16)),
            compound="left",
            font=FONT_CAPTION,
            text_color=TEXT_SECONDARY,
        )
        self.lbl_vol_icon.pack(side="left", padx=(0, 6))

        self.vol_slider = ctk.CTkSlider(
            vol_frame,
            from_=0,
            to=100,
            height=12,
            corner_radius=9999,
            progress_color=STATUS_INFO,
            button_color=STATUS_INFO,
            button_hover_color="#38bdf8",
            fg_color=SURFACE_INPUT,
            command=self._player_set_volume,
        )
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.vol_slider.set(70)

        self.lbl_vol_val = ctk.CTkLabel(
            vol_frame,
            text="70%",
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
            width=36,
        )
        self.lbl_vol_val.pack(side="right")

    def _sync_active_chapter(self, cur_pos_ms):
        if not self.current_chapters:
            return
        active_idx = -1
        for i, ch in enumerate(self.current_chapters):
            st_ms = ch.get("start_ms", 0)
            if cur_pos_ms >= st_ms:
                active_idx = i
            else:
                break
        if active_idx != self.active_chapter_index and active_idx >= 0:
            self.active_chapter_index = active_idx
            self._highlight_active_chapter(active_idx)

    def _highlight_active_chapter(self, index):
        if not hasattr(self, "chap_tree"):
            return
        children = self.chap_tree.get_children()
        if 0 <= index < len(children):
            item_id = children[index]
            self.chap_tree.selection_set(item_id)
            self.chap_tree.see(item_id)

    def _on_chapter_double_click(self, event):
        selected = self.chap_tree.selection()
        if not selected or not self.current_chapters:
            return
        item_id = selected[0]
        try:
            ch_idx = int(item_id)
            if 0 <= ch_idx < len(self.current_chapters):
                target_ms = self.current_chapters[ch_idx].get("start_ms", 0)
                self._player_seek_to_ms(target_ms)
        except ValueError:
            pass

    def _refresh_playlist_view(self):
        """
        Memuat ulang daftar audio yang tersedia di riwayat serta memindai
        seluruh isi folder penyimpanan unduhan secara rekursif (termasuk semua subfolder).
        """
        if hasattr(self, "_chapters_cache"):
            self._chapters_cache.clear()
        self.player_tree.delete(*self.player_tree.get_children())
        self.playlist_items = []
        seen_paths = set()

        histories = load_history()
        hist_by_rjid = {}
        hist_by_path = {}

        for h in histories:
            r_id = h.get("rjid", "").strip().upper()
            if r_id and r_id != "-":
                hist_by_rjid[r_id] = h
            out_p = h.get("output_path", "")
            if out_p:
                hist_by_path[os.path.normcase(os.path.abspath(out_p))] = h

        # 1. Masukkan berkas dari riwayat yang berkas fisiknya masih ada di disk
        for h in histories:
            fpath = h.get("output_path", "")
            if fpath and os.path.exists(fpath):
                norm_p = os.path.normcase(os.path.abspath(fpath))
                if norm_p not in seen_paths:
                    seen_paths.add(norm_p)
                    try:
                        fsize = os.path.getsize(fpath)
                        sz_str = f"{fsize / (1024 * 1024 * 1024):.2f} GB" if fsize >= 1024**3 else f"{fsize / (1024 * 1024):.1f} MB"
                    except OSError:
                        sz_str = "-"

                    item = {
                        "rjid": h.get("rjid", "-"),
                        "title": h.get("title", os.path.basename(fpath)),
                        "cv": h.get("cv", "-"),
                        "circle": h.get("circle", "-"),
                        "file_size": sz_str,
                        "output_path": os.path.abspath(fpath),
                        "cover_url": h.get("cover_url", ""),
                    }
                    self.playlist_items.append(item)

        # 2. Pindai folder download secara rekursif untuk mendeteksi file audio
        download_dir = os.path.abspath(get_download_dir())
        AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"}

        if os.path.exists(download_dir):
            for root, dirs, files in os.walk(download_dir, followlinks=False):
                # Lewati direktori sistem / cache / temp / recycle bin
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".")
                    and not d.startswith("temp_")
                    and d.lower() not in {"$recycle.bin", "system volume information"}
                ]

                # Cari gambar cover lokal jika ada di subfolder yang sama
                local_cover = None
                img_candidates = [
                    f for f in files
                    if os.path.splitext(f)[1].lower() in {".jpg", ".jpeg", ".png", ".webp"}
                ]
                if img_candidates:
                    pref_covers = [
                        f for f in img_candidates
                        if any(k in f.lower() for k in ["cover", "folder", "thumb", "main", "img", "front"])
                    ]
                    chosen_img = pref_covers[0] if pref_covers else img_candidates[0]
                    local_cover = os.path.abspath(os.path.join(root, chosen_img))

                for f in sorted(files):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in AUDIO_EXTS:
                        full_path = os.path.abspath(os.path.join(root, f))
                        norm_p = os.path.normcase(full_path)
                        if norm_p in seen_paths:
                            continue
                        seen_paths.add(norm_p)

                        # Deteksi ID RJ dari nama berkas atau nama subfolder
                        match = re.search(r"(RJ\d{6,8}|VJ\d{6,8}|BJ\d{6,8})", f, re.IGNORECASE)
                        if not match:
                            match = re.search(r"(RJ\d{6,8}|VJ\d{6,8}|BJ\d{6,8})", os.path.basename(root), re.IGNORECASE)

                        rjid_detected = match.group(1).upper() if match else "-"
                        ref_meta = hist_by_path.get(norm_p) or (hist_by_rjid.get(rjid_detected) if rjid_detected != "-" else None)

                        # Hitung ukuran berkas
                        try:
                            fsize = os.path.getsize(full_path)
                            if fsize >= 1024 * 1024 * 1024:
                                size_str = f"{fsize / (1024 * 1024 * 1024):.2f} GB"
                            else:
                                size_str = f"{fsize / (1024 * 1024):.1f} MB"
                        except OSError:
                            size_str = "-"

                        # Judul karya
                        base_name_no_ext = os.path.splitext(f)[0]
                        clean_name = re.sub(r"^\[(?:RJ|VJ|BJ)\d+\]\s*", "", base_name_no_ext).strip()
                        rel_sub = os.path.relpath(root, download_dir)
                        if rel_sub != "." and not clean_name.lower().startswith(rel_sub.lower()):
                            title_display = f"{clean_name} ({rel_sub})"
                        else:
                            title_display = clean_name or base_name_no_ext

                        if ref_meta and ref_meta.get("title"):
                            title_to_use = ref_meta.get("title")
                        else:
                            title_to_use = title_display

                        cv_display = ref_meta.get("cv", "-") if ref_meta else "-"
                        circle_display = ref_meta.get("circle", "-") if ref_meta else "-"
                        cover_to_use = local_cover or (ref_meta.get("cover_url", "") if ref_meta else "")
                        if not cover_to_use and rjid_detected != "-":
                            cover_to_use = f"https://pic.weeabo0.xyz/{rjid_detected}_img_main.jpg"

                        item = {
                            "rjid": rjid_detected,
                            "title": title_to_use,
                            "cv": cv_display,
                            "circle": circle_display,
                            "file_size": size_str,
                            "output_path": full_path,
                            "cover_url": cover_to_use,
                        }
                        self.playlist_items.append(item)

        # Masukkan seluruh item ke Treeview Playlist
        for idx, item in enumerate(self.playlist_items):
            self.player_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    item.get("rjid", "-"),
                    item.get("title", "-"),
                    item.get("cv", "-"),
                    item.get("file_size", "-"),
                ),
            )

        if hasattr(self, "lbl_p_title"):
            self.lbl_p_title.configure(text=f"{t('lbl_playlist')} ({len(self.playlist_items)})")

    def _on_playlist_select(self, event):
        selected = self.player_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.playlist_items):
            item = self.playlist_items[idx]
            self.lbl_p_track_title.configure(text=item.get("title", "-"))
            self.lbl_p_track_sub.configure(text=f"{item.get('rjid', '-')} • {item.get('cv', '-')}")

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
        if not file_path or not os.path.isfile(file_path):
            show_dark_error(self, "Error Audio", "Berkas audio tidak ditemukan atau telah dipindahkan.")
            return

        self._player_stop()

        self.current_playing_file = file_path
        self.current_playing_meta = meta or {}
        rjid = self.current_playing_meta.get("rjid", "-")
        title = self.current_playing_meta.get("title", os.path.basename(file_path))
        cv = self.current_playing_meta.get("cv", "-")

        self.lbl_p_track_title.configure(text=title)
        self.lbl_p_track_sub.configure(text=f"{rjid} • {cv}")

        # Render Cover Art
        cover_cand = self.current_playing_meta.get("cover_url", "")
        self._render_player_cover(cover_cand)

        # Hitung durasi audio akurat via FFmpeg
        dur_ms = self._get_precise_duration_ms(file_path)
        self.player_duration_ms = dur_ms

        # Evaluasi Engine Pemutar
        file_ext = os.path.splitext(file_path)[1].lower()
        use_mf = False
        if sys.platform == "win32" and file_ext in [".m4a", ".aac", ".mp3", ".wav"]:
            if hasattr(self, "mf_player") and self.mf_player.is_available():
                if self.mf_player.load(file_path):
                    use_mf = True

        self.use_mf_player = use_mf

        if self.use_mf_player:
            self.mf_player.play()
            cur_vol = int(self.vol_slider.get())
            self.mf_player.set_volume(cur_vol)
            self.is_playing = True
            self.is_paused = False
            self.btn_play_pause.configure(image=get_icon("pause", size=(22, 22)), text="")
            self.lbl_time_total.configure(text=self._format_time(dur_ms))
            self._load_track_chapters(file_path, rjid=rjid)
            self._player_schedule_tick()
            return

        # Fallback ke Windows MCI
        short_name = "asmr_player"
        self._mci_send(f"close {short_name}")
        err, _ = self._mci_send(f'open "{file_path}" type mpegvideo alias {short_name}')
        if err != 0:
            err, _ = self._mci_send(f'open "{file_path}" alias {short_name}')

        if err != 0:
            show_dark_error(self, "Error Pemutar", f"Format audio tidak didukung oleh Windows Media Player MCI. (Error code: {err})")
            return

        self._mci_send(f"set {short_name} time format milliseconds")
        _, len_str = self._mci_send(f"status {short_name} length")
        try:
            mci_dur = int(len_str)
        except ValueError:
            mci_dur = 0

        self.mci_raw_duration_ms = mci_dur
        if self.player_duration_ms <= 0:
            self.player_duration_ms = mci_dur

        self._mci_send(f"play {short_name}")
        self.is_playing = True
        self.is_paused = False
        self.btn_play_pause.configure(image=get_icon("pause", size=(22, 22)), text="")
        self.lbl_time_total.configure(text=self._format_time(self.player_duration_ms))

        # Set Volume MCI Awal
        cur_vol = int(self.vol_slider.get())
        self._player_set_volume(cur_vol)

        # Muat daftar bab
        self._load_track_chapters(file_path, rjid=rjid)
        self._player_schedule_tick()

    def _render_player_cover(self, cover_cand):
        rjid = self.current_playing_meta.get("rjid", "")
        cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg") if rjid and rjid != "-" else ""
        if cache_file and os.path.exists(cache_file):
            try:
                pil_img = Image.open(cache_file)
                pil_img.thumbnail((290, 185))
                self.player_preview_image = ImageTk.PhotoImage(pil_img)
                self.player_canvas.delete("all")
                self.player_canvas.create_image(145, 92, image=self.player_preview_image)
                return
            except Exception:
                pass

        if cover_cand:
            # 1. Cek apakah cover_cand adalah berkas lokal di disk
            if os.path.isfile(cover_cand):
                try:
                    pil_img = Image.open(cover_cand)
                    pil_img.thumbnail((290, 185))
                    self.player_preview_image = ImageTk.PhotoImage(pil_img)
                    self.player_canvas.delete("all")
                    self.player_canvas.create_image(145, 92, image=self.player_preview_image)
                    return
                except Exception:
                    pass

            # 2. Jika merupakan URL web (HTTP/HTTPS)
            def _apply_player_cover(p_img):
                try:
                    if hasattr(self, "player_canvas") and self.player_canvas.winfo_exists():
                        self.player_preview_image = ImageTk.PhotoImage(p_img)
                        self.player_canvas.delete("all")
                        self.player_canvas.create_image(145, 92, image=self.player_preview_image)
                except Exception:
                    pass

            def _load_c():
                try:
                    req = urllib.request.Request(cover_cand, headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((290, 185))
                    if cache_file:
                        os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                        pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                    self.after(0, lambda: _apply_player_cover(pil_img))
                except Exception:
                    pass
            threading.Thread(target=_load_c, daemon=True).start()
        else:
            self.player_canvas.delete("all")
            self.player_canvas.create_text(145, 92, text="Tidak ada cover", fill=TEXT_MUTED, font=FONT_BODY)

    def _load_track_chapters(self, file_path, rjid=""):
        self.chap_tree.delete(*self.chap_tree.get_children())
        self.current_chapters = []
        self.active_chapter_index = -1

        chaps = extract_chapters_from_audio(file_path)
        if chaps:
            self.current_chapters = chaps
            for i, ch in enumerate(chaps):
                t_str = self._format_time(ch.get("start_ms", 0))
                self.chap_tree.insert("", "end", iid=str(i), values=(t_str, ch.get("title", f"Chapter {i+1}")))
            return

        cue_path = os.path.splitext(file_path)[0] + ".cue"
        if os.path.exists(cue_path):
            chaps = extract_chapters_from_audio(cue_path)
            if chaps:
                self.current_chapters = chaps
                for i, ch in enumerate(chaps):
                    t_str = self._format_time(ch.get("start_ms", 0))
                    self.chap_tree.insert("", "end", iid=str(i), values=(t_str, ch.get("title", f"Track {i+1}")))
                return

        if rjid and rjid not in self._syncing_chaps:
            self._syncing_chaps.add(rjid)
            threading.Thread(target=self._fetch_and_create_cue_background, args=(file_path, rjid), daemon=True).start()

    def _fetch_and_create_cue_background(self, file_path, rjid):
        meta = self.current_playing_meta
        chaps = fetch_japaneseasmr_chapters(rjid, meta=meta)
        if chaps:
            write_cue_sheet(file_path, chaps, meta=meta)
            def _apply():
                if self.current_playing_file == file_path:
                    self._load_track_chapters(file_path, rjid=rjid)
            self.after(0, _apply)

    def _get_precise_duration_ms(self, file_path):
        sec = get_precise_duration_seconds(file_path)
        return int(sec * 1000)

    def _mci_send(self, cmd):
        return mci_send(cmd)

    def _player_play_pause_toggle(self):
        if not self.current_playing_file:
            self._player_play_selected()
            return

        if self.is_playing:
            if self.use_mf_player:
                self.mf_player.pause()
            else:
                self._mci_send("pause asmr_player")
            self.is_playing = False
            self.is_paused = True
            self.btn_play_pause.configure(image=get_icon("play", size=(22, 22)), text="")
        else:
            if self.is_paused:
                if self.use_mf_player:
                    self.mf_player.play()
                else:
                    self._mci_send("resume asmr_player")
            else:
                if self.use_mf_player:
                    self.mf_player.play()
                else:
                    self._mci_send("play asmr_player")
            self.is_playing = True
            self.is_paused = False
            self.btn_play_pause.configure(image=get_icon("pause", size=(22, 22)), text="")
            self._player_schedule_tick()

    def _player_stop(self):
        if self.use_mf_player:
            self.mf_player.stop()
        else:
            self._mci_send("stop asmr_player")
            self._mci_send("seek asmr_player to start")

        self.is_playing = False
        self.is_paused = False
        self.btn_play_pause.configure(image=get_icon("play", size=(22, 22)), text="")
        self.timeline_slider.set(0)
        self.lbl_time_cur.configure(text="00:00")

    def _on_slider_change(self, val):
        self.is_user_dragging_slider = True
        try:
            pct = float(val)
            target_ms = int((pct / 100.0) * self.player_duration_ms)
            self.lbl_time_cur.configure(text=self._format_time(target_ms))
        except Exception:
            pass

    def _on_slider_release(self, event=None):
        pct = float(self.timeline_slider.get())
        target_ms = int((pct / 100.0) * self.player_duration_ms)
        self._player_seek_to_ms(target_ms)
        self.is_user_dragging_slider = False

    def _player_seek_to_ms(self, pos_ms):
        if not self.current_playing_file or self.player_duration_ms <= 0:
            return
        target_ms = max(0, min(self.player_duration_ms, pos_ms))

        if self.use_mf_player:
            self.mf_player.seek(target_ms / 1000.0)
        else:
            ref_len = self.mci_raw_duration_ms if self.mci_raw_duration_ms > 0 else self.player_duration_ms
            ratio = max(0.0, min(1.0, target_ms / float(self.player_duration_ms)))
            mci_target = int(ratio * ref_len)
            self._mci_send(f"seek asmr_player to {mci_target}")
            if self.is_playing:
                self._mci_send("play asmr_player")

        pct = (target_ms / float(self.player_duration_ms)) * 100.0
        self.timeline_slider.set(pct)
        self.lbl_time_cur.configure(text=self._format_time(target_ms))
        self._sync_active_chapter(target_ms)

    def _player_set_volume(self, val):
        vol_pct = int(float(val))
        if hasattr(self, "lbl_vol_val"):
            self.lbl_vol_val.configure(text=f"{vol_pct}%")
        if getattr(self, "use_mf_player", False):
            self.mf_player.set_volume(vol_pct)
        else:
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
            self.btn_loop.configure(text=" Loop: ON", image=get_icon("repeat", size=(14, 14)), text_color=STATUS_SUCCESS, fg_color=SURFACE_ELEVATED)
        else:
            self.btn_loop.configure(text=" Loop: OFF", image=get_icon("repeat", size=(14, 14)), text_color=TEXT_MUTED, fg_color=SURFACE_INPUT)

    def _player_tick(self):
        if not self.is_playing or not self.current_playing_file:
            return

        if self.use_mf_player:
            pos_sec = self.mf_player.get_position_sec()
            pos_ms = int(pos_sec * 1000)
            dur_ms = self.player_duration_ms
            ratio = max(0.0, min(1.0, pos_ms / float(dur_ms))) if dur_ms > 0 else 0.0

            if not self.is_user_dragging_slider and dur_ms > 0:
                pct = ratio * 100.0
                self.timeline_slider.set(pct)
                self.lbl_time_cur.configure(text=self._format_time(pos_ms))
                self._sync_active_chapter(pos_ms)

            if dur_ms > 0 and pos_ms >= dur_ms - 500:
                if self.is_looping:
                    self.mf_player.seek(0)
                    self.mf_player.play()
                    self._player_schedule_tick()
                else:
                    self._player_next_track()
                return

            self._player_schedule_tick()
            return

        _, pos_str = self._mci_send("status asmr_player position")
        _, mode_str = self._mci_send("status asmr_player mode")

        try:
            mci_pos_ms = int(pos_str)
        except ValueError:
            mci_pos_ms = 0

        ref_len = self.mci_raw_duration_ms if self.mci_raw_duration_ms > 0 else self.player_duration_ms
        ratio = max(0.0, min(1.0, mci_pos_ms / float(ref_len))) if ref_len > 0 else 0.0
        real_pos_ms = int(ratio * self.player_duration_ms)

        if not self.is_user_dragging_slider and self.player_duration_ms > 0:
            pct = ratio * 100.0
            self.timeline_slider.set(pct)
            self.lbl_time_cur.configure(text=self._format_time(real_pos_ms))
            self._sync_active_chapter(real_pos_ms)

        if mode_str == "stopped" or (ref_len > 0 and mci_pos_ms >= ref_len - 500):
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
        return format_time(ms)
