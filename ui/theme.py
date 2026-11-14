"""
Design System, Tokyo Night Theme Tokens, & Tipografi Modern untuk JapaneseASMR Downloader.
Palet warna dirancang menggunakan model persepsi OKLCH & Tokyo Night Depth Architecture
dengan 4 level ketinggian (elevation layers), 2 aksen terukur (Violet & Sky), dan skala sudut/spacing disiplin.
"""
from tkinter import ttk
import tkinter.font as tkfont

# ==================== PALET WARNA (TOKYO NIGHT & OKLCH) ====================
# Layer Kedalaman Visual (Depth Architecture)
BG_SIDEBAR = "#0b0e14"         # Layer 0: Ultra deep navy - Sidebar navigasi menempel rata
BG_VIEWPORT = "#131722"        # Layer 1: Charcoal navy - Kanvas utama konten
BG_APP = BG_VIEWPORT           # Alias kompatibilitas
SURFACE_CARD = "#1e2333"       # Layer 2: Surface card kontainer konten
SURFACE_ELEVATED = "#282f44"   # Layer 3: Modal, dropdown, card hover/active
SURFACE_INPUT = "#171b26"      # Background input text field

# Garis Batas (Borders)
BORDER_SUBTLE = "#282f44"      # Border kontainer kartu (1px)
BORDER_ACTIVE = "#38bdf8"      # Border fokus input / active highlight
BORDER_MUTED = "#1e2538"       # Pembatas halus

# 2 Aksen Fungsional (Anti-Rainbow)
ACCENT_PRIMARY = "#8b5cf6"        # Electric Violet (Tombol utama, tab aktif, progress)
ACCENT_PRIMARY_HOVER = "#7c3aed"  # Hover state violet
ACCENT_HOVER = ACCENT_PRIMARY_HOVER # Alias kompatibilitas
ACCENT_MUTED = "#4c1d95"          # Dark violet badge background

ACCENT_SECONDARY = "#38bdf8"      # Sky Blue (Status pemutaran aktif, pill info)
ACCENT_SECONDARY_HOVER = "#0ea5e9"
STATUS_INFO = ACCENT_SECONDARY    # Alias kompatibilitas

# Status Semantik
STATUS_SUCCESS = "#10b981"     # Emerald Green (Selesai unduh, simpan sukses)
STATUS_WARNING = "#f59e0b"     # Amber (Peringatan, skip track)
STATUS_DANGER = "#f43f5e"      # Rose / Danger (Hapus, stop playback)

# Tipografi & Teks
TEXT_PRIMARY = "#f8fafc"       # Putih salju kontras tinggi (Kontras >= 12:1)
TEXT_SECONDARY = "#cbd5e1"     # Slate 300 - Label sekunder, metadata
TEXT_MUTED = "#94a3b8"         # Slate 400 - Placeholder, status pasif
TEXT_DIM = "#64748b"           # Slate 500 - Border label / disable

# ==================== SKALA SUDUT (CORNER RADII) ====================
RADIUS_SIDEBAR = 0             # Rata menempel ke sisi jendela
RADIUS_CARD = 10               # Kontainer kartu & frame konten
RADIUS_BUTTON = 8              # Tombol aksi & input field
RADIUS_INPUT = 8               # Input entry & combobox
RADIUS_PILL = 9999             # Status pill & tombol playback bulat

# Alias kompatibilitas
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 12
RADIUS_ROUND = 9999

# ==================== SKALA SPACING DISIPLIN ====================
SPACE_XS = 4                   # Micro: gap ikon & teks
SPACE_SM = 8                   # Tight: padding internal item
SPACE_MD = 12                  # Standard: jarak antar kartu vertikal
SPACE_LG = 16                  # Relaxed: margin antar grup tombol
SPACE_XL = 24                  # Section: padding halaman utama

# ==================== TIPOGRAFI MODERN DENGAN FALLBACK TERUJI ====================
_RESOLVED_FONTS = {}

def get_system_font_family(is_display: bool = False, is_mono: bool = False) -> str:
    """
    Mendeteksi keluarga font yang terpasang di sistem operasi dengan fallback cerdas:
    Windows 11 -> Segoe UI Variable Display/Text
    Windows 10 / Fallback -> Inter -> Segoe UI -> Yu Gothic UI -> sans-serif
    """
    key = (is_display, is_mono)
    if key in _RESOLVED_FONTS:
        return _RESOLVED_FONTS[key]

    if is_mono:
        try:
            available = set(tkfont.families())
            for candidate in ["Cascadia Code", "Consolas", "Courier New"]:
                if candidate in available:
                    _RESOLVED_FONTS[key] = candidate
                    return candidate
        except Exception:
            pass
        _RESOLVED_FONTS[key] = "Consolas"
        return "Consolas"

    try:
        available = set(tkfont.families())
        if is_display and "Segoe UI Variable Display" in available:
            font_name = "Segoe UI Variable Display"
        elif not is_display and "Segoe UI Variable Text" in available:
            font_name = "Segoe UI Variable Text"
        elif "Inter" in available:
            font_name = "Inter"
        elif "Segoe UI" in available:
            font_name = "Segoe UI"
        elif "Yu Gothic UI" in available:
            font_name = "Yu Gothic UI"
        else:
            font_name = "Arial"
    except Exception:
        font_name = "Segoe UI"

    _RESOLVED_FONTS[key] = font_name
    return font_name


FONT_FAMILY = get_system_font_family(is_display=False)
FONT_DISPLAY_FAMILY = get_system_font_family(is_display=True)
FONT_MONO_FAMILY = get_system_font_family(is_mono=True)

# Predefined Modern Font Tuples
FONT_TITLE = (FONT_DISPLAY_FAMILY, 18, "bold")
FONT_SECTION = (FONT_DISPLAY_FAMILY, 14, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 12, "bold")
FONT_BODY = (FONT_FAMILY, 11, "normal")
FONT_BODY_BOLD = (FONT_FAMILY, 11, "bold")
FONT_CAPTION = (FONT_FAMILY, 10, "normal")
FONT_CODE = (FONT_MONO_FAMILY, 10, "normal")


def configure_ttk_dark_theme(style: ttk.Style):
    """
    Mengonfigurasi tema ttk bawaan (seperti ttk.Treeview dan Scrollbar)
    agar serasi dengan kanvas gelap Tokyo Night.
    """
    style.theme_use("clam")

    # Treeview Styling
    style.configure(
        "Treeview",
        background=SURFACE_CARD,
        foreground=TEXT_PRIMARY,
        fieldbackground=SURFACE_CARD,
        rowheight=32,
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
        padding=(8, 8),
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
        troughcolor=BG_VIEWPORT,
        bordercolor=BG_VIEWPORT,
        arrowcolor=TEXT_MUTED,
        relief="flat",
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", BORDER_ACTIVE), ("pressed", ACCENT_PRIMARY)],
    )
