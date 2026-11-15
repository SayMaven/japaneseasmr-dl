"""
Design System, Tokyo Night Theme Tokens, and Modern Typography for JapaneseASMR Downloader.
Color palette designed using perceptual OKLCH color modeling and Tokyo Night Depth Architecture
with 4 elevation layers, 2 functional accents (Violet and Sky), and a disciplined spacing/corner scale.
"""
from tkinter import ttk
import tkinter.font as tkfont

# ==================== COLOR PALETTE (TOKYO NIGHT & OKLCH) ====================
# Visual Depth Architecture Layers
BG_SIDEBAR = "#0b0e14"         # Layer 0: Ultra-deep navy - Flush sidebar background
BG_VIEWPORT = "#131722"        # Layer 1: Charcoal navy - Main viewport canvas
BG_APP = BG_VIEWPORT           # Compatibility alias
SURFACE_CARD = "#1e2333"       # Layer 2: Card container surface
SURFACE_ELEVATED = "#282f44"   # Layer 3: Modal dialogs, dropdowns, hovered cards
SURFACE_INPUT = "#171b26"      # Input text field background

# Border Tokens
BORDER_SUBTLE = "#282f44"      # Container boundary border (1px)
BORDER_ACTIVE = "#38bdf8"      # Active input focus / highlight border
BORDER_MUTED = "#1e2538"       # Subtle divider border

# Functional Accent Tokens
ACCENT_PRIMARY = "#8b5cf6"        # Electric Violet (Primary buttons, active tabs, progress bars)
ACCENT_PRIMARY_HOVER = "#7c3aed"  # Primary hover state
ACCENT_HOVER = ACCENT_PRIMARY_HOVER  # Compatibility alias
ACCENT_MUTED = "#4c1d95"          # Muted violet badge background

ACCENT_SECONDARY = "#38bdf8"      # Sky Blue (Playback status, active pill indicators)
ACCENT_SECONDARY_HOVER = "#0ea5e9"
STATUS_INFO = ACCENT_SECONDARY    # Compatibility alias

# Semantic Status Tokens
STATUS_SUCCESS = "#10b981"     # Emerald Green (Download completed, save successful)
STATUS_WARNING = "#f59e0b"     # Amber (Warning, skip action)
STATUS_DANGER = "#f43f5e"      # Rose / Danger (Delete, stop playback)

# Typography Text Colors
TEXT_PRIMARY = "#f8fafc"       # Snow white high-contrast text (Contrast >= 12:1)
TEXT_SECONDARY = "#cbd5e1"     # Slate 300 - Secondary labels, metadata
TEXT_MUTED = "#94a3b8"         # Slate 400 - Placeholders, inactive status
TEXT_DIM = "#64748b"           # Slate 500 - Inactive border labels, disabled controls

# ==================== CORNER RADII SCALE ====================
RADIUS_SIDEBAR = 0             # Flush edge-to-edge docking
RADIUS_CARD = 10               # Card containers and major content frames
RADIUS_BUTTON = 8              # Action buttons and text inputs
RADIUS_INPUT = 8               # Input entries and comboboxes
RADIUS_PILL = 9999             # Circular pill badges and playback controls

# Compatibility aliases
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 12
RADIUS_ROUND = 9999

# ==================== DISCIPLINED SPACING SCALE ====================
SPACE_XS = 4                   # Micro: gap between icon and text
SPACE_SM = 8                   # Tight: internal item padding
SPACE_MD = 12                  # Standard: vertical spacing between cards
SPACE_LG = 16                  # Relaxed: margins between button groups
SPACE_XL = 24                  # Section: main page padding

# ==================== MODERN TYPOGRAPHY & FALLBACK SYSTEM ====================
_RESOLVED_FONTS = {}

def get_system_font_family(is_display: bool = False, is_mono: bool = False) -> str:
    """
    Detect and resolve installed system font families with intelligent fallback:
    Windows: Yu Gothic UI -> Segoe UI Variable -> Segoe UI -> sans-serif.
    Yu Gothic UI is prioritized on Windows so Japanese (Kanji/Kana) and Latin
    characters share matching, balanced, elegant stroke weights (preventing bold Meiryo fallback).
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
        # Prioritize Yu Gothic UI on Windows if available so Japanese (Kanji/Kana)
        # and Latin characters render with balanced normal stroke weights without heavy Meiryo fallback.
        if "Yu Gothic UI" in available:
            font_name = "Yu Gothic UI"
        elif is_display and "Segoe UI Variable Display" in available:
            font_name = "Segoe UI Variable Display"
        elif not is_display and "Segoe UI Variable Text" in available:
            font_name = "Segoe UI Variable Text"
        elif "Inter" in available:
            font_name = "Inter"
        elif "Segoe UI" in available:
            font_name = "Segoe UI"
        elif "Meiryo UI" in available:
            font_name = "Meiryo UI"
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
    Configure native ttk widget themes (Treeview, Scrollbar)
    to seamlessly match the Tokyo Night dark aesthetic.
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
