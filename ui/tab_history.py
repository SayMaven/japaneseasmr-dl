import io
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk
import urllib.request

from PIL import Image, ImageTk

from config_manager import load_history, save_history
from i18n import t
from ui.constants import REFERER, USER_AGENT
from ui.dialogs import (
    ask_dark_yesno,
    show_dark_error,
    show_dark_info,
    show_dark_warning,
)


class HistoryTabMixin:
    """Mixin untuk membangun antarmuka dan menangani aksi pada Tab Riwayat (History)."""
    def _build_history_tab(self):
        container = self.tab_history

        # Layout 2 Kolom: Kiri (Tabel Riwayat), Kanan (Detail & Cover)
        left_h_panel = tk.Frame(container, bg="#1e1e2e")
        left_h_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # Header Riwayat & Tombol Refresh
        h_header = tk.Frame(left_h_panel, bg="#1e1e2e")
        h_header.pack(fill="x", pady=(0, 6))

        self.lbl_h_header = tk.Label(
            h_header,
            text="Riwayat Karya Terunduh",
            font=("Segoe UI", 11, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
        )
        self.lbl_h_header.pack(side="left")

        self.refresh_hist_btn = tk.Button(
            h_header,
            text="Segarkan",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            bd=0,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._load_history_view,
        )
        self.refresh_hist_btn.pack(side="right")

        # Banner Statistik Penyimpanan
        stats_frame = tk.Frame(left_h_panel, bg="#282a36", bd=1, relief="solid")
        stats_frame.pack(fill="x", pady=(0, 8))

        self.lbl_hist_stats = tk.Label(
            stats_frame,
            text="Memuat statistik koleksi...",
            font=("Segoe UI", 9, "bold"),
            bg="#282a36",
            fg="#8be9fd",
            padx=10,
            pady=5,
            anchor="w",
        )
        self.lbl_hist_stats.pack(fill="x")

        # Tabel Riwayat Treeview
        cols = ("date", "rjid", "title", "size")
        self.hist_tree = ttk.Treeview(left_h_panel, columns=cols, show="headings", selectmode="browse")
        self.hist_tree.heading("date", text="Tanggal Unduh", anchor="center")
        self.hist_tree.heading("rjid", text="Kode RJ", anchor="center")
        self.hist_tree.heading("title", text="Judul Karya", anchor="w")
        self.hist_tree.heading("size", text="Ukuran", anchor="center")

        self.hist_tree.column("date", width=140, anchor="center")
        self.hist_tree.column("rjid", width=110, anchor="center")
        self.hist_tree.column("title", width=280, anchor="w")
        self.hist_tree.column("size", width=80, anchor="center")

        h_scroll = ttk.Scrollbar(left_h_panel, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=h_scroll.set)

        self.hist_tree.pack(side="left", fill="both", expand=True)
        h_scroll.pack(side="right", fill="y")
        self.hist_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        # Panel Kanan Riwayat (Detail & Cover)
        self.right_h_panel = tk.LabelFrame(
            container,
            text=" Detail Riwayat Koleksi ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=330,
        )
        self.right_h_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        self.right_h_panel.pack_propagate(False)

        # Tombol Buka File di Riwayat
        h_actions = tk.Frame(self.right_h_panel, bg="#1e1e2e")
        h_actions.pack(fill="x", padx=12, pady=10, side="bottom")

        self.btn_play_file = tk.Button(
            h_actions,
            text="Putar di Player Bawaan",
            font=("Segoe UI", 9, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            bd=0,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self._play_history_in_player,
        )
        self.btn_play_file.pack(fill="x", pady=(0, 6))

        self.btn_del_history = tk.Button(
            h_actions,
            text="Hapus Riwayat",
            font=("Segoe UI", 8),
            bg="#44475a",
            fg="#ff5555",
            activebackground="#6272a4",
            activeforeground="#ff5555",
            bd=0,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=lambda: self._delete_history_item(),
        )
        self.btn_del_history.pack(fill="x")

        # Canvas Cover
        self.hist_canvas = tk.Canvas(
            self.right_h_panel,
            bg="#282a36",
            width=290,
            height=195,
            bd=0,
            highlightthickness=1,
            highlightbackground="#44475a",
        )
        self.hist_canvas.pack(pady=8, padx=10)
        self.hist_canvas.create_text(145, 97, text="Pilih item riwayat", fill="#6272a4", font=("Segoe UI", 10))

        h_info_inner = tk.Frame(self.right_h_panel, bg="#1e1e2e")
        h_info_inner.pack(fill="both", expand=True, padx=12, pady=3)

        self.lbl_h_id = self._create_info_row(h_info_inner, "Kode RJ", "-", "lbl_detail_rjid")
        self.lbl_h_title = self._create_info_row(h_info_inner, "Judul", "-", "lbl_detail_title")
        self.lbl_h_cv = self._create_info_row(h_info_inner, "CV / Seiyuu", "-", "lbl_detail_cv")
        self.lbl_h_circle = self._create_info_row(h_info_inner, "Circle / Maker", "-", "lbl_detail_circle")
        self.lbl_h_rating = self._create_info_row(h_info_inner, "Rating Usia", "-", "lbl_detail_age")
        self.lbl_h_genre = self._create_info_row(h_info_inner, "Genre / Tag", "-", "lbl_detail_genre")
        self.lbl_h_path = self._create_info_row(h_info_inner, "Status File", "-", "col_status")

    def _load_history_view(self):
        """Memuat ulang tabel riwayat dari history.json dan menghitung statistik koleksi."""
        self.hist_tree.delete(*self.hist_tree.get_children())
        histories = load_history()
        total_size_bytes = 0
        available_count = 0

        for idx, h in enumerate(histories):
            fpath = h.get("output_path", "")
            if os.path.exists(fpath):
                try:
                    fsize = os.path.getsize(fpath)
                    total_size_bytes += fsize
                    available_count += 1
                except OSError:
                    pass

            self.hist_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    h.get("download_date", "-"),
                    h.get("rjid", "-"),
                    h.get("title", "-"),
                    h.get("file_size", "-"),
                ),
            )

        # Update Banner Statistik
        if total_size_bytes >= 1024 * 1024 * 1024:
            size_str = f"{total_size_bytes / (1024 * 1024 * 1024):.2f} GB"
        else:
            size_str = f"{total_size_bytes / (1024 * 1024):.1f} MB"

        stats_text = (
            f"📊 Total Koleksi: {len(histories)} Karya   |   "
            f"💾 Total Penyimpanan: {size_str}   |   "
            f"✅ File Tersedia di Disk: {available_count}/{len(histories)}"
        )
        if hasattr(self, "lbl_hist_stats"):
            self.lbl_hist_stats.config(text=stats_text)

    def _on_history_select(self, event):
        selected = self.hist_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        histories = load_history()
        if idx < len(histories):
            h = histories[idx]
            self.lbl_h_id.config(text=h.get("rjid", "-"))
            self.lbl_h_title.config(text=h.get("title", "-"))
            self.lbl_h_cv.config(text=h.get("cv", "-"))
            self.lbl_h_circle.config(text=h.get("circle", "-"))
            
            rating = h.get("age_rating", "-")
            self.lbl_h_rating.config(text=rating, fg="#ff79c6" if "18" in rating else "#50fa7b")
            self.lbl_h_genre.config(text=h.get("genre", "-"))

            file_path = h.get("output_path", "")
            self.btn_del_history.config(state="normal")
            if os.path.exists(file_path):
                self.lbl_h_path.config(text="✅ File Tersedia", fg="#50fa7b")
                self.btn_play_file.config(state="normal")
            else:
                self.lbl_h_path.config(text="❌ File Sudah Dihapus / Tidak Ditemukan", fg="#ff5555")
                self.btn_play_file.config(state="disabled")

            # Load Cover Thumbnail (Cache lokal / fallback online)
            rjid = h.get("rjid", "")
            cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg")
            if os.path.exists(cache_file):
                try:
                    pil_img = Image.open(cache_file)
                    pil_img.thumbnail((280, 195))
                    self.hist_preview_image = ImageTk.PhotoImage(pil_img)
                    self.hist_canvas.delete("all")
                    self.hist_canvas.create_image(145, 97, image=self.hist_preview_image)
                    return
                except Exception:
                    pass

            # Fallback download cover jika cache belum ada
            def load_online_cover():
                cover_url = h.get("cover_url", f"https://pic.weeabo0.xyz/{rjid}_img_main.jpg")
                try:
                    req = urllib.request.Request(cover_url, headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((280, 195))
                    os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                    pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                    self.hist_preview_image = ImageTk.PhotoImage(pil_img)
                    self.hist_canvas.delete("all")
                    self.hist_canvas.create_image(145, 97, image=self.hist_preview_image)
                except Exception:
                    pass

            threading.Thread(target=load_online_cover, daemon=True).start()

    def _play_history_in_player(self):
        """Memutar file riwayat terpilih langsung di Tab Pemutar Audio."""
        selected = self.hist_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        histories = load_history()
        if idx < len(histories):
            h = histories[idx]
            file_path = h.get("output_path", "")
            if not os.path.exists(file_path):
                self._open_selected_history_file()
                return

            # Alihkan notebook ke Tab Player
            self.notebook.select(self.tab_player)
            self._refresh_playlist_view()
            self._player_load_and_play(file_path, meta=h)

    def _open_selected_history_file(self):
        selected = self.hist_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        histories = load_history()
        if idx < len(histories):
            h = histories[idx]
            file_path = h.get("output_path", "")
            if os.path.exists(file_path):
                os.startfile(file_path)
            else:
                self.lbl_h_path.config(text="❌ File Sudah Dihapus / Tidak Ditemukan", fg="#ff5555")
                self.btn_play_file.config(state="disabled")
                ans = ask_dark_yesno(
                    self,
                    "File Tidak Ditemukan",
                    f"File audio untuk '{h.get('rjid', '-')}' sudah tidak ditemukan di lokasi penyimpanan (mungkin telah dipindahkan atau dihapus).\n\nLokasi:\n{file_path}\n\nApakah Anda ingin menghapus riwayat ini dari daftar riwayat?",
                    confirm_text="Hapus Catatan",
                    cancel_text="Batal",
                )
                if ans:
                    self._delete_history_item(idx)

    def _delete_history_item(self, idx=None):
        if idx is None:
            selected = self.hist_tree.selection()
            if not selected:
                show_dark_info(self, "Informasi", "Pilih item riwayat yang ingin dihapus terlebih dahulu.")
                return
            idx = int(selected[0])

        histories = load_history()
        if 0 <= idx < len(histories):
            deleted = histories.pop(idx)
            from config_manager import save_history
            save_history(histories)
            self._load_history_view()
            # Reset detail view
            self.hist_canvas.delete("all")
            self.hist_canvas.create_text(145, 97, text="Pilih item riwayat", fill="#6272a4", font=("Segoe UI", 10))
            self.lbl_h_id.config(text="-")
            self.lbl_h_title.config(text="-")
            self.lbl_h_cv.config(text="-")
            self.lbl_h_circle.config(text="-")
            self.lbl_h_rating.config(text="-", fg="#f8f8f2")
            self.lbl_h_genre.config(text="-")
            self.lbl_h_path.config(text="-")
            self.btn_play_file.config(state="disabled")
            self.btn_del_history.config(state="disabled")
            self._log(f"[i] Menghapus riwayat untuk: {deleted.get('rjid', '-')}")
