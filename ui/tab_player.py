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
    discover_all_audio_tracks,
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
from ui.player_engine import (
    NativeMFPlayer,
    format_time,
    get_precise_duration_ms,
    mci_send,
)
from ui.theme import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BORDER_ACTIVE,
    BORDER_SUBTLE,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CAPTION,
    FONT_CODE,
    FONT_SUBTITLE,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_ROUND,
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


class PlayerTabMixin:
    """Mixin untuk membangun antarmuka dan logika pemutar audio (Player Tab)."""
    def _build_player_tab(self):
        container = self.tab_player

        # Layout 2 Kolom: Kiri (Playlist & Chapters), Kanan (Now Playing & Controls)
        main_container = ctk.CTkFrame(container, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        left_p_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        left_p_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # 1. Playlist Card
        playlist_card = ctk.CTkFrame(
            left_p_panel,
            corner_radius=RADIUS_LG,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        playlist_card.pack(fill="both", expand=True, pady=(0, 10))

        p_header = ctk.CTkFrame(playlist_card, fg_color="transparent")
        p_header.pack(fill="x", padx=14, pady=(10, 8))

        self.lbl_p_title = ctk.CTkLabel(
            p_header,
            text=f"🎵 {t('lbl_playlist')}",
            font=FONT_SUBTITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_p_title.pack(side="left")

        self.refresh_p_btn = ctk.CTkButton(
            p_header,
            text=f"🔄 {t('btn_refresh_playlist')}",
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_MD,
            height=30,
            width=100,
            command=self._refresh_playlist_view,
        )
        self.refresh_p_btn.pack(side="right")

        # Treeview Playlist
        tree_p_container = ctk.CTkFrame(
            playlist_card,
            corner_radius=RADIUS_MD,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        tree_p_container.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        cols = ("rjid", "title", "cv", "size")
        self.player_tree = ttk.Treeview(tree_p_container, columns=cols, show="headings", selectmode="browse", style="Treeview")
        self.player_tree.heading("rjid", text=t("col_rjid"), anchor="center")
        self.player_tree.heading("title", text=t("col_play_title"), anchor="w")
        self.player_tree.heading("cv", text=t("col_hist_cv"), anchor="w")
        self.player_tree.heading("size", text=t("col_play_duration"), anchor="center")

        self.player_tree.column("rjid", width=95, anchor="center")
        self.player_tree.column("title", width=240, anchor="w")
        self.player_tree.column("cv", width=120, anchor="w")
        self.player_tree.column("size", width=75, anchor="center")

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
            corner_radius=RADIUS_LG,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.chap_frame.pack(fill="x", pady=0)
        self.chap_frame.pack_propagate(False)

        chap_header = ctk.CTkFrame(self.chap_frame, fg_color="transparent")
        chap_header.pack(fill="x", padx=14, pady=(8, 4))

        self.lbl_chap_title = ctk.CTkLabel(
            chap_header,
            text=f"📑 {t('lbl_chapters')}",
            font=FONT_SUBTITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_chap_title.pack(side="left")

        chap_tree_container = ctk.CTkFrame(
            self.chap_frame,
            corner_radius=RADIUS_MD,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        chap_tree_container.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        c_cols = ("time", "title")
        self.chap_tree = ttk.Treeview(chap_tree_container, columns=c_cols, show="headings", selectmode="browse", style="Treeview")
        self.chap_tree.heading("time", text=t("col_chap_time"), anchor="center")
        self.chap_tree.heading("title", text=t("col_chap_title"), anchor="w")
        self.chap_tree.column("time", width=90, anchor="center")
        self.chap_tree.column("title", width=340, anchor="w")

        chap_scroll = ttk.Scrollbar(chap_tree_container, orient="vertical", command=self.chap_tree.yview, style="Vertical.TScrollbar")
        self.chap_tree.configure(yscrollcommand=chap_scroll.set)

        self.chap_tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        chap_scroll.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.chap_tree.bind("<Double-1>", self._on_chapter_double_click)

        # 3. Panel Kanan: Now Playing Screen & Controls
        self.right_p_panel = ctk.CTkFrame(
            main_container,
            width=330,
            corner_radius=RADIUS_LG,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.right_p_panel.pack(side="right", fill="both", pady=0)
        self.right_p_panel.pack_propagate(False)

        np_header = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        np_header.pack(fill="x", padx=14, pady=(12, 6))

        self.lbl_now_playing_title = ctk.CTkLabel(
            np_header,
            text=f"🎧 {t('lbl_playlist')}",
            font=FONT_SUBTITLE,
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
        self.player_canvas.pack(pady=4, padx=14)
        self.player_canvas.create_text(
            145, 92, text="Pilih audio untuk memutar", fill=TEXT_MUTED, font=FONT_BODY
        )

        # Track Info (Title, RJID, CV)
        track_info_frame = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        track_info_frame.pack(fill="x", padx=16, pady=(6, 4))

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
        timeline_frame.pack(fill="x", padx=16, pady=(6, 2))

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
            corner_radius=RADIUS_SM,
            progress_color=ACCENT_PRIMARY,
            button_color=ACCENT_PRIMARY,
            button_hover_color=ACCENT_HOVER,
            fg_color=SURFACE_INPUT,
            command=self._on_slider_change,
        )
        self.timeline_slider.pack(fill="x", padx=16, pady=(2, 6))
        self.timeline_slider.set(0)
        self.timeline_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "is_user_dragging_slider", True))
        self.timeline_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # Control Buttons Row (Modern Round Controls)
        ctrl_frame = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        ctrl_frame.pack(pady=(4, 6))

        self.btn_prev = ctk.CTkButton(
            ctrl_frame,
            text="⏮",
            font=("Segoe UI", 13, "bold"),
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            width=38,
            height=38,
            corner_radius=19,
            command=self._player_prev_track,
        )
        self.btn_prev.pack(side="left", padx=4)

        self.btn_play_pause = ctk.CTkButton(
            ctrl_frame,
            text="▶",
            font=("Segoe UI", 16, "bold"),
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
            text_color="#ffffff",
            width=50,
            height=50,
            corner_radius=25,
            command=self._player_play_pause_toggle,
        )
        self.btn_play_pause.pack(side="left", padx=6)

        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="■",
            font=("Segoe UI", 12, "bold"),
            fg_color=SURFACE_ELEVATED,
            hover_color=STATUS_DANGER,
            text_color=TEXT_PRIMARY,
            width=38,
            height=38,
            corner_radius=19,
            command=self._player_stop,
        )
        self.btn_stop.pack(side="left", padx=4)

        self.btn_next = ctk.CTkButton(
            ctrl_frame,
            text="⏭",
            font=("Segoe UI", 13, "bold"),
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            width=38,
            height=38,
            corner_radius=19,
            command=self._player_next_track,
        )
        self.btn_next.pack(side="left", padx=4)

        # Loop Toggle & Volume Control
        opt_row = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        opt_row.pack(fill="x", padx=16, pady=(4, 6))

        self.btn_loop = ctk.CTkButton(
            opt_row,
            text="🔁 Loop: OFF",
            font=FONT_CAPTION,
            fg_color=SURFACE_INPUT,
            hover_color=SURFACE_ELEVATED,
            text_color=TEXT_MUTED,
            height=28,
            width=85,
            corner_radius=RADIUS_MD,
            command=self._player_toggle_loop,
        )
        self.btn_loop.pack(side="left")

        # Volume Slider
        vol_frame = ctk.CTkFrame(self.right_p_panel, fg_color="transparent")
        vol_frame.pack(fill="x", padx=16, pady=(4, 8))

        self.lbl_vol_icon = ctk.CTkLabel(
            vol_frame,
            text="🔊 Volume:",
            font=FONT_CAPTION,
            text_color=TEXT_SECONDARY,
        )
        self.lbl_vol_icon.pack(side="left", padx=(0, 6))

        self.vol_slider = ctk.CTkSlider(
            vol_frame,
            from_=0,
            to=100,
            height=12,
            corner_radius=RADIUS_SM,
            progress_color=STATUS_INFO,
            button_color=STATUS_INFO,
            button_hover_color="#38bdf8",
            fg_color=SURFACE_INPUT,
            command=self._player_set_volume,
        )
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.vol_slider.set(80)

        self.lbl_vol_val = ctk.CTkLabel(
            vol_frame,
            text="80%",
            font=FONT_CODE,
            text_color=STATUS_INFO,
            width=35,
        )
        self.lbl_vol_val.pack(side="right")

    # ==========================================
    # PEMUTAR AUDIO BAWAAN
    # ==========================================
    def _get_precise_duration_ms(self, file_path):
        return get_precise_duration_ms(file_path)

    def _mci_send(self, command):
        return mci_send(command)

    def _refresh_playlist_view(self):
        """Memuat ulang daftar audio yang tersedia di riwayat serta memindai folder download."""
        self.player_tree.delete(*self.player_tree.get_children())
        self.playlist_items.clear()

        # 1. Masukkan berkas dari Riwayat resmi
        histories = load_history()
        added_paths = set()
        for h in histories:
            f_path = h.get("output_path", "")
            if f_path and os.path.isfile(f_path) and f_path not in added_paths:
                added_paths.add(f_path)
                item = {
                    "rjid": h.get("rjid", "-"),
                    "title": h.get("title", os.path.basename(f_path)),
                    "cv": h.get("cv", "-"),
                    "output_path": f_path,
                    "cover_url": h.get("cover_url", ""),
                    "genre": h.get("genre", "-"),
                }
                self.playlist_items.append(item)

        # 2. Pindai folder download secara rekursif
        d_dir = get_download_dir()
        if os.path.exists(d_dir):
            for root, _, files in os.walk(d_dir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in [".m4a", ".mp3", ".flac", ".wav", ".aac"]:
                        full_p = os.path.join(root, f)
                        if full_p not in added_paths:
                            added_paths.add(full_p)
                            # Coba tebak RJID dari nama file / folder
                            m_rj = re.search(r'(RJ\d{6,8})', f, re.IGNORECASE)
                            if not m_rj:
                                m_rj = re.search(r'(RJ\d{6,8})', root, re.IGNORECASE)
                            rjid_found = m_rj.group(1).upper() if m_rj else "-"
                            clean_t = os.path.splitext(f)[0]
                            clean_t = re.sub(r'\[RJ\d+\]\s*', '', clean_t, flags=re.IGNORECASE)

                            item = {
                                "rjid": rjid_found,
                                "title": clean_t,
                                "cv": "-",
                                "output_path": full_p,
                                "cover_url": "",
                                "genre": "-",
                            }
                            self.playlist_items.append(item)

        # 3. Tampilkan ke Treeview
        for idx, item in enumerate(self.playlist_items):
            f_path = item.get("output_path", "")
            dur_str = "-"
            if os.path.exists(f_path):
                sz = os.path.getsize(f_path)
                dur_str = f"{sz / (1024 * 1024):.1f} MB"

            self.player_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(item.get("rjid", "-"), item.get("title", "-"), item.get("cv", "-"), dur_str),
            )

        if hasattr(self, "lbl_p_title"):
            self.lbl_p_title.configure(text=f"🎵 {t('lbl_playlist')} ({len(self.playlist_items)})")

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
            self.btn_play_pause.configure(text="⏸")
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
        self.btn_play_pause.configure(text="⏸")
        self.lbl_time_total.configure(text=self._format_time(self.player_duration_ms))

        # Set Volume MCI Awal
        cur_vol = int(self.vol_slider.get())
        self._player_set_volume(cur_vol)

        # Muat daftar bab
        self._load_track_chapters(file_path, rjid=rjid)
        self._player_schedule_tick()

    def _render_player_cover(self, image_url_or_path):
        """Memuat gambar cover beresolusi tinggi ke canvas player."""
        self.player_canvas.delete("all")
        cover_url = image_url_or_path
        rjid = self.current_playing_meta.get("rjid", "-")
        cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg") if rjid and rjid != "-" else None

        # 1. Coba dari cache lokal
        if cache_file and os.path.exists(cache_file):
            try:
                pil_img = Image.open(cache_file)
                pil_img.thumbnail((290, 185))
                self.player_preview_image = ImageTk.PhotoImage(pil_img)
                self.player_canvas.create_image(145, 92, image=self.player_preview_image)
                return
            except Exception:
                pass

        # 2. Coba jika berupa berkas lokal
        if cover_url and os.path.isfile(cover_url):
            try:
                pil_img = Image.open(cover_url)
                pil_img.thumbnail((290, 185))
                self.player_preview_image = ImageTk.PhotoImage(pil_img)
                self.player_canvas.create_image(145, 92, image=self.player_preview_image)
                return
            except Exception:
                pass

        # 3. Muat gambar dari jaringan
        if cover_url and (cover_url.startswith("http://") or cover_url.startswith("https://")):
            def load_cover():
                try:
                    cover_ref = "https://www.dlsite.com" if "dlsite" in cover_url else ("https://asmr.one/" if "asmr.one" in cover_url else REFERER)
                    req = urllib.request.Request(
                        cover_url,
                        headers={
                            "Referer": cover_ref,
                            "User-Agent": USER_AGENT,
                            "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((290, 185))
                    os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                    if rjid and rjid != "-":
                        pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                    self.player_preview_image = ImageTk.PhotoImage(pil_img)
                    self.player_canvas.delete("all")
                    self.player_canvas.create_image(145, 92, image=self.player_preview_image)
                except Exception:
                    pass

            threading.Thread(target=load_cover, daemon=True).start()
        else:
            self.player_canvas.create_text(145, 92, text="Tidak ada cover", fill=TEXT_MUTED, font=FONT_BODY)

    def _get_current_pos_ms(self):
        if not self.is_playing and not self.is_paused:
            return 0
        if self.use_mf_player:
            return int(self.mf_player.get_position_sec() * 1000)
        _, pos_str = self._mci_send("status asmr_player position")
        try:
            mci_pos_ms = int(pos_str)
        except ValueError:
            mci_pos_ms = 0
        ref_len = self.mci_raw_duration_ms if self.mci_raw_duration_ms > 0 else self.player_duration_ms
        if ref_len > 0:
            ratio = max(0.0, min(1.0, mci_pos_ms / float(ref_len)))
        else:
            ratio = 0.0
        return int(ratio * self.player_duration_ms)

    def _load_track_chapters(self, file_path, rjid=None):
        """Memuat daftar bab dari CUE sheet, tag audio internal, atau sync JapaneseASMR."""
        self.chap_tree.delete(*self.chap_tree.get_children())
        self.current_chapters.clear()
        self.active_chapter_index = -1

        norm_path = os.path.normpath(file_path)
        if norm_path in self._chapters_cache:
            mtime, cached_chaps = self._chapters_cache[norm_path]
            curr_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            if curr_mtime == mtime:
                self.current_chapters = cached_chaps
                for ch in self.current_chapters:
                    t_str = self._format_time(ch["start_ms"])
                    self.chap_tree.insert("", "end", iid=str(ch["index"] - 1), values=(t_str, ch["title"]))
                return

        chapters = extract_chapters_from_audio(file_path)
        if chapters:
            self.current_chapters = chapters
            for ch in chapters:
                t_str = self._format_time(ch["start_ms"])
                self.chap_tree.insert("", "end", iid=str(ch["index"] - 1), values=(t_str, ch["title"]))
            curr_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            self._chapters_cache[norm_path] = (curr_mtime, chapters)
            return

        self.chap_tree.insert("", "end", iid="none", values=("-", "Audio ini tidak memiliki bab/chapter"))

        m_rj = re.search(r'(RJ\d{6,8})', os.path.basename(file_path), re.IGNORECASE)
        if not m_rj and rjid and rjid != "-":
            m_rj = re.search(r'(RJ\d{6,8})', rjid, re.IGNORECASE)

        sync_set = getattr(self, "_syncing_chaps", None)
        if sync_set is None:
            self._syncing_chaps = set()
            sync_set = self._syncing_chaps

        if m_rj and norm_path not in sync_set:
            sync_set.add(norm_path)
            rj_cand = m_rj.group(1).upper()

            def _bg_sync_chapters(target_file, rj):
                try:
                    j_ch = fetch_japaneseasmr_chapters(rj)
                    if j_ch and len(j_ch) > 1:
                        tot_sec = get_precise_duration_seconds(target_file)
                        c_list = []
                        for i, ch in enumerate(j_ch):
                            s_ms = ch["start"]
                            if i + 1 < len(j_ch):
                                e_ms = j_ch[i + 1]["start"]
                            else:
                                e_ms = int(tot_sec * 1000) if tot_sec > 0 else (s_ms + 60000)
                            c_list.append({
                                "start": s_ms,
                                "end": max(s_ms + 1000, e_ms),
                                "title": ch["title"],
                            })
                        is_target_m4a = target_file.lower().endswith(".m4a")
                        if not is_target_m4a:
                            write_cue_sheet(target_file, c_list)
                        ui_chapters = []
                        for idx, c in enumerate(c_list):
                            ui_chapters.append({
                                "index": idx + 1,
                                "title": c.get("title", f"Bab {idx + 1}"),
                                "start_ms": c.get("start", 0),
                            })
                        mtime = os.path.getmtime(target_file) if os.path.exists(target_file) else 0
                        self._chapters_cache[target_file] = (mtime, ui_chapters)
                        self.after(0, lambda: self._load_track_chapters(target_file))
                except Exception:
                    pass

            threading.Thread(target=_bg_sync_chapters, args=(norm_path, rj_cand), daemon=True).start()

    def _on_chapter_double_click(self, event=None):
        sel = self.chap_tree.selection()
        if not sel or sel[0] == "none":
            return
        try:
            c_idx = int(sel[0])
            if 0 <= c_idx < len(self.current_chapters):
                target_ms = self.current_chapters[c_idx]["start_ms"]
                self._player_seek_to_ms(target_ms)
                if not self.is_playing:
                    self._player_play_pause_toggle()
        except ValueError:
            pass

    def _highlight_active_chapter(self, index):
        if not self.current_chapters:
            return
        try:
            iid = str(index)
            if self.chap_tree.exists(iid):
                self.chap_tree.selection_set(iid)
                self.chap_tree.see(iid)
        except Exception:
            pass

    def _sync_active_chapter(self, pos_ms):
        if not self.current_chapters:
            return
        active_idx = -1
        for i, ch in enumerate(self.current_chapters):
            if pos_ms >= ch["start_ms"]:
                active_idx = i
            else:
                break
        if active_idx != self.active_chapter_index and active_idx != -1:
            self.active_chapter_index = active_idx
            self._highlight_active_chapter(active_idx)

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
            self.btn_play_pause.configure(text="▶")
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
            self.btn_play_pause.configure(text="⏸")
            self._player_schedule_tick()

    def _player_stop(self):
        if self.use_mf_player:
            self.mf_player.stop()
        else:
            self._mci_send("stop asmr_player")
            self._mci_send("seek asmr_player to start")

        self.is_playing = False
        self.is_paused = False
        self.btn_play_pause.configure(text="▶")
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
            self.btn_loop.configure(text="🔁 Loop: ON", text_color=STATUS_SUCCESS, fg_color=SURFACE_ELEVATED)
        else:
            self.btn_loop.configure(text="🔁 Loop: OFF", text_color=TEXT_MUTED, fg_color=SURFACE_INPUT)

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
