import io
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import urllib.request

from PIL import Image, ImageTk

from config_manager import (
    get_download_dir,
    resolve_input_to_rjid,
    save_config,
    set_download_dir,
)
from dlsite_scraper import fetch_dlsite_metadata, resolve_best_cover_url
from i18n import t
from ui.constants import REFERER, USER_AGENT
from ui.dialogs import (
    ask_dark_yesno,
    show_dark_error,
    show_dark_info,
    show_dark_warning,
)


class QueueTabMixin:
    """Mixin untuk membangun antarmuka dan menangani aksi pada Tab Antrean (Queue)."""
    def _build_queue_tab(self):
        container = self.tab_queue

        # Layout 2 Kolom: Kiri (Input & Tabel), Kanan (Cover & Info Detail)
        main_container = tk.Frame(container, bg="#1e1e2e")
        main_container.pack(fill="both", expand=True)

        left_panel = tk.Frame(main_container, bg="#1e1e2e")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # 1. Baris Input & Tombol Tambah
        self.input_frame = tk.LabelFrame(
            left_panel,
            text=" Input Kode RJ / URL ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        self.input_frame.pack(fill="x", pady=(0, 10), ipady=5)

        input_inner = tk.Frame(self.input_frame, bg="#1e1e2e")
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

        self.paste_btn = tk.Button(
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
        self.paste_btn.pack(side="left", padx=(0, 8))

        self.add_btn = tk.Button(
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
        self.add_btn.pack(side="right")

        # Opsi Checkbox Nama File (Diletakkan rapi di bawah baris input)
        opts_frame = tk.Frame(self.input_frame, bg="#1e1e2e")
        opts_frame.pack(fill="x", padx=10, pady=(2, 4))

        self.chk_name = tk.Checkbutton(
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
        self.chk_name.pack(side="left")

        # 2. Tabel Antrean
        self.queue_frame = tk.LabelFrame(
            left_panel,
            text=" Daftar Antrean Download ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        self.queue_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("no", "rjid", "title", "status")
        self.tree = ttk.Treeview(self.queue_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("no", text="#", anchor="center")
        self.tree.heading("rjid", text="Kode RJ", anchor="center")
        self.tree.heading("title", text="Judul / Keterangan", anchor="w")
        self.tree.heading("status", text="Status", anchor="center")

        self.tree.column("no", width=35, anchor="center")
        self.tree.column("rjid", width=110, anchor="center")
        self.tree.column("title", width=260, anchor="w")
        self.tree.column("status", width=110, anchor="center")

        tree_scroll = ttk.Scrollbar(self.queue_frame, orient="vertical", command=self.tree.yview)
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

        self.clear_btn = tk.Button(
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
        self.clear_btn.pack(side="right")

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
        self.log_frame = tk.LabelFrame(
            left_panel,
            text=" Status & Log Konsol ",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        self.log_frame.pack(fill="x", pady=(0, 5))

        self.log_text = tk.Text(
            self.log_frame,
            height=5,
            bg="#181825",
            fg="#a6adc8",
            font=("Consolas", 9),
            bd=0,
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Panel Kanan: Preview Thumbnail & Info Card
        self.right_panel = tk.LabelFrame(
            main_container,
            text=" Informasi Karya & Preview ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=330,
        )
        self.right_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        self.right_panel.pack_propagate(False)

        # Canvas Cover
        self.cover_canvas = tk.Canvas(
            self.right_panel,
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
        info_inner = tk.Frame(self.right_panel, bg="#1e1e2e")
        info_inner.pack(fill="both", expand=True, padx=12, pady=3)

        self.lbl_q_id = self._create_info_row(info_inner, "Kode RJ", "-", "lbl_detail_rjid")
        self.lbl_q_title = self._create_info_row(info_inner, "Judul", "-", "lbl_detail_title")
        self.lbl_q_cv = self._create_info_row(info_inner, "CV / Seiyuu", "-", "lbl_detail_cv")
        self.lbl_q_circle = self._create_info_row(info_inner, "Circle / Maker", "-", "lbl_detail_circle")
        self.lbl_q_rating = self._create_info_row(info_inner, "Rating Usia", "-", "lbl_detail_age")
        self.lbl_q_genre = self._create_info_row(info_inner, "Genre / Tag", "-", "lbl_detail_genre")

    def _create_info_row(self, parent, label_text, default_value, key=None):
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
        if not hasattr(self, "_info_rows"):
            self._info_rows = []
        if key:
            self._info_rows.append((lbl, key))
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
            self._refresh_playlist_view()

    def _log(self, message):
        def append():
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
        self.after(0, append)

    def _open_downloads_folder(self):
        d_dir = get_download_dir()
        os.makedirs(d_dir, exist_ok=True)
        os.startfile(os.path.abspath(d_dir))

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
            rjid = resolve_input_to_rjid(token)
            if rjid:
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
            if meta.get("cover_url"):
                self.queue_items[index]["cover_url"] = meta["cover_url"]
            if meta.get("dlsite_cover_url"):
                self.queue_items[index]["dlsite_cover_url"] = meta["dlsite_cover_url"]

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
            cover_to_fetch = meta.get("cover_url") or resolve_best_cover_url(rj_id, meta.get("dlsite_cover_url"))
            if cover_to_fetch:
                try:
                    cover_ref = "https://www.dlsite.com" if "dlsite" in cover_to_fetch else ("https://asmr.one/" if "asmr.one" in cover_to_fetch else REFERER)
                    req = urllib.request.Request(
                        cover_to_fetch,
                        headers={
                            "Referer": cover_ref,
                            "User-Agent": USER_AGENT,
                            "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((280, 195))
                    self.queue_items[index]["cover_image"] = pil_img
                    os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                    pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)

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
        self.lbl_q_id.config(text=item.get("rjid", "-"))
        self.lbl_q_title.config(text=item.get("title", "-"))
        self.lbl_q_cv.config(text=item.get("cv", "-"))
        self.lbl_q_circle.config(text=item.get("circle", "-"))
        
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

    def _paste_from_clipboard(self):
        try:
            clip_text = self.clipboard_get().strip()
            if clip_text:
                auto_clip = self.var_auto_clipboard.get() if hasattr(self, "var_auto_clipboard") else self.config.get("auto_clipboard", True)
                if auto_clip:
                    tokens = re.split(r"[\s,;]+", clip_text)
                    resolved_tokens = []
                    for t in tokens:
                        if not t:
                            continue
                        r = resolve_input_to_rjid(t)
                        resolved_tokens.append(r if r else t)
                    if resolved_tokens:
                        clip_text = ", ".join(resolved_tokens)
                self.id_entry.delete(0, "end")
                self.id_entry.insert(0, clip_text)
                self.id_entry.config(fg="#50fa7b")
                self._log(f"[i] Berhasil menempel dari clipboard: {clip_text[:40]}...")
        except Exception as e:
            self._log(f"[!] Gagal membaca clipboard: {e}")
