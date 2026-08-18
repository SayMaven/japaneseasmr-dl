import html
import io
import json
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.request
from PIL import Image, ImageTk

from config_manager import (
    add_to_history,
    cache_cover_image,
    discover_all_audio_tracks,
    get_download_dir,
    load_config,
    load_history,
    resolve_audio_url,
    save_config,
    set_download_dir,
)

REFERER = "https://japaneseasmr.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


import ctypes


def apply_dark_titlebar(window):
    """Menerapkan Dark Titlebar pada Windows 10/11 agar titlebar jendela utama ikut berwarna gelap."""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        value = ctypes.c_int(2)
        set_attr = ctypes.windll.dwmapi.DwmSetWindowAttribute
        if set_attr(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)) != 0:
            set_attr(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


class InAppModal:
    """Modal Dialog In-App yang muncul melayang elegan di tengah jendela aplikasi tanpa menutupi background."""
    @staticmethod
    def show(parent, title, message, dialog_type="info", confirm_text="OK", cancel_text="Batal"):
        result = [False]
        wait_var = tk.BooleanVar(parent, value=False)

        type_configs = {
            "info": {"bg": "#50fa7b", "fg": "#1e1e2e", "symbol": "i", "title": title or "Selesai", "title_color": "#50fa7b", "border": "#50fa7b"},
            "warning": {"bg": "#f1fa8c", "fg": "#1e1e2e", "symbol": "!", "title": title or "Peringatan", "title_color": "#f1fa8c", "border": "#f1fa8c"},
            "error": {"bg": "#ff5555", "fg": "#ffffff", "symbol": "✕", "title": title or "Error", "title_color": "#ff5555", "border": "#ff5555"},
            "question": {"bg": "#8be9fd", "fg": "#1e1e2e", "symbol": "?", "title": title or "Konfirmasi", "title_color": "#8be9fd", "border": "#bd93f9"},
        }
        cfg = type_configs.get(dialog_type, type_configs["info"])

        # Card Dialog Melayang di Tengah Jendela (Tanpa Frame Hitam Fullscreen)
        outer_card = tk.Frame(parent, bg=cfg["border"], bd=2)
        outer_card.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(outer_card, bg="#282a36", padx=26, pady=22)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        # Header (Canvas Badge + Judul)
        header = tk.Frame(card, bg="#282a36")
        header.pack(fill="x", pady=(0, 14))

        badge = tk.Canvas(header, width=30, height=30, bg="#282a36", highlightthickness=0)
        badge.pack(side="left", padx=(0, 12))
        badge.create_oval(2, 2, 28, 28, fill=cfg["bg"], outline=cfg["bg"])
        badge.create_text(15, 15, text=cfg["symbol"], fill=cfg["fg"], font=("Segoe UI", 12, "bold"))

        lbl_title = tk.Label(header, text=cfg["title"], font=("Segoe UI", 12, "bold"), bg="#282a36", fg=cfg["title_color"])
        lbl_title.pack(side="left", anchor="center")

        # Message Text
        msg_frame = tk.Frame(card, bg="#282a36")
        msg_frame.pack(fill="both", expand=True, pady=(0, 20))

        lbl_msg = tk.Label(
            msg_frame,
            text=message,
            font=("Segoe UI", 10),
            bg="#282a36",
            fg="#f8f8f2",
            wraplength=420,
            justify="left",
            anchor="w",
        )
        lbl_msg.pack(fill="x")

        # Action Buttons
        btn_frame = tk.Frame(card, bg="#282a36")
        btn_frame.pack(fill="x")

        def _close(val):
            if outer_card.winfo_exists():
                result[0] = val
                outer_card.destroy()
                wait_var.set(True)

        if dialog_type == "question":
            btn_cancel = tk.Button(
                btn_frame,
                text=cancel_text,
                font=("Segoe UI", 9),
                bg="#44475a",
                fg="#f8f8f2",
                activebackground="#6272a4",
                activeforeground="#ffffff",
                bd=0,
                padx=18,
                pady=6,
                cursor="hand2",
                command=lambda: _close(False),
            )
            btn_cancel.pack(side="right", padx=(10, 0))

            btn_ok = tk.Button(
                btn_frame,
                text=confirm_text,
                font=("Segoe UI", 9, "bold"),
                bg="#bd93f9",
                fg="#1e1e2e",
                activebackground="#ff79c6",
                bd=0,
                padx=18,
                pady=6,
                cursor="hand2",
                command=lambda: _close(True),
            )
            btn_ok.pack(side="right")
            btn_ok.focus_set()
        else:
            btn_ok = tk.Button(
                btn_frame,
                text=confirm_text,
                font=("Segoe UI", 9, "bold"),
                bg="#bd93f9",
                fg="#1e1e2e",
                activebackground="#ff79c6",
                bd=0,
                padx=24,
                pady=6,
                cursor="hand2",
                command=lambda: _close(True),
            )
            btn_ok.pack(side="right")
            btn_ok.focus_set()

        parent.bind("<Return>", lambda e: _close(True) if outer_card.winfo_exists() else None)
        parent.bind("<Escape>", lambda e: _close(False) if outer_card.winfo_exists() else None)

        outer_card.lift()
        parent.wait_variable(wait_var)
        return result[0]


def show_dark_info(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="info", confirm_text="OK")


def show_dark_warning(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="warning", confirm_text="Mengerti")


def show_dark_error(parent, title, message):
    InAppModal.show(parent, title, message, dialog_type="error", confirm_text="Tutup")


def ask_dark_yesno(parent, title, message, confirm_text="Ya", cancel_text="Batal"):
    return InAppModal.show(parent, title, message, dialog_type="question", confirm_text=confirm_text, cancel_text=cancel_text)


def sanitize_filename(name):
    """Membersihkan karakter yang dilarang pada sistem file Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().rstrip(".")
    return clean if clean else "audio"


def fetch_dlsite_metadata(rj_id):
    """Mengambil metadata karya (Judul, CV, Circle, Genre, Rating) dari DLsite."""
    info = {
        "title": "",
        "cv": "-",
        "circle": "-",
        "genre": "-",
        "age_rating": "-",
        "cover_url": f"https://pic.weeabo0.xyz/{rj_id}_img_main.jpg",
    }
    urls = [
        f"https://www.dlsite.com/maniax/work/=/product_id/{rj_id}.html",
        f"https://www.dlsite.com/home/work/=/product_id/{rj_id}.html",
        f"https://www.dlsite.com/girls/work/=/product_id/{rj_id}.html",
        f"https://www.dlsite.com/pro/work/=/product_id/{rj_id}.html",
    ]

    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Cookie": "adultchecked=1; locale=ja_JP",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                page_html = resp.read().decode("utf-8", errors="ignore")

            # 1. Ambil Judul
            title_match = re.search(r'<meta itemprop="name" content="(.*?)">', page_html)
            if not title_match:
                title_match = re.search(r'id=["\']work_name["\'][^>]*>(.*?)</h1>', page_html, re.DOTALL)
            if title_match:
                raw_title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
                raw_title = raw_title.replace(" | DLsite", "").replace(" - DLsite", "").strip()
                info["title"] = html.unescape(raw_title)

            # 2. Ambil Circle / Maker
            maker_match = re.search(r'<th>\s*(?:サークル名|ブランド名|メーカー名|著者)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if maker_match:
                makers = re.findall(r'<a[^>]*>(.*?)</a>', maker_match.group(1), re.DOTALL)
                clean_makers = [re.sub(r'<[^>]+>', '', m).strip() for m in makers if re.sub(r'<[^>]+>', '', m).strip()]
                if clean_makers:
                    info["circle"] = html.unescape(", ".join(clean_makers))

            if info["circle"] == "-":
                brand_match = re.search(r'<div itemprop="brand"[^>]*>.*?<meta itemprop="name" content="(.*?)">', page_html, re.DOTALL)
                if not brand_match:
                    brand_match = re.search(r'"position":\s*3,\s*"name":\s*"([^"]+)"', page_html)
                if brand_match:
                    raw_brand = html.unescape(brand_match.group(1).strip())
                    if "/" in raw_brand:
                        parts = raw_brand.split("/", 1)
                        info["circle"] = parts[0].strip()
                        if info["cv"] == "-":
                            info["cv"] = parts[1].strip()
                    else:
                        info["circle"] = raw_brand

            # 3. Ambil CV / Voice Actor (Bisa 1 atau banyak Seiyuu)
            cv_match = re.search(r'<th>\s*(?:声優|キャラクターボイス|ボイス|キャスト)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if cv_match:
                cvs = re.findall(r'<a[^>]*>(.*?)</a>', cv_match.group(1), re.DOTALL)
                clean_cvs = [re.sub(r'<[^>]+>', '', c).strip() for c in cvs if re.sub(r'<[^>]+>', '', c).strip()]
                if clean_cvs:
                    info["cv"] = html.unescape(", ".join(clean_cvs))
                else:
                    raw_cv_td = re.sub(r'<[^>]+>', '', cv_match.group(1)).strip()
                    if raw_cv_td:
                        info["cv"] = html.unescape(raw_cv_td)

            # 4. Fallback CV dari Judul / Deskripsi jika belum terisi
            if info["cv"] == "-":
                desc_match = re.search(r'<meta itemprop="description" content="(.*?)">', page_html, re.DOTALL)
                desc_text = html.unescape(desc_match.group(1)) if desc_match else ""
                combined_text = f"{info['title']} {desc_text}"

                cv_entries = re.findall(r'(?:CV|声優|キャラクターボイス|ボイス|キャスト|声の出演)[：:\s【\[（(]+([^\n\r,、/】\]）)\s]+)', combined_text, re.IGNORECASE)
                valid_cvs = []
                for entry in cv_entries:
                    clean_entry = entry.strip()
                    if 1 < len(clean_entry) < 30 and not clean_entry.startswith("http") and clean_entry not in valid_cvs:
                        valid_cvs.append(clean_entry)
                if valid_cvs:
                    info["cv"] = ", ".join(valid_cvs)

            # 5. Ambil Genre / Tag
            genre_match = re.search(r'<th>\s*(?:ジャンル|タグ)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if genre_match:
                g_links = re.findall(r'<a[^>]*>(.*?)</a>', genre_match.group(1), re.DOTALL)
                clean_genres = [re.sub(r'<[^>]+>', '', g).strip() for g in g_links if re.sub(r'<[^>]+>', '', g).strip()]
                if clean_genres:
                    info["genre"] = html.unescape(", ".join(clean_genres))
                else:
                    raw_g = re.sub(r'<[^>]+>', '', genre_match.group(1)).strip()
                    if raw_g:
                        info["genre"] = html.unescape(", ".join([x.strip() for x in raw_g.splitlines() if x.strip()]))

            # 6. Ambil Rating Usia (年齢指定)
            age_match = re.search(r'<th>\s*(?:年齢指定|レーティング)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if age_match:
                clean_age = re.sub(r'<[^>]+>', '', age_match.group(1)).strip()
                if clean_age:
                    info["age_rating"] = html.unescape(clean_age)
            elif "maniax" in url or "r18" in page_html.lower():
                info["age_rating"] = "R18"

            if info["title"]:
                break
        except Exception:
            continue

    return info


class JapaneseASMRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JapaneseASMR Downloader & Cover Embedder")
        self.geometry("1060x820")
        self.minsize(940, 720)
        self.configure(bg="#1e1e2e")
        apply_dark_titlebar(self)

        # Config & State
        self.config = load_config()
        self.is_downloading = False
        self.stop_requested = False
        self.queue_items = []
        self.current_preview_image = None
        self.placeholder_text = "RJ01673437"

        self._init_styles()
        self._build_ui()
        self._load_history_view()

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

        title_label = tk.Label(
            header_frame,
            text="🎧 JapaneseASMR Downloader + Cover Embedder",
            font=("Segoe UI", 15, "bold"),
            bg="#282a36",
            fg="#50fa7b",
        )
        title_label.pack(side="left", padx=20, pady=12)

        # Directory Selector & Open Folder Buttons
        dir_controls = tk.Frame(header_frame, bg="#282a36")
        dir_controls.pack(side="right", padx=20, pady=10)

        change_dir_btn = tk.Button(
            dir_controls,
            text="📁 Ganti Folder",
            font=("Segoe UI", 9, "bold"),
            bg="#bd93f9",
            fg="#1e1e2e",
            activebackground="#ff79c6",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._change_download_dir,
        )
        change_dir_btn.pack(side="left", padx=(0, 8))

        open_folder_btn = tk.Button(
            dir_controls,
            text="📂 Buka Folder",
            font=("Segoe UI", 9, "bold"),
            bg="#44475a",
            fg="#8be9fd",
            activebackground="#6272a4",
            activeforeground="#ffffff",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._open_downloads_folder,
        )
        open_folder_btn.pack(side="left")

        # Bar status folder simpan
        dir_bar = tk.Frame(self, bg="#181825", height=26)
        dir_bar.pack(fill="x", side="top")
        self.lbl_current_dir = tk.Label(
            dir_bar,
            text=f"📁 Lokasi Simpan: {os.path.abspath(get_download_dir())}",
            font=("Segoe UI", 8),
            bg="#181825",
            fg="#a6adc8",
            anchor="w",
        )
        self.lbl_current_dir.pack(fill="x", padx=15, pady=2)

        # Notebook (Tab Antrean vs Riwayat)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        # Tab 1: Download & Antrean
        self.tab_queue = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(self.tab_queue, text=" 📥 Antrean Download ")

        # Tab 2: Riwayat Unduhan
        self.tab_history = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(self.tab_history, text=" 📜 Riwayat Unduhan ")
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._load_history_view())

        self._build_queue_tab()
        self._build_history_tab()

    def _build_queue_tab(self):
        main_container = self.tab_queue

        left_panel = tk.Frame(main_container, bg="#1e1e2e")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # 1. Input Box
        input_frame = tk.LabelFrame(
            left_panel,
            text=" Input Kode RJ / URL ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        input_frame.pack(fill="x", pady=(0, 10), ipady=5)

        input_inner = tk.Frame(input_frame, bg="#1e1e2e")
        input_inner.pack(fill="x", padx=10, pady=5)

        self.id_entry = tk.Entry(
            input_inner,
            font=("Consolas", 11),
            bg="#282a36",
            fg="#6272a4",
            insertbackground="#50fa7b",
            bd=1,
            relief="solid",
        )
        self.id_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=4)
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

        add_btn = tk.Button(
            input_inner,
            text="➕ Tambah ke Antrean",
            font=("Segoe UI", 9, "bold"),
            bg="#bd93f9",
            fg="#1e1e2e",
            activebackground="#ff79c6",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._add_to_queue,
        )
        add_btn.pack(side="right")

        # 2. Tabel Antrean
        queue_frame = tk.LabelFrame(
            left_panel,
            text=" Daftar Antrean Download ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        queue_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("no", "rjid", "title", "status")
        self.tree = ttk.Treeview(queue_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("no", text="#", anchor="center")
        self.tree.heading("rjid", text="Kode RJ", anchor="center")
        self.tree.heading("title", text="Judul / Keterangan", anchor="w")
        self.tree.heading("status", text="Status", anchor="center")

        self.tree.column("no", width=35, anchor="center")
        self.tree.column("rjid", width=110, anchor="center")
        self.tree.column("title", width=260, anchor="w")
        self.tree.column("status", width=110, anchor="center")

        tree_scroll = ttk.Scrollbar(queue_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        tree_scroll.pack(side="right", fill="y", pady=5, padx=(0, 5))
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Action Buttons
        btn_action_frame = tk.Frame(left_panel, bg="#1e1e2e")
        btn_action_frame.pack(fill="x", pady=(0, 10))

        self.start_btn = tk.Button(
            btn_action_frame,
            text="▶️ Mulai Download",
            font=("Segoe UI", 10, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            activebackground="#8be9fd",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._start_download_thread,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_action_frame,
            text="⏹️ Berhenti",
            font=("Segoe UI", 10, "bold"),
            bg="#ff5555",
            fg="#ffffff",
            activebackground="#ff6e6e",
            bd=0,
            padx=14,
            pady=6,
            state="disabled",
            cursor="hand2",
            command=self._stop_downloads,
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        clear_btn = tk.Button(
            btn_action_frame,
            text="🗑️ Bersihkan Antrean",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            activebackground="#6272a4",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._clear_queue,
        )
        clear_btn.pack(side="right")

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

        # Log Console
        log_frame = tk.LabelFrame(
            left_panel,
            text=" Status & Log Konsol ",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
        )
        log_frame.pack(fill="x", pady=(0, 5))

        self.log_text = tk.Text(
            log_frame,
            height=5,
            bg="#181825",
            fg="#a6adc8",
            font=("Consolas", 9),
            bd=0,
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Panel Kanan: Preview Thumbnail & Info Card
        right_panel = tk.LabelFrame(
            main_container,
            text=" Informasi Karya & Preview ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=330,
        )
        right_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        right_panel.pack_propagate(False)

        # Bottom Options (Docked first)
        options_frame = tk.Frame(right_panel, bg="#1e1e2e")
        options_frame.pack(fill="x", padx=12, pady=(0, 10), side="bottom")

        self.opt_detailed_name = tk.BooleanVar(value=self.config.get("use_detailed_filename", True))
        chk_name = tk.Checkbutton(
            options_frame,
            text="Gunakan Judul Asli di Nama File",
            variable=self.opt_detailed_name,
            command=self._save_options,
            bg="#1e1e2e",
            fg="#8be9fd",
            selectcolor="#282a36",
            activebackground="#1e1e2e",
            activeforeground="#8be9fd",
            font=("Segoe UI", 8),
        )
        chk_name.pack(anchor="w")

        # Canvas Cover
        self.cover_canvas = tk.Canvas(
            right_panel,
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
        info_inner = tk.Frame(right_panel, bg="#1e1e2e")
        info_inner.pack(fill="both", expand=True, padx=12, pady=3)

        self.lbl_id = self._create_info_row(info_inner, "Kode RJ", "-")
        self.lbl_title = self._create_info_row(info_inner, "Judul", "-")
        self.lbl_cv = self._create_info_row(info_inner, "CV / Seiyuu", "-")
        self.lbl_circle = self._create_info_row(info_inner, "Circle / Maker", "-")
        self.lbl_rating = self._create_info_row(info_inner, "Rating Usia", "-")
        self.lbl_genre = self._create_info_row(info_inner, "Genre / Tag", "-")

    def _build_history_tab(self):
        container = self.tab_history

        # Panel Kiri: Tabel Riwayat
        left_h_panel = tk.Frame(container, bg="#1e1e2e")
        left_h_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # Header Riwayat
        h_header = tk.Frame(left_h_panel, bg="#1e1e2e")
        h_header.pack(fill="x", pady=(0, 8))

        lbl_hist_title = tk.Label(
            h_header,
            text="Daftar Audio yang Pernah Diunduh",
            font=("Segoe UI", 11, "bold"),
            bg="#1e1e2e",
            fg="#50fa7b",
        )
        lbl_hist_title.pack(side="left")

        refresh_btn = tk.Button(
            h_header,
            text="🔄 Segarkan",
            font=("Segoe UI", 9),
            bg="#44475a",
            fg="#f8f8f2",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._load_history_view,
        )
        refresh_btn.pack(side="right")

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
        right_h_panel = tk.LabelFrame(
            container,
            text=" Detail Riwayat Koleksi ",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#f8f8f2",
            bd=1,
            relief="solid",
            width=330,
        )
        right_h_panel.pack(side="right", fill="both", padx=(5, 0), pady=10)
        right_h_panel.pack_propagate(False)

        # Tombol Buka File di Riwayat (Pack di bottom terlebih dahulu)
        h_actions = tk.Frame(right_h_panel, bg="#1e1e2e")
        h_actions.pack(fill="x", padx=12, pady=10, side="bottom")

        self.btn_play_file = tk.Button(
            h_actions,
            text="▶️ Putar / Buka File",
            font=("Segoe UI", 9, "bold"),
            bg="#50fa7b",
            fg="#1e1e2e",
            bd=0,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self._open_selected_history_file,
        )
        self.btn_play_file.pack(fill="x", pady=(0, 6))

        self.btn_del_history = tk.Button(
            h_actions,
            text="🗑️ Hapus dari Riwayat",
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
            right_h_panel,
            bg="#282a36",
            width=290,
            height=195,
            bd=0,
            highlightthickness=1,
            highlightbackground="#44475a",
        )
        self.hist_canvas.pack(pady=8, padx=10)
        self.hist_canvas.create_text(145, 97, text="Pilih item riwayat", fill="#6272a4", font=("Segoe UI", 10))

        h_info_inner = tk.Frame(right_h_panel, bg="#1e1e2e")
        h_info_inner.pack(fill="both", expand=True, padx=12, pady=3)

        self.lbl_h_id = self._create_info_row(h_info_inner, "Kode RJ", "-")
        self.lbl_h_title = self._create_info_row(h_info_inner, "Judul", "-")
        self.lbl_h_cv = self._create_info_row(h_info_inner, "CV / Seiyuu", "-")
        self.lbl_h_circle = self._create_info_row(h_info_inner, "Circle / Maker", "-")
        self.lbl_h_rating = self._create_info_row(h_info_inner, "Rating Usia", "-")
        self.lbl_h_genre = self._create_info_row(h_info_inner, "Genre / Tag", "-")
        self.lbl_h_path = self._create_info_row(h_info_inner, "Status File", "-")

    def _create_info_row(self, parent, label_text, default_value):
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
            m = re.search(r"(RJ\d+|\d{6,8})", token, re.IGNORECASE)
            if m:
                rjid = m.group(1).upper()
                if not rjid.startswith("RJ"):
                    rjid = f"RJ{rjid}"
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
            try:
                req = urllib.request.Request(meta["cover_url"], headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    img_data = resp.read()
                pil_img = Image.open(io.BytesIO(img_data))
                pil_img.thumbnail((280, 195))
                self.queue_items[index]["cover_image"] = pil_img

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
        self.lbl_id.config(text=item["rjid"])
        self.lbl_title.config(text=item["title"])
        self.lbl_cv.config(text=item["cv"])
        self.lbl_circle.config(text=item["circle"])
        
        rating = item.get("age_rating", "-")
        self.lbl_rating.config(text=rating, fg="#ff79c6" if "18" in rating else "#50fa7b")
        self.lbl_genre.config(text=item.get("genre", "-"))

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
        self.lbl_id.config(text="-")
        self.lbl_title.config(text="-")
        self.lbl_cv.config(text="-")
        self.lbl_circle.config(text="-")
        self.lbl_rating.config(text="-", fg="#f8f8f2")
        self.lbl_genre.config(text="-")
        self._update_progress(0, "Antrean dibersihkan")
        self._log("[i] Antrean dibersihkan.")

    def _log(self, text):
        def _append():
            self.log_text.insert("end", text + "\n")
            self.log_text.see("end")
        self.after(0, _append)

    def _update_progress(self, val_pct, status_text=None):
        def _apply():
            clamped = max(0, min(100, val_pct))
            self.progress_bar["value"] = clamped
            self.lbl_progress_pct.config(text=f"{int(clamped)}%")
            if status_text:
                self.lbl_progress_status.config(text=f"Status: {status_text}")
        self.after(0, _apply)

    def _load_history_view(self):
        """Memuat ulang tabel riwayat dari history.json."""
        self.hist_tree.delete(*self.hist_tree.get_children())
        histories = load_history()
        for idx, h in enumerate(histories):
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
                    f"File audio untuk '{h.get('rjid', '-')}' sudah tidak ditemukan di lokasi penyimpanan (mungkin telah dipindahkan atau dihapus).\n\nLokasi:\n{file_path}\n\nApakah Anda ingin menghapus catatan ini dari daftar riwayat?",
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

    def _start_download_thread(self):
        if self.is_downloading:
            return
        if not self.queue_items:
            show_dark_info(self, "Informasi", "Silakan tambahkan kode RJ ke antrean terlebih dahulu.")
            return

        self.is_downloading = True
        self.stop_requested = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _stop_downloads(self):
        self.stop_requested = True
        self._log("[!] Meminta penghentian download...")
        self.stop_btn.config(state="disabled")

    def _download_worker(self):
        download_dir = get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        total_items = len(self.queue_items)
        self._update_progress(0, f"Mempersiapkan {total_items} item...")

        for idx, item in enumerate(self.queue_items):
            if self.stop_requested:
                self._log("[!] Proses download dihentikan oleh pengguna.")
                self._update_progress(0, "Download dihentikan")
                break

            item_step = 100.0 / max(1, total_items)
            base_pct = idx * item_step

            if item["status"] == "Selesai":
                self._update_progress((idx + 1) * item_step, f"[{idx+1}/{total_items}] Selesai (Dilewati)")
                continue

            rjid = item["rjid"]
            title = item.get("title", "")

            # Nama File Output
            if self.opt_detailed_name.get() and title and title != "Memuat info..." and title != rjid:
                clean_title = sanitize_filename(title)
                final_output = os.path.join(download_dir, f"[{rjid}] {clean_title}.mp3")
            else:
                final_output = os.path.join(download_dir, f"{rjid}.mp3")

            # Cek jika file sudah ada
            if os.path.exists(final_output):
                self._log(f"[SKIP] File '{os.path.basename(final_output)}' sudah ada.")
                item["status"] = "Selesai"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Selesai (Ada)"))
                self._update_progress((idx + 1) * item_step, f"[{idx+1}/{total_items}] Selesai (Sudah Ada)")
                continue

            # Update status ke downloading
            item["status"] = "Downloading"
            self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Mengunduh..."))
            self.after(0, lambda i=idx: self.tree.selection_set(str(i)))

            cover_url = item.get("cover_url") or f"https://pic.weeabo0.xyz/{rjid}_img_main.jpg"
            temp_dir = os.path.join(".cache", "temp")
            os.makedirs(temp_dir, exist_ok=True)

            temp_cover = os.path.join(temp_dir, f"temp_{rjid}_cover.jpg")
            temp_files = [temp_cover]

            try:
                self._log(f"\n--- [{idx+1}/{total_items}] Memproses {rjid} ---")

                # 0. Deteksi Semua Track (Multi-track & Omake)
                self._update_progress(base_pct + item_step * 0.05, f"[{idx+1}/{total_items}] Memindai track audio...")
                self._log("[0/3] Mendeteksi jumlah track audio...")
                tracks = discover_all_audio_tracks(rjid, REFERER, USER_AGENT)
                track_names = [t["name"] for t in tracks]
                if len(tracks) > 1:
                    self._log(f"[i] Terdeteksi {len(tracks)} track ({', '.join(track_names)}). Semua akan digabung otomatis!")
                else:
                    self._log(f"[i] Terdeteksi 1 track audio.")

                # 1. Download & Standardize Cover to JPEG (agar terbaca Windows Explorer)
                self._update_progress(base_pct + item_step * 0.15, f"[{idx+1}/{total_items}] Mengunduh cover art...")
                self._log("[1/3] Mengunduh cover art...")
                req = urllib.request.Request(cover_url, headers={"Referer": REFERER, "User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    img_bytes = resp.read()
                with Image.open(io.BytesIO(img_bytes)) as pil_c:
                    pil_c.convert("RGB").save(temp_cover, "JPEG", quality=92)

                # 2. Download Semua Track Audio
                downloaded_track_files = []
                for t_idx, track_info in enumerate(tracks, start=1):
                    t_name = track_info["name"]
                    t_url = track_info["url"]
                    t_out_tmpl = os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.%(ext)s")
                    t_final_mp3 = os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp3")

                    temp_files.extend([
                        t_final_mp3,
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}_.mp3"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp4"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.temp.mp4"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.(ext)s.mp3"),
                    ])

                    track_prog = base_pct + item_step * (0.15 + 0.65 * (t_idx / len(tracks)))
                    self._update_progress(track_prog, f"[{idx+1}/{total_items}] Mengunduh {t_name} [{t_idx}/{len(tracks)}]...")
                    self._log(f"[2/3] Mengunduh {t_name} [{t_idx}/{len(tracks)}] (16 koneksi)...")
                    cmd_ytdlp = [
                        "yt-dlp",
                        "-N", "16",
                        "--downloader", "aria2c",
                        "--fixup", "never",
                        "--add-header", f"Referer: {REFERER}",
                        "--add-header", f"Origin: {REFERER}",
                        "--user-agent", USER_AGENT,
                        t_url,
                        "-x",
                        "--audio-format", "mp3",
                        "-o", t_out_tmpl,
                    ]
                    subprocess.run(
                        cmd_ytdlp,
                        check=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )

                    # Deteksi file audio yang berhasil dibuat
                    possible_files = [
                        t_final_mp3,
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}_.mp3"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.(ext)s.mp3"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp4"),
                    ]
                    actual_file = next((f for f in possible_files if os.path.exists(f)), None)

                    if not actual_file:
                        raise FileNotFoundError(f"File audio untuk {t_name} gagal diunduh.")
                    downloaded_track_files.append(actual_file)

                # 3. Embed Thumbnail & Full Metadata ke MP3 (serta Concatenate jika Multi-track)
                artist_val = item.get("cv", "")
                if not artist_val or artist_val == "-":
                    artist_val = "JapaneseASMR"
                album_val = item.get("circle", "")
                if not album_val or album_val == "-":
                    album_val = rjid
                genre_val = item.get("genre", "")
                if not genre_val or genre_val == "-":
                    genre_val = "ASMR"
                rating_val = item.get("age_rating", "-")

                self._update_progress(base_pct + item_step * 0.90, f"[{idx+1}/{total_items}] Menyematkan cover & metadata ID3...")

                if len(downloaded_track_files) > 1:
                    self._log(f"[3/3] Menggabungkan {len(tracks)} track & menyematkan metadata ID3...")
                    concat_list_file = os.path.join(temp_dir, f"concat_{rjid}.txt")
                    temp_files.append(concat_list_file)
                    with open(concat_list_file, "w", encoding="utf-8") as f_concat:
                        for tf in downloaded_track_files:
                            safe_p = os.path.abspath(tf).replace("\\", "/")
                            f_concat.write(f"file '{safe_p}'\n")

                    cmd_ffmpeg = [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel", "error",
                        "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", concat_list_file,
                        "-i", temp_cover,
                        "-map", "0:a",
                        "-map", "1:v",
                        "-c:a", "libmp3lame",
                        "-q:a", "2",
                        "-c:v", "mjpeg",
                        "-disposition:v:0", "attached_pic",
                        "-id3v2_version", "3",
                        "-metadata:s:v", "title=Album cover",
                        "-metadata:s:v", "comment=Cover (front)",
                        "-metadata", f"title={title if title else rjid}",
                        "-metadata", f"artist={artist_val}",
                        "-metadata", f"album={album_val}",
                        "-metadata", f"genre={genre_val}",
                        "-metadata", f"comment=Rating: {rating_val} | Tracks: {len(tracks)} Gabungan ({', '.join(track_names)})",
                        final_output,
                    ]
                else:
                    self._log("[3/3] Menyematkan cover art, Genre, Rating & metadata ID3...")
                    cmd_ffmpeg = [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel", "error",
                        "-y",
                        "-i", downloaded_track_files[0],
                        "-i", temp_cover,
                        "-map", "0:a",
                        "-map", "1:v",
                        "-c:a", "copy",
                        "-c:v", "mjpeg",
                        "-disposition:v:0", "attached_pic",
                        "-id3v2_version", "3",
                        "-metadata:s:v", "title=Album cover",
                        "-metadata:s:v", "comment=Cover (front)",
                        "-metadata", f"title={title if title else rjid}",
                        "-metadata", f"artist={artist_val}",
                        "-metadata", f"album={album_val}",
                        "-metadata", f"genre={genre_val}",
                        "-metadata", f"comment=Rating: {rating_val} | Circle: {album_val} | CV: {artist_val}",
                        final_output,
                    ]

                subprocess.run(
                    cmd_ffmpeg,
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )

                # Simpan ke riwayat unduhan & cache cover art
                add_to_history(
                    rjid=rjid,
                    title=title,
                    cv=item.get("cv", "-"),
                    circle=item.get("circle", "-"),
                    genre=item.get("genre", "-"),
                    age_rating=item.get("age_rating", "-"),
                    cover_url=cover_url,
                    output_path=final_output,
                    temp_cover_path=temp_cover,
                )

                item["status"] = "Selesai"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Selesai"))
                self.after(0, self._load_history_view)
                self._update_progress((idx + 1) * item_step, f"[{idx+1}/{total_items}] Selesai {rjid}")
                self._log(f"[✓] SUKSES: Tersimpan di {os.path.basename(final_output)}")

            except Exception as e:
                item["status"] = "Error"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Error"))
                self._log(f"[X] Gagal memproses {rjid}: {e}")

            finally:
                for tf in temp_files:
                    if os.path.exists(tf):
                        try:
                            os.remove(tf)
                        except OSError:
                            pass

        self.is_downloading = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._update_progress(100, "Semua proses selesai (100%)")
        self._log("\n--- Semua proses download dalam antrean selesai ---")
        self.after(0, lambda: show_dark_info(self, "Selesai", "Semua proses unduhan dalam antrean telah selesai!"))


if __name__ == "__main__":
    app = JapaneseASMRApp()
    app.mainloop()
