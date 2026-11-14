import io
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import urllib.request
import customtkinter as ctk

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
    STATUS_WARNING,
    SURFACE_CARD,
    SURFACE_ELEVATED,
    SURFACE_INPUT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class QueueTabMixin:
    """Mixin untuk membangun antarmuka dan menangani aksi pada Tab Antrean (Queue) v1.2.0."""
    def _build_queue_tab(self):
        container = self.tab_queue

        # Layout 2 Kolom: Kiri (Input & Tabel), Kanan (Cover & Info Detail)
        main_container = ctk.CTkFrame(container, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        left_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, SPACE_MD))

        # 1. Baris Input & Tombol Tambah (Modern Card)
        self.input_card = ctk.CTkFrame(
            left_panel,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.input_card.pack(fill="x", pady=(0, SPACE_MD), padx=0)

        input_header = ctk.CTkFrame(self.input_card, fg_color="transparent")
        input_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM))

        self.lbl_input_title = ctk.CTkLabel(
            input_header,
            text=t("lbl_input_group"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_input_title.pack(side="left")

        input_row = ctk.CTkFrame(self.input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=SPACE_LG, pady=(2, SPACE_SM))

        self.id_entry = ctk.CTkEntry(
            input_row,
            placeholder_text=f"Misal: {self.placeholder_text} atau https://...",
            font=FONT_CODE,
            corner_radius=RADIUS_INPUT,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
            text_color=TEXT_PRIMARY,
            height=38,
        )
        self.id_entry.pack(side="left", fill="x", expand=True, padx=(0, SPACE_SM))
        self.id_entry.bind("<Return>", lambda e: self._add_to_queue())

        self.paste_btn = ctk.CTkButton(
            input_row,
            text=f" {t('btn_paste')}",
            image=get_icon("clipboard", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_PRIMARY,
            corner_radius=RADIUS_BUTTON,
            height=38,
            width=100,
            command=self._paste_from_clipboard,
        )
        self.paste_btn.pack(side="left", padx=(0, SPACE_SM))

        self.add_btn = ctk.CTkButton(
            input_row,
            text=f" {t('btn_add_queue')}",
            image=get_icon("plus", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
            text_color="#ffffff",
            corner_radius=RADIUS_BUTTON,
            height=38,
            width=140,
            command=self._add_to_queue,
        )
        self.add_btn.pack(side="right")

        opts_row = ctk.CTkFrame(self.input_card, fg_color="transparent")
        opts_row.pack(fill="x", padx=SPACE_LG, pady=(0, SPACE_MD))

        self.chk_name = ctk.CTkCheckBox(
            opts_row,
            text=t("chk_detailed_name"),
            variable=self.opt_detailed_name,
            command=self._save_options,
            font=FONT_CAPTION,
            text_color=TEXT_SECONDARY,
            corner_radius=RADIUS_BUTTON,
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_HOVER,
        )
        self.chk_name.pack(side="left")

        # 2. Tabel Antrean & Kontrol Aksi (Modern Card)
        self.queue_card = ctk.CTkFrame(
            left_panel,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )

        # Action Buttons Header
        queue_actions = ctk.CTkFrame(self.queue_card, fg_color="transparent")
        queue_actions.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM))

        self.lbl_queue_heading = ctk.CTkLabel(
            queue_actions,
            text=t("tab_queue"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_queue_heading.pack(side="left", padx=(0, SPACE_LG))

        self.start_btn = ctk.CTkButton(
            queue_actions,
            text=f" {t('btn_start_download')}",
            image=get_icon("play", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=STATUS_SUCCESS,
            hover_color="#059669",
            text_color="#ffffff",
            corner_radius=RADIUS_BUTTON,
            height=34,
            width=135,
            command=self._start_download_thread,
        )
        self.start_btn.pack(side="left", padx=(0, SPACE_SM))

        self.stop_btn = ctk.CTkButton(
            queue_actions,
            text=f" {t('btn_stop_download')}",
            image=get_icon("stop", size=(16, 16)),
            font=FONT_BODY_BOLD,
            fg_color=STATUS_DANGER,
            hover_color="#e11d48",
            text_color="#ffffff",
            corner_radius=RADIUS_BUTTON,
            height=34,
            width=115,
            state="disabled",
            command=self._stop_downloads,
        )
        self.stop_btn.pack(side="left", padx=(0, SPACE_SM))

        self.clear_btn = ctk.CTkButton(
            queue_actions,
            text=f" {t('btn_clear_queue')}",
            image=get_icon("trash", size=(16, 16)),
            font=FONT_BODY,
            fg_color=SURFACE_ELEVATED,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_SECONDARY,
            corner_radius=RADIUS_BUTTON,
            height=34,
            width=125,
            command=self._clear_queue,
        )
        self.clear_btn.pack(side="right")

        # Treeview Container
        tree_container = ctk.CTkFrame(
            self.queue_card,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_INPUT,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        tree_container.pack(fill="both", expand=True, padx=SPACE_LG, pady=(0, SPACE_MD))

        cols = ("no", "rjid", "title", "status")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse", style="Treeview")
        self.tree.heading("no", text="#", anchor="center")
        self.tree.heading("rjid", text=t("col_rjid"), anchor="center")
        self.tree.heading("title", text=t("col_title"), anchor="w")
        self.tree.heading("status", text=t("col_status"), anchor="center")

        self.tree.column("no", width=45, anchor="center")
        self.tree.column("rjid", width=120, anchor="center")
        self.tree.column("title", width=340, anchor="w")
        self.tree.column("status", width=120, anchor="center")

        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview, style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        tree_scroll.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # 3. Progress Card (Status, Bar, Speed, ETA)
        progress_card = ctk.CTkFrame(
            left_panel,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )

        p_info_row = ctk.CTkFrame(progress_card, fg_color="transparent")
        p_info_row.pack(fill="x", padx=SPACE_LG, pady=(SPACE_SM, SPACE_SM // 2))

        self.lbl_progress_status = ctk.CTkLabel(
            p_info_row,
            text=f"{t('col_status')}: {t('status_ready')}",
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_progress_status.pack(side="left")

        self.lbl_progress_pct = ctk.CTkLabel(
            p_info_row,
            text="0%",
            font=FONT_BODY_BOLD,
            text_color=STATUS_SUCCESS,
        )
        self.lbl_progress_pct.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(
            progress_card,
            corner_radius=9999,
            height=10,
            fg_color=SURFACE_INPUT,
            progress_color=ACCENT_PRIMARY,
        )
        self.progress_bar.pack(fill="x", padx=SPACE_LG, pady=(2, 6))
        self.progress_bar.set(0)

        detail_row = ctk.CTkFrame(progress_card, fg_color="transparent")
        detail_row.pack(fill="x", padx=SPACE_LG, pady=(2, SPACE_SM))

        self.lbl_progress_speed = ctk.CTkLabel(
            detail_row,
            text="Kecepatan: -",
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
        )
        self.lbl_progress_speed.pack(side="left", padx=(0, SPACE_LG))

        self.lbl_progress_eta = ctk.CTkLabel(
            detail_row,
            text="Sisa Waktu: -",
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
        )
        self.lbl_progress_eta.pack(side="left", padx=(0, SPACE_LG))

        self.lbl_progress_size = ctk.CTkLabel(
            detail_row,
            text="Ukuran: -",
            font=FONT_CAPTION,
            text_color=TEXT_MUTED,
        )
        self.lbl_progress_size.pack(side="right")

        # 4. Status & Log Konsol
        log_card = ctk.CTkFrame(
            left_panel,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=SPACE_MD, pady=(SPACE_SM, 2))

        self.lbl_log_header = ctk.CTkLabel(
            log_header,
            text=t("lbl_log_header"),
            font=FONT_CAPTION,
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.lbl_log_header.pack(side="left")

        log_inner = ctk.CTkFrame(log_card, fg_color="transparent")
        log_inner.pack(fill="both", expand=True, padx=SPACE_SM, pady=(2, SPACE_SM))

        self.log_text = tk.Text(
            log_inner,
            height=6,
            bg=SURFACE_INPUT,
            fg=TEXT_SECONDARY,
            font=FONT_CODE,
            bd=0,
            wrap="word",
            insertbackground=ACCENT_PRIMARY,
            relief="flat",
        )
        log_scroll = ttk.Scrollbar(log_inner, orient="vertical", command=self.log_text.yview, style="Vertical.TScrollbar")
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Susun panel kiri: Elemen bawah dipack lebih dulu agar tinggi minimumnya terjamin
        log_card.pack(side="bottom", fill="x")
        progress_card.pack(side="bottom", fill="x", pady=(0, SPACE_MD))
        self.queue_card.pack(side="top", fill="both", expand=True, pady=(0, SPACE_MD))

        # Panel Kanan: Preview Thumbnail & Info Card
        self.right_panel = ctk.CTkFrame(
            main_container,
            width=320,
            corner_radius=RADIUS_CARD,
            fg_color=SURFACE_CARD,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.right_panel.pack(side="right", fill="both", pady=0)
        self.right_panel.pack_propagate(False)

        right_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        right_header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_SM))

        self.lbl_preview_title = ctk.CTkLabel(
            right_header,
            text=t("lbl_preview_title"),
            font=FONT_SECTION,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_preview_title.pack(side="left")

        # Canvas Cover
        self.cover_canvas = tk.Canvas(
            self.right_panel,
            bg=SURFACE_INPUT,
            width=290,
            height=195,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_SUBTLE,
        )
        self.cover_canvas.pack(pady=4, padx=SPACE_LG)
        self.cover_canvas.create_text(
            145, 97, text="Tidak ada cover", fill=TEXT_MUTED, font=FONT_BODY
        )

        # Info Labels
        info_inner = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        info_inner.pack(fill="both", expand=True, padx=SPACE_SM, pady=(4, SPACE_MD))

        self.lbl_q_id = self._create_info_row(info_inner, "Kode RJ", "-", "lbl_detail_rjid")
        self.lbl_q_title = self._create_info_row(info_inner, "Judul", "-", "lbl_detail_title")
        self.lbl_q_cv = self._create_info_row(info_inner, "CV / Seiyuu", "-", "lbl_detail_cv")
        self.lbl_q_circle = self._create_info_row(info_inner, "Circle / Maker", "-", "lbl_detail_circle")
        self.lbl_q_rating = self._create_info_row(info_inner, "Rating Usia", "-", "lbl_detail_age")
        self.lbl_q_genre = self._create_info_row(info_inner, "Genre / Tag", "-", "lbl_detail_genre")

    def _create_info_row(self, parent, label_text, default_value, key=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=3)

        lbl = ctk.CTkLabel(
            frame,
            text=f"{label_text}:",
            font=FONT_CAPTION,
            text_color=ACCENT_PRIMARY,
            anchor="w",
        )
        lbl.pack(fill="x")

        val_lbl = ctk.CTkLabel(
            frame,
            text=default_value,
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=275,
            justify="left",
        )
        val_lbl.pack(fill="x")

        if not hasattr(self, "_info_rows"):
            self._info_rows = []
        self._info_rows.append((lbl, key))

        return val_lbl

    def _save_options(self):
        val = self.opt_detailed_name.get()
        self.config["use_detailed_filename"] = val
        if hasattr(self, "var_detailed_name"):
            self.var_detailed_name.set(val)
        save_config(self.config)

    def _log(self, text):
        def _append():
            if hasattr(self, "log_text"):
                self.log_text.insert("end", text + "\n")
                self.log_text.see("end")
        self.after(0, _append)

    def _add_to_queue(self):
        raw_text = self.id_entry.get().strip()
        if not raw_text or raw_text == self.placeholder_text:
            show_dark_info(self, "Informasi", "Silakan masukkan kode RJ terlebih dahulu.")
            return

        tokens = re.split(r"[\s,;]+", raw_text)
        added_count = 0

        for tok in tokens:
            rjid = resolve_input_to_rjid(tok)
            if not rjid:
                continue

            if any(item["rjid"] == rjid for item in self.queue_items):
                continue

            row_id = len(self.queue_items) + 1
            item = {
                "no": row_id,
                "rjid": rjid,
                "title": "Memuat info...",
                "status": "Pending",
                "cover_url": "",
                "cover_image": None,
                "circle": "-",
                "cv": "-",
                "age_rating": "-",
                "genre": "-",
            }
            self.queue_items.append(item)
            self.tree.insert("", "end", iid=str(row_id - 1), values=(row_id, rjid, "Memuat info...", "Pending"))
            added_count += 1

            threading.Thread(target=self._fetch_metadata_for_item, args=(row_id - 1, rjid), daemon=True).start()

        if added_count > 0:
            self.id_entry.delete(0, "end")
            self._log(f"[+] Menambahkan {added_count} item ke antrean.")
        else:
            show_dark_warning(self, "Peringatan", "Tidak ada kode RJ baru yang valid atau item sudah ada di antrean.")

    def _fetch_metadata_for_item(self, row_idx, rjid):
        def _update_ui(meta, pil_img):
            try:
                if row_idx < len(self.queue_items):
                    item = self.queue_items[row_idx]
                    title = meta.get("title") or rjid
                    item["title"] = title
                    item["cover_url"] = meta.get("cover_url", "")
                    item["cover_image"] = pil_img
                    item["circle"] = meta.get("circle", "-")
                    item["cv"] = meta.get("cv", "-")
                    item["age_rating"] = meta.get("age_rating", "-")
                    item["genre"] = meta.get("genre", "-")

                    if hasattr(self, "tree") and self.tree.winfo_exists():
                        self.tree.set(str(row_idx), "title", title)
                        selected = self.tree.selection()
                        if selected and int(selected[0]) == row_idx:
                            self._show_info_card(item)
                            if pil_img:
                                self._render_cover_image(pil_img)
            except Exception:
                pass

        meta = fetch_dlsite_metadata(rjid)
        pil_img = None
        cover_to_fetch = resolve_best_cover_url(rjid, meta.get("cover_url", ""))

        if cover_to_fetch:
            os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
            cache_file = os.path.join(".cache", "covers", f"{rjid}.jpg")

            if os.path.exists(cache_file):
                try:
                    pil_img = Image.open(cache_file)
                except Exception:
                    pass

            if not pil_img:
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
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        img_data = resp.read()
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((290, 195))
                    pil_img.convert("RGB").save(cache_file, "JPEG", quality=85)
                except Exception:
                    pass

        try:
            self.after(0, lambda: _update_ui(meta, pil_img))
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
                self.cover_canvas.create_text(145, 97, text="Memuat cover...", fill=TEXT_MUTED, font=FONT_BODY)

    def _show_info_card(self, item):
        self.lbl_q_id.configure(text=item.get("rjid", "-"))
        self.lbl_q_title.configure(text=item.get("title", "-"))
        self.lbl_q_cv.configure(text=item.get("cv", "-"))
        self.lbl_q_circle.configure(text=item.get("circle", "-"))

        rating = item.get("age_rating", "-")
        self.lbl_q_rating.configure(
            text=rating,
            text_color=STATUS_DANGER if "18" in rating else STATUS_SUCCESS,
        )
        self.lbl_q_genre.configure(text=item.get("genre", "-"))

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
        self.cover_canvas.create_text(145, 97, text="Tidak ada cover", fill=TEXT_MUTED, font=FONT_BODY)
        self.lbl_q_id.configure(text="-")
        self.lbl_q_title.configure(text="-")
        self.lbl_q_cv.configure(text="-")
        self.lbl_q_circle.configure(text="-")
        self.lbl_q_rating.configure(text="-", text_color=TEXT_PRIMARY)
        self.lbl_q_genre.configure(text="-")
        self._update_progress(0, "Antrean dibersihkan")
        self._log("[i] Antrean dibersihkan.")

    def _paste_from_clipboard(self):
        try:
            clip_text = self.clipboard_get()
            if not clip_text:
                return

            tokens = re.split(r"[\s,;]+", clip_text.strip())
            valid_rjs = []
            for tok in tokens:
                rjid = resolve_input_to_rjid(tok)
                if rjid and rjid not in valid_rjs:
                    valid_rjs.append(rjid)

            if valid_rjs:
                self.id_entry.delete(0, "end")
                self.id_entry.insert(0, " ".join(valid_rjs))
                self._add_to_queue()
            else:
                self.id_entry.delete(0, "end")
                self.id_entry.insert(0, clip_text.strip())
        except Exception as e:
            self._log(f"[!] Gagal membaca clipboard: {e}")
