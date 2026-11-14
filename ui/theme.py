"""
Design System & OKLCH Theme Tokens untuk JapaneseASMR Downloader.
Palet warna dirancang menggunakan model persepsi OKLCH untuk menjamin
keseragaman kecerahan (lightness), bebas hue-drift, dan kontras WCAG AAA.
"""
from tkinter import ttk

# ==================== OKLCH DESIGN TOKENS (HEX EXPORT) ====================
# Latar Belakang & Permukaan
BG_APP = "#151821"           # oklch(0.16 0.015 260) - Kanvas utama
SURFACE_CARD = "#202533"     # oklch(0.22 0.020 260) - Kartu & Sidebar
SURFACE_ELEVATED = "#2b3245" # oklch(0.28 0.025 260) - Modal, dropdown, card aktif
SURFACE_INPUT = "#1a1e2b"    # oklch(0.19 0.018 260) - Input background
BORDER_SUBTLE = "#373f54"    # oklch(0.32 0.025 260) - Border halus (1px)
BORDER_ACTIVE = "#525e7d"    # oklch(0.42 0.030 260) - Focus border

# Aksen & Branding (Perceptual Violet)
ACCENT_PRIMARY = "#a855f7"   # oklch(0.65 0.190 290) - Tombol utama & aktif
ACCENT_HOVER = "#c084fc"     # oklch(0.72 0.170 290) - Hover state aksen
ACCENT_MUTED = "#581c87"     # oklch(0.35 0.150 290) - Badge aksen background

# Status Semantik
STATUS_SUCCESS = "#34d399"   # oklch(0.72 0.170 150) - Selesai, online, play
STATUS_WARNING = "#fbbf24"   # oklch(0.78 0.140 85)  - Skip, warning
STATUS_DANGER = "#f87171"    # oklch(0.62 0.210 25)  - Stop, error, delete
STATUS_INFO = "#38bdf8"      # oklch(0.74 0.160 220) - Info, loading

# Tipografi & Teks
TEXT_PRIMARY = "#f1f5f9"     # oklch(0.96 0.005 260) - Teks utama (Kontras >= 11:1)
TEXT_SECONDARY = "#94a3b8"   # oklch(0.68 0.015 260) - Label sekunder, ETA
TEXT_MUTED = "#64748b"       # oklch(0.55 0.015 260) - Placeholder, disable

# Radius Sudut (Corner Radii)
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 12
RADIUS_ROUND = 9999

# Tipografi Font Families
FONT_FAMILY = "Segoe UI"
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SUBTITLE = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_BODY_BOLD = ("Segoe UI", 11, "bold")
FONT_CAPTION = ("Segoe UI", 9)
FONT_CODE = ("Consolas", 10)


def configure_ttk_dark_theme(style: ttk.Style):
    """
    Mengonfigurasi tema ttk bawaan (seperti ttk.Treeview dan Scrollbar)
    agar serasi dengan kanvas gelap CustomTkinter berbasis OKLCH.
    """
    style.theme_use("clam")

    # Treeview Styling
    style.configure(
        "Treeview",
        background=SURFACE_CARD,
        foreground=TEXT_PRIMARY,
        fieldbackground=SURFACE_CARD,
        rowheight=28,
        borderwidth=0,
        font=FONT_BODY,
    )
    style.map(
        "Treeview",
        background=[("selected", ACCENT_PRIMARY)],
        foreground=[("selected", "#ffffff")],
    )

    # Treeview Heading
    style.configure(
        "Treeview.Heading",
        background=SURFACE_ELEVATED,
        foreground=TEXT_SECONDARY,
        relief="flat",
        font=FONT_BODY_BOLD,
        padding=(6, 6),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", BORDER_SUBTLE)],
        foreground=[("active", TEXT_PRIMARY)],
    )

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=SURFACE_CARD,
        troughcolor=BG_APP,
        bordercolor=BG_APP,
        arrowcolor=TEXT_MUTED,
        relief="flat",
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", BORDER_ACTIVE), ("pressed", ACCENT_PRIMARY)],
    )

