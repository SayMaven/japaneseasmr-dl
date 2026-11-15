import io
import os
import threading
import tkinter as tk
from tkinter import ttk
import urllib.request
import customtkinter as ctk

from PIL import Image, ImageTk

from config_manager import load_history, save_history
from i18n import t
from ui.constants import REFERER, USER_AGENT
from ui.dialogs import (
    ask_dark_yesno,
    show_dark_info,
)
from ui.icons import get_icon
from ui.theme import (
    BORDER_ACTIVE,
    BORDER_SUBTLE,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CAPTION,
    FONT_SECTION,
    RADIUS_BUTTON,
    RADIUS_CARD,
    RADIUS_INPUT,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
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


class HistoryTabMixin:
    """Mixin providing interface construction and interaction handlers for the History Tab."""
    def _build_history_tab(self):
        container = self.tab_history

        # 2-Column layout: Left (History Table & Search), Right (Details & Cover Art)
        main_container = ctk.CTkFrame(container, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        left_h_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        left_h_panel.pack(side="left", fill="both", expand=True, padx=(0, SPACE_MD))

        # 1. History header and search controls
        header_card = ctk.CTkFrame(
            left_h_panel,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        header_card.pack(fill="x", pady=(0, SPACE_MD))

        h_header = ctk.CTkFrame(header_card, fg_color="transparent")
        h_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM))

        self.lbl_h_header = ctk.CTkLabel(
            h_header,
            text=t("tab_history"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_h_header.pack(side="left")

        self.refresh_hist_btn = ctk.CTkButton(
            h_header,
            text=f" {t('btn_refresh_playlist')}",
            image=get_icon("refresh", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=32,
            width=110,
            command=self._load_history_view,
        )
        self.refresh_hist_btn.pack(side="right")

        # Search Bar
        search_row = ctk.CTkFrame(header_card, fg_color="transparent")
        search_row.pack(fill="x", padx=SPACE_LG, pady=(0, SPACE_MD))

        self.hist_search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Cari berdasarkan kode RJ, judul, atau CV...",
            font=FONT_BODY,
            corner_radius=RADIUS_INPUT,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
            text_color=TEXT_PRIMARY,
            height=36,
        )
        self.hist_search_entry.pack(side="left", fill="x", expand=True, padx=(0, SPACE_SM))
        self.hist_search_entry.bind("<KeyRelease>", lambda e: self._on_hist_search_changed())

        self.btn_clear_search = ctk.CTkButton(
            search_row,
            text=" Reset",
            image=get_icon("rotate-ccw", size=(14, 14)),
            font=FONT_CAPTION,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_SECONDARY,
            corner_radius=RADIUS_BUTTON,
            height=36,
            width=80,
            command=self._reset_hist_search,
        )
        self.btn_clear_search.pack(side="right")

        # 2. History table card
        table_card = ctk.CTkFrame(
            left_h_panel,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        table_card.pack(fill="both", expand=True, pady=(0, SPACE_MD))

        # Storage statistics banner
        stats_frame = ctk.CTkFrame(table_card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM // 2))

        self.lbl_hist_stats = ctk.CTkLabel(
            stats_frame,
            text="Memuat statistik koleksi...",
            font=FONT_CAPTION,
            text_color=STATUS_INFO,
            anchor="w",
        )
        self.lbl_hist_stats.pack(fill="x")

        # History Treeview table
        tree_container = ctk.CTkFrame(
            table_card,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        tree_container.pack(fill="both", expand=True, padx=SPACE_LG, pady=(0, SPACE_MD))

        cols = ("date", "rjid", "title", "size")
        self.hist_tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse", style="Treeview")
        self.hist_tree.heading("date", text=t("col_hist_date"), anchor="center")
        self.hist_tree.heading("rjid", text=t("col_hist_rjid"), anchor="center")
        self.hist_tree.heading("title", text=t("col_hist_title"), anchor="w")
        self.hist_tree.heading("size", text=t("col_play_duration"), anchor="center")

        self.hist_tree.column("date", width=140, anchor="center")
        self.hist_tree.column("rjid", width=120, anchor="center")
        self.hist_tree.column("title", width=360, anchor="w")
        self.hist_tree.column("size", width=90, anchor="center")

        h_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.hist_tree.yview, style="Vertical.TScrollbar")
        self.hist_tree.configure(yscrollcommand=h_scroll.set)

        self.hist_tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        h_scroll.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.hist_tree.bind("<<TreeviewSelect>>", self._on_history_select)
        self.hist_tree.bind("<Double-1>", lambda e: self._play_history_in_player())

        # 3. Right detail panel (Details & Cover art)
        self.right_h_panel = ctk.CTkFrame(
            main_container,
            width=320,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.right_h_panel.pack(side="right", fill="both", pady=0)
        self.right_h_panel.pack_propagate(False)

        right_h_header = ctk.CTkFrame(self.right_h_panel, fg_color="transparent")
        right_h_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM))

        self.lbl_hist_detail_title = ctk.CTkLabel(
            right_h_header,
            text=t("lbl_preview_title"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_hist_detail_title.pack(side="left")

        # Cover canvas
        self.hist_canvas = tk.Canvas(
            self.right_h_panel,
            bg=SURFACE_INPUT,
            width=290,
            height=195,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_SUBTLE,
        )
        self.hist_canvas.pack(pady=4, padx=SPACE_LG)
        self.hist_canvas.create_text(
            145, 97, text="Pilih item riwayat", fill=TEXT_MUTED, font=FONT_BODY
        )

        # Action buttons at the bottom of the right panel
        h_actions = ctk.CTkFrame(self.right_h_panel, fg_color="transparent")
        h_actions.pack(fill="x", padx=SPACE_LG, pady=SPACE_MD, side="bottom")

        self.btn_play_file = ctk.CTkButton(
            h_actions,
            text=f" {t('btn_play_selected')}",
            image=get_icon("play", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=STATUS_SUCCESS,
            hover_color="#059669",
            text_color="#ffffff",
            corner_radius=RADIUS_BUTTON,
            height=36,
            state="disabled",
            command=self._play_history_in_player,
        )
        self.btn_play_file.pack(fill="x", pady=(0, 6))

        self.btn_open_folder_file = ctk.CTkButton(
            h_actions,
            text=" Buka Berkas Audio",
            image=get_icon("folder", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=32,
            state="disabled",
            command=self._open_selected_history_file,
        )
        self.btn_open_folder_file.pack(fill="x", pady=(0, 6))

        self.btn_del_history = ctk.CTkButton(
            h_actions,
            text=f" {t('btn_clear_history')}",
            image=get_icon("trash", size=(14, 14)),
            font=FONT_CAPTION,
            fg_color=SURFACE_INPUT,
            hover_color=STATUS_DANGER,
            text_color=STATUS_DANGER,
            corner_radius=RADIUS_BUTTON,
            height=30,
            state="disabled",
            command=lambda: self._delete_history_item(),
        )
        self.btn_del_history.pack(fill="x")

        # Info Labels (Scrollable)
        h_info_scroll = ctk.CTkScrollableFrame(self.right_h_panel, fg_color="transparent")
        h_info_scroll.pack(fill="both", expand=True, padx=SPACE_SM, pady=(4, 6))

        self.lbl_h_id = self._create_info_row(h_info_scroll, "Kode RJ", "-", "lbl_detail_rjid")
        self.lbl_h_title = self._create_info_row(h_info_scroll, "Judul", "-", "lbl_detail_title")
        self.lbl_h_cv = self._create_info_row(h_info_scroll, "CV / Seiyuu", "-", "lbl_detail_cv")
        self.lbl_h_circle = self._create_info_row(h_info_scroll, "Circle / Maker", "-", "lbl_detail_circle")
        self.lbl_h_rating = self._create_info_row(h_info_scroll, "Rating Usia", "-", "lbl_detail_age")
        self.lbl_h_genre = self._create_info_row(h_info_scroll, "Genre / Tag", "-", "lbl_detail_genre")
        self.lbl_h_path = self._create_info_row(h_info_scroll, "Lokasi Berkas", "-", "lbl_detail_path")

    def _on_hist_search_changed(self):
        query = self.hist_search_entry.get().strip().lower()
        self._load_history_view(query=query)

    def _reset_hist_search(self):
        self.hist_search_entry.delete(0, "end")
        self._load_history_view()

    def _load_history_view(self, query=None):
        self.hist_tree.delete(*self.hist_tree.get_children())
        histories = load_history()

        if not histories:
            self.lbl_hist_stats.configure(text="Belum ada karya yang diunduh dalam riwayat.")
            return

        total_bytes = 0
        displayed_count = 0

        for idx, h in enumerate(histories):
            file_path = h.get("output_path", "")
            size_str = "-"
            if file_path and os.path.exists(file_path):
                sz = os.path.getsize(file_path)
                total_bytes += sz
                size_str = f"{sz / (1024 * 1024):.1f} MB"

            date_str = h.get("date", "-")
            rjid = h.get("rjid", "-")
            title = h.get("title", "-")
            cv = h.get("cv", "-")

            # Filter Search Query
            if query:
                combined_text = f"{rjid} {title} {cv}".lower()
                if query not in combined_text:
                    continue

            self.hist_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(date_str, rjid, title, size_str),
            )
            displayed_count += 1

        total_gb = total_bytes / (1024 * 1024 * 1024)
        if query:
            self.lbl_hist_stats.configure(text=f"Ditemukan {displayed_count} dari total {len(histories)} karya. (Ukuran: {total_gb:.2f} GB)")
        else:
            self.lbl_hist_stats.configure(text=f"Total: {len(histories)} karya tersimpan ({total_gb:.2f} GB)")

    def _on_history_select(self, event):
        selected = self.hist_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        histories = load_history()
        if idx < len(histories):
            h = histories[idx]
            self.lbl_h_id.configure(text=h.get("rjid", "-"))
            self.lbl_h_title.configure(text=h.get("title", "-"))
            self.lbl_h_cv.configure(text=h.get("cv", "-"))
            self.lbl_h_circle.configure(text=h.get("circle", "-"))

            rating = h.get("age_rating", "-")
            self.lbl_h_rating.configure(
                text=rating,
                text_color=STATUS_DANGER if "18" in rating else STATUS_SUCCESS,
            )
            self.lbl_h_genre.configure(text=h.get("genre", "-"))

            file_path = h.get("output_path", "-")
            self.lbl_h_path.configure(text=file_path)

            self.btn_del_history.configure(state="normal")
            if hasattr(self, "btn_open_folder_file"):
                self.btn_open_folder_file.configure(state="normal" if os.path.exists(file_path) else "disabled")

            if os.path.exists(file_path):
                self.btn_play_file.configure(state="normal")
            else:
                self.lbl_h_path.configure(text="[!] File Sudah Dihapus / Tidak Ditemukan")
                self.btn_play_file.configure(state="disabled")

            # Load Cover Thumbnail
            rjid = h.get("rjid", "")
            cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg")
            if os.path.exists(cache_file):
                try:
                    pil_img = Image.open(cache_file)
                    pil_img.thumbnail((290, 195))
                    self.hist_preview_image = ImageTk.PhotoImage(pil_img)
                    self.hist_canvas.delete("all")
                    self.hist_canvas.create_image(145, 97, image=self.hist_preview_image)
                    return
                except Exception:
                    pass

            def _apply_online_cover(p_img):
                try:
                    if hasattr(self, "hist_canvas") and self.hist_canvas.winfo_exists():
                        self.hist_preview_image = ImageTk.PhotoImage(p_img)
                        self.hist_canvas.delete("all")
                        self.hist_canvas.create_image(145, 97, image=self.hist_preview_image)
                except Exception:
                    pass

            def load_online_cover():
                cover_url = h.get("cover_url", f"https://pic.weeabo0.xyz/{rjid}_img_main.jpg")
                try:
                    req = urllib.request.Request(cover_url, headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((290, 195))
                    os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                    pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                    self.after(0, lambda: _apply_online_cover(pil_img))
                except Exception:
                    pass

            threading.Thread(target=load_online_cover, daemon=True).start()

    def _play_history_in_player(self):
        """Play the selected history item directly within the Audio Player Tab."""
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

            if hasattr(self, "_select_page"):
                self._select_page("player")
            elif hasattr(self, "notebook"):
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
                self.lbl_h_path.configure(text="[!] File Sudah Dihapus / Tidak Ditemukan")
                self.btn_play_file.configure(state="disabled")
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
            save_history(histories)
            self._load_history_view()
            # Reset detail view
            self.hist_canvas.delete("all")
            self.hist_canvas.create_text(145, 97, text="Pilih item riwayat", fill=TEXT_MUTED, font=FONT_BODY)
            self.lbl_h_id.configure(text="-")
            self.lbl_h_title.configure(text="-")
            self.lbl_h_cv.configure(text="-")
            self.lbl_h_circle.configure(text="-")
            self.lbl_h_rating.configure(text="-", text_color=TEXT_PRIMARY)
            self.lbl_h_genre.configure(text="-")
            self.lbl_h_path.configure(text="-")
            self.btn_play_file.configure(state="disabled")
            if hasattr(self, "btn_open_folder_file"):
                self.btn_open_folder_file.configure(state="disabled")
            self.btn_del_history.configure(state="disabled")
            self._log(t("log_history_entry_deleted", rjid=deleted.get("rjid", "-")))
