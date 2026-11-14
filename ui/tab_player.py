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


class PlayerTabMixin:
    """Mixin untuk membangun antarmuka dan logika pemutar audio (Player Tab)."""
    def _build_player_tab(self):
        container = self.tab_player

        # 1. Panel Kiri: Playlist & Koleksi
        left_p_panel = tk.Frame(container, bg="#1e1e2e")
        left_p_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        p_header = tk.Frame(left_p_panel, bg="#1e1e2e")
        p_header.pack(fill="x", pady=(0, 6))

        self.lbl_p_title = tk.Label(
            p_header,
            text="Daftar Putar / Koleksi Audio",
            font=("Segoe UI", 11, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
        )
        self.lbl_p_title.pack(side="left")

        self.refresh_p_btn = tk.Button(
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
        self.refresh_p_btn.pack(side="right")

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
        self.right_p_panel = tk.LabelFrame(
            container,
            text=" Sedang Diputar (Now Playing) ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=380,
        )
        self.right_p_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        self.right_p_panel.pack_propagate(False)

        # Cover Canvas
        self.player_canvas = tk.Canvas(
            self.right_p_panel,
            bg="#282a36",
            width=290,
            height=165,
            bd=0,
            highlightthickness=1,
            highlightbackground="#bd93f9",
        )
        self.player_canvas.pack(pady=(6, 4), padx=12)
        self.player_canvas.create_text(
            145, 82, text="Pilih audio dari playlist untuk memutar", fill="#6272a4", font=("Segoe UI", 9), justify="center"
        )

        # Meta Info
        self.lbl_p_now_title = tk.Label(
            self.right_p_panel,
            text="Belum Ada Audio Diputar",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
            wraplength=340,
            justify="center",
        )
        self.lbl_p_now_title.pack(fill="x", padx=10, pady=(0, 2))

        self.lbl_p_now_sub = tk.Label(
            self.right_p_panel,
            text="CV: - | Circle: -",
            font=("Segoe UI", 8),
            bg="#1e1e2e",
            fg="#a6adc8",
            wraplength=340,
            justify="center",
        )
        self.lbl_p_now_sub.pack(fill="x", padx=10, pady=(0, 4))

        # Timeline Slider & Duration Labels
        timeline_frame = tk.Frame(self.right_p_panel, bg="#1e1e2e")
        timeline_frame.pack(fill="x", padx=12, pady=(0, 2))

        self.lbl_time_cur = tk.Label(timeline_frame, text="00:00", font=("Consolas", 9), bg="#1e1e2e", fg="#50fa7b")
        self.lbl_time_cur.pack(side="left")

        self.lbl_time_total = tk.Label(timeline_frame, text="00:00", font=("Consolas", 9), bg="#1e1e2e", fg="#a6adc8")
        self.lbl_time_total.pack(side="right")

        self.timeline_slider = ttk.Scale(
            self.right_p_panel,
            from_=0,
            to=100,
            orient="horizontal",
            command=self._on_slider_change,
        )
        self.timeline_slider.pack(fill="x", padx=12, pady=(0, 4))
        self.timeline_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "is_user_dragging_slider", True))
        self.timeline_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # Control Buttons Row
        ctrl_frame = tk.Frame(self.right_p_panel, bg="#1e1e2e")
        ctrl_frame.pack(pady=(0, 4))

        self.btn_prev = tk.Button(
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
        self.btn_prev.pack(side="left", padx=3)

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

        self.btn_stop = tk.Button(
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
        self.btn_stop.pack(side="left", padx=3)

        self.btn_next = tk.Button(
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
        self.btn_next.pack(side="left", padx=3)

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
        vol_frame = tk.Frame(self.right_p_panel, bg="#1e1e2e")
        vol_frame.pack(fill="x", padx=15, pady=(2, 4))

        self.lbl_vol_icon = tk.Label(vol_frame, text="Volume:", font=("Segoe UI", 8, "bold"), bg="#1e1e2e", fg="#bd93f9")
        self.lbl_vol_icon.pack(side="left", padx=(0, 6))

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

        # 6. Kotak Daftar Bab / Tracklist (Scrollable)
        self.chap_frame = tk.LabelFrame(
            self.right_p_panel,
            text=" 📑 Daftar Bab / Tracklist ",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#bd93f9",
            bd=1,
            relief="solid",
        )
        self.chap_frame.pack(fill="both", expand=True, padx=12, pady=(6, 8))

        chap_tree_frame = tk.Frame(self.chap_frame, bg="#1e1e2e")
        chap_tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        chap_cols = ("time", "title")
        self.chap_tree = ttk.Treeview(
            chap_tree_frame,
            columns=chap_cols,
            show="headings",
            selectmode="browse",
        )
        self.chap_tree.heading("time", text="Waktu", anchor="center")
        self.chap_tree.heading("title", text="Judul Bab / Scene", anchor="w")

        self.chap_tree.column("time", width=62, minwidth=55, stretch=False, anchor="center")
        self.chap_tree.column("title", width=255, minwidth=180, stretch=True, anchor="w")

        chap_scroll = ttk.Scrollbar(chap_tree_frame, orient="vertical", command=self.chap_tree.yview)
        self.chap_tree.configure(yscrollcommand=chap_scroll.set)

        self.chap_tree.pack(side="left", fill="both", expand=True)
        chap_scroll.pack(side="right", fill="y")

        self.chap_tree.tag_configure("normal", foreground="#cdd6f4")
        self.chap_tree.tag_configure("active", foreground="#50fa7b", background="#313244")

        self.chap_tree.bind("<Double-1>", self._on_chapter_double_click)
        self.chap_tree.bind("<Return>", self._on_chapter_double_click)

    def _get_precise_duration_ms(self, file_path):
        """
        Mendapatkan durasi presisi berkas audio (dalam milidetik) via FFmpeg
        untuk mencegah distorsi panjang durasi akibat bug VBR Windows MCI.
        """
        try:
            ffmpeg_bin = get_bin_executable("ffmpeg")
            cmd = [ffmpeg_bin, "-hide_banner", "-i", file_path]
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            txt = res.stderr.decode("utf-8", errors="ignore")
            m = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', txt)
            if m:
                h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                return int((h * 3600 + mi * 60 + s) * 1000)
        except Exception:
            pass
        return 0

    def _mci_send(self, command):
        if sys.platform != "win32":
            return 0, ""
        buf = ctypes.create_unicode_buffer(256)
        err = ctypes.windll.winmm.mciSendStringW(command, buf, 255, 0)
        return err, buf.value

    def _refresh_playlist_view(self):
        """
        Memuat ulang daftar audio yang tersedia di riwayat serta memindai
        seluruh isi folder penyimpanan (termasuk semua subfolder di dalamnya).
        """
        self._chapters_cache.clear()
        self.player_tree.delete(*self.player_tree.get_children())
        histories = load_history()
        self.playlist_items = []

        seen_paths = set()
        hist_by_rjid = {}

        for h in histories:
            r_id = h.get("rjid", "").strip().upper()
            if r_id and r_id != "-":
                hist_by_rjid[r_id] = h

        # 1. Masukkan berkas dari riwayat yang masih ada di disk
        for h in histories:
            fpath = h.get("output_path", "")
            if fpath and os.path.exists(fpath):
                norm_p = os.path.normcase(os.path.abspath(fpath))
                if norm_p not in seen_paths:
                    seen_paths.add(norm_p)
                    self.playlist_items.append(h)

        # 2. Pindai folder penyimpanan download secara rekursif (termasuk subfolder)
        download_dir = os.path.abspath(get_download_dir())
        AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"}

        if os.path.exists(download_dir):
            for root, dirs, files in os.walk(download_dir, followlinks=False):
                # Lewati direktori sistem / cache / temp
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".")
                    and not d.startswith("temp_")
                    and d.lower() != "$recycle.bin"
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
                        if any(k in f.lower() for k in ["cover", "folder", "thumb", "main", "img"])
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
                        match = re.search(r"(RJ\d+|VJ\d+|BJ\d+)", f, re.IGNORECASE)
                        if not match:
                            match = re.search(r"(RJ\d+|VJ\d+|BJ\d+)", os.path.basename(root), re.IGNORECASE)

                        rjid_detected = match.group(1).upper() if match else "-"
                        ref_meta = hist_by_rjid.get(rjid_detected) if rjid_detected != "-" else None

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

                        cv_display = ref_meta.get("cv", "-") if ref_meta else "-"
                        circle_display = ref_meta.get("circle", "-") if ref_meta else "-"
                        cover_to_use = local_cover or (ref_meta.get("cover_url", "") if ref_meta else "")
                        if not cover_to_use and rjid_detected != "-":
                            cover_to_use = f"https://pic.weeabo0.xyz/{rjid_detected}_img_main.jpg"

                        item = {
                            "rjid": rjid_detected,
                            "title": title_display,
                            "cv": cv_display,
                            "circle": circle_display,
                            "file_size": size_str,
                            "output_path": full_path,
                            "cover_url": cover_to_use,
                        }
                        self.playlist_items.append(item)

        # Masukkan ke Treeview Playlist
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
            self.lbl_p_title.config(text=f"Daftar Putar / Koleksi Audio ({len(self.playlist_items)} Track)")

    def _on_playlist_select(self, event):
        selected = self.player_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.playlist_items):
            item = self.playlist_items[idx]
            self._render_player_cover(item.get("rjid", ""), item.get("cover_url", ""))
            self._load_track_chapters(item.get("output_path", ""))

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
        is_m4a = short_path.lower().endswith((".m4a", ".aac", ".mp4"))

        # Ambil durasi presisi via FFmpeg agar konsisten
        precise_dur = self._get_precise_duration_ms(short_path)
        self.player_duration_ms = precise_dur

        if is_m4a:
            # Gunakan engine Windows Media Foundation (MFPlay) untuk berkas M4A/AAC
            if not self.mf_player.load(short_path):
                show_dark_error(self, "Gagal Memutar", f"Format audio tidak dapat diputar: {os.path.basename(file_path)}")
                return
            self.use_mf_player = True
            self.mf_player.play()
        else:
            # Berkas MP3: Coba MCI terlebih dahulu
            self._mci_send("close asmr_player")
            err, _ = self._mci_send(f'open "{short_path}" type mpegvideo alias asmr_player')
            if err != 0:
                err, _ = self._mci_send(f'open "{short_path}" alias asmr_player')

            if err == 0:
                self.use_mf_player = False
                self._mci_send("set asmr_player time format milliseconds")
                _, len_str = self._mci_send("status asmr_player length")
                try:
                    mci_len = int(len_str)
                except ValueError:
                    mci_len = 0
                self.mci_raw_duration_ms = mci_len if mci_len > 0 else precise_dur
                if self.player_duration_ms <= 0:
                    self.player_duration_ms = self.mci_raw_duration_ms
                self._mci_send("play asmr_player")
            else:
                # Fallback ke Media Foundation jika MCI gagal
                if self.mf_player.load(short_path):
                    self.use_mf_player = True
                    self.mf_player.play()
                else:
                    show_dark_error(self, "Gagal Memutar", "Format audio tidak dapat diputar oleh sistem.")
                    return

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
        self._load_track_chapters(file_path)
        self._player_schedule_tick()

    def _render_player_cover(self, rjid, cover_url):
        # 1. Cek jika cover_url adalah file gambar lokal di disk
        if cover_url and os.path.exists(cover_url):
            try:
                pil_img = Image.open(cover_url)
                pil_img.thumbnail((290, 165))
                self.player_preview_image = ImageTk.PhotoImage(pil_img)
                self.player_canvas.delete("all")
                self.player_canvas.create_image(145, 82, image=self.player_preview_image)
                return
            except Exception:
                pass

        # 2. Cek cache thumbnail lokal .cache/covers/{rjid}.jpg
        cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg")
        if os.path.exists(cache_file):
            try:
                pil_img = Image.open(cache_file)
                pil_img.thumbnail((290, 165))
                self.player_preview_image = ImageTk.PhotoImage(pil_img)
                self.player_canvas.delete("all")
                self.player_canvas.create_image(145, 82, image=self.player_preview_image)
                return
            except Exception:
                pass

        # 3. Muat gambar dari jaringan jika berupa HTTP/HTTPS URL
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
                    pil_img.thumbnail((290, 165))
                    os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                    if rjid and rjid != "-":
                        pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                    self.player_preview_image = ImageTk.PhotoImage(pil_img)
                    self.player_canvas.delete("all")
                    self.player_canvas.create_image(145, 82, image=self.player_preview_image)
                except Exception:
                    pass
            threading.Thread(target=load_cover, daemon=True).start()

    def _get_current_pos_ms(self):
        """Mendapatkan posisi playback terkini dalam milidetik (MFPlayer atau MCI)."""
        if not self.current_playing_file:
            return 0
        if self.use_mf_player:
            return int(self.mf_player.get_position_sec() * 1000)
        else:
            _, pos_str = self._mci_send("status asmr_player position")
            try:
                mci_pos = int(pos_str)
            except ValueError:
                mci_pos = 0
            ref_len = self.mci_raw_duration_ms if self.mci_raw_duration_ms > 0 else self.player_duration_ms
            ratio = (mci_pos / float(ref_len)) if ref_len > 0 else 0.0
            return int(ratio * self.player_duration_ms)

    def _load_track_chapters(self, file_path):
        """Memuat daftar bab (CUE sheet atau embedded M4A/MP3) ke dalam Treeview."""
        self.chap_tree.delete(*self.chap_tree.get_children())
        self.current_chapters = []
        self.active_chapter_index = -1

        if not file_path or not os.path.exists(file_path):
            self.chap_frame.config(text=" 📑 Daftar Bab / Tracklist (0 Bab) ")
            self.chap_tree.insert("", "end", iid="none", values=("-", "(Tidak ada audio yang dipilih)"), tags=("normal",))
            return

        norm_path = os.path.normcase(os.path.abspath(file_path))
        try:
            mtime = os.path.getmtime(norm_path)
        except OSError:
            mtime = 0

        cached = self._chapters_cache.get(norm_path)
        if cached and cached[0] == mtime and cached[1]:
            chapters = cached[1]
        else:
            try:
                chapters = extract_chapters_from_audio(norm_path)
            except Exception:
                chapters = []
            if chapters:
                self._chapters_cache[norm_path] = (mtime, chapters)

        self.current_chapters = chapters
        if chapters:
            self.chap_frame.config(text=f" 📑 Daftar Bab / Tracklist ({len(chapters)} Bab) ")
            for idx, c in enumerate(chapters):
                time_str = self._format_time(c.get("start_ms", 0))
                title_str = c.get("title", f"Bab {idx + 1}")
                self.chap_tree.insert("", "end", iid=str(idx), values=(time_str, title_str), tags=("normal",))
            # Sinkronkan posisi bab aktif jika audio yang dimainkan sama dengan track yang dimuat
            if self.current_playing_file and os.path.normcase(os.path.abspath(self.current_playing_file)) == norm_path:
                self._sync_active_chapter(self._get_current_pos_ms())
        else:
            self.chap_frame.config(text=" 📑 Daftar Bab / Tracklist (0 Bab) ")
            self.chap_tree.insert("", "end", iid="none", values=("-", "(Tidak ada penanda bab / file cue)"), tags=("normal",))

            # Coba sinkronisasi bab otomatis dari japaneseasmr jika berkas memiliki Kode RJ
            m_rj = re.search(r"(RJ\d+)", os.path.basename(norm_path), re.IGNORECASE)
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
        """Seek pemutar langsung ke waktu bab yang diklik dua kali oleh pengguna."""
        sel = self.chap_tree.selection()
        if not sel or sel[0] == "none":
            return
        try:
            c_idx = int(sel[0])
        except ValueError:
            return

        if 0 <= c_idx < len(self.current_chapters):
            chapter = self.current_chapters[c_idx]
            target_ms = chapter.get("start_ms", 0)

            # Jika belum ada file yang diputar tapi playlist dipilih, load & play
            if not self.current_playing_file:
                p_sel = self.player_tree.selection()
                if p_sel:
                    p_idx = int(p_sel[0])
                    if 0 <= p_idx < len(self.playlist_items):
                        item = self.playlist_items[p_idx]
                        self._player_load_and_play(item.get("output_path", ""), meta=item)
                elif self.playlist_items:
                    self._player_load_and_play(self.playlist_items[0].get("output_path", ""), meta=self.playlist_items[0])

            self._player_seek_to_ms(target_ms)
            if not self.is_playing:
                self._player_play_pause_toggle()
            self._highlight_active_chapter(c_idx)

    def _highlight_active_chapter(self, active_idx):
        """Menyorot baris bab yang sedang aktif dan menggulir ke posisinya secara otomatis."""
        if self.active_chapter_index == active_idx:
            return
        self.active_chapter_index = active_idx
        for idx in range(len(self.current_chapters)):
            iid = str(idx)
            if self.chap_tree.exists(iid):
                if idx == active_idx:
                    self.chap_tree.item(iid, tags=("active",))
                    self.chap_tree.see(iid)
                else:
                    self.chap_tree.item(iid, tags=("normal",))

    def _sync_active_chapter(self, cur_ms):
        """Mencari bab yang sesuai dengan posisi waktu playback sekarang dan menyorotnya."""
        if not self.current_chapters:
            return
        active_idx = -1
        for i, ch in enumerate(self.current_chapters):
            if ch.get("start_ms", 0) <= cur_ms:
                active_idx = i
            else:
                break
        if active_idx != -1 and active_idx != self.active_chapter_index:
            self._highlight_active_chapter(active_idx)

    def _player_play_pause_toggle(self):
        if not self.current_playing_file:
            if self.playlist_items:
                self.current_track_index = 0
                item = self.playlist_items[0]
                self._player_load_and_play(item.get("output_path", ""), meta=item)
            return

        if self.is_playing:
            if self.use_mf_player:
                self.mf_player.pause()
            else:
                self._mci_send("pause asmr_player")
            self.is_playing = False
            self.is_paused = True
            self.btn_play_pause.config(text="▶ Putar")
        else:
            if self.use_mf_player:
                self.mf_player.play()
            else:
                self._mci_send("play asmr_player")
            self.is_playing = True
            self.is_paused = False
            self.btn_play_pause.config(text="❚❚ Jeda")
            self._player_schedule_tick()

    def _player_stop(self):
        if self.use_mf_player:
            self.mf_player.stop()
        else:
            self._mci_send("stop asmr_player")
            self._mci_send("seek asmr_player to start")
        self.is_playing = False
        self.is_paused = False
        self.btn_play_pause.config(text="▶ Putar")
        self.timeline_slider.set(0)
        self.lbl_time_cur.config(text="00:00")
        self._highlight_active_chapter(-1)

    def _on_slider_change(self, val):
        if self.is_user_dragging_slider and self.player_duration_ms > 0:
            cur_ms = int(float(val) * self.player_duration_ms / 100.0)
            self.lbl_time_cur.config(text=self._format_time(cur_ms))

    def _on_slider_release(self, event):
        self.is_user_dragging_slider = False
        if not self.current_playing_file or self.player_duration_ms <= 0:
            return
        target_pct = self.timeline_slider.get()
        target_ms = int((float(target_pct) / 100.0) * self.player_duration_ms)
        self._player_seek_to_ms(target_ms)

    def _player_seek_to_ms(self, target_ms):
        """Melakukan seek audio ke posisi milidetik tertentu pada MFPlayer atau MCI."""
        if not self.current_playing_file:
            return
        if self.player_duration_ms > 0:
            target_ms = max(0, min(self.player_duration_ms, target_ms))
        else:
            target_ms = max(0, target_ms)

        if self.use_mf_player:
            target_sec = target_ms / 1000.0
            self.mf_player.seek(target_sec)
            if self.is_playing:
                self.mf_player.play()
        else:
            ref_len = self.mci_raw_duration_ms if self.mci_raw_duration_ms > 0 else self.player_duration_ms
            scale_ms = int(target_ms * (ref_len / float(self.player_duration_ms))) if self.player_duration_ms > 0 else target_ms
            self._mci_send(f"seek asmr_player to {scale_ms}")
            if self.is_playing:
                self._mci_send("play asmr_player")

        if self.player_duration_ms > 0:
            pct = (target_ms / float(self.player_duration_ms)) * 100.0
            self.timeline_slider.set(pct)
        self.lbl_time_cur.config(text=self._format_time(target_ms))
        self._sync_active_chapter(target_ms)

    def _player_set_volume(self, val):
        vol_pct = int(float(val))
        if hasattr(self, "lbl_vol_val"):
            self.lbl_vol_val.config(text=f"{vol_pct}%")
        if self.use_mf_player:
            self.mf_player.set_volume(vol_pct)
        else:
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

        if self.use_mf_player:
            pos_sec = self.mf_player.get_position_sec()
            pos_ms = int(pos_sec * 1000)
            dur_ms = self.player_duration_ms
            if dur_ms > 0:
                ratio = max(0.0, min(1.0, pos_ms / float(dur_ms)))
            else:
                ratio = 0.0

            if not self.is_user_dragging_slider and dur_ms > 0:
                pct = ratio * 100.0
                self.timeline_slider.set(pct)
                self.lbl_time_cur.config(text=self._format_time(pos_ms))
                self._sync_active_chapter(pos_ms)

            # Cek jika track selesai
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
        if ref_len > 0:
            ratio = max(0.0, min(1.0, mci_pos_ms / float(ref_len)))
        else:
            ratio = 0.0

        real_pos_ms = int(ratio * self.player_duration_ms)

        if not self.is_user_dragging_slider and self.player_duration_ms > 0:
            pct = ratio * 100.0
            self.timeline_slider.set(pct)
            self.lbl_time_cur.config(text=self._format_time(real_pos_ms))
            self._sync_active_chapter(real_pos_ms)

        # Cek jika track selesai
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
        total_sec = max(0, int(ms / 1000))
        mins = total_sec // 60
        secs = total_sec % 60
        hours = mins // 60
        if hours > 0:
            mins = mins % 60
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

