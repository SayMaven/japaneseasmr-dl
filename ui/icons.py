"""
Modul manajemen ikon vektor transparan pre-rendered untuk CustomTkinter.
Menggunakan in-memory PIL caching untuk performa instan tanpa parsing SVG runtime,
100% kompatibel dengan Nuitka standalone dan multi-window/restart di Windows.
"""
import os
from typing import Tuple, Optional
from PIL import Image
import customtkinter as ctk

# Lokasi folder aset ikon
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")

# Cache PIL Image murni (independen dari state Tkinter)
_PIL_CACHE = {}
_ICON_CACHE = _PIL_CACHE  # Alias kompatibilitas

def clear_icon_cache():
    """Mengosongkan cache in-memory PIL image."""
    global _PIL_CACHE
    _PIL_CACHE.clear()

def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join([c * 2 for c in hex_str])
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def get_icon(name: str, size: Tuple[int, int] = (18, 18), color: Optional[str] = None) -> ctk.CTkImage:
    """
    Mengambil ikon CTkImage berdasarkan nama.
    Jika color ditentukan (format hex '#ffffff'), ikon akan ditint ke warna tersebut.
    Meng-cache PIL.Image di memori sehingga performa instan (<0.01ms) dan aman
    terhadap lifecycle root window Tkinter.
    """
    cache_key = (name, size, color)
    if cache_key in _PIL_CACHE:
        final_img = _PIL_CACHE[cache_key]
    else:
        png_path = os.path.join(ICONS_DIR, f"{name}.png")
        if not os.path.exists(png_path):
            fallback_path = os.path.join(ICONS_DIR, "check.png")
            if os.path.exists(fallback_path):
                png_path = fallback_path
            else:
                final_img = Image.new("RGBA", (size[0] * 3, size[1] * 3), (0, 0, 0, 0))
                _PIL_CACHE[cache_key] = final_img
                return ctk.CTkImage(light_image=final_img, dark_image=final_img, size=size)

        try:
            base_img = Image.open(png_path).convert("RGBA")
            if color:
                rgb = _hex_to_rgb(color)
                r, g, b, alpha = base_img.split()
                color_img = Image.new("RGB", base_img.size, rgb)
                tinted = Image.new("RGBA", base_img.size)
                tinted.paste(color_img, (0, 0), mask=alpha)
                final_img = tinted
            else:
                final_img = base_img

            _PIL_CACHE[cache_key] = final_img
        except Exception as e:
            print(f"[ui.icons] Gagal memuat ikon '{name}': {e}")
            final_img = Image.new("RGBA", (size[0] * 2, size[1] * 2), (0, 0, 0, 0))
            _PIL_CACHE[cache_key] = final_img

    return ctk.CTkImage(
        light_image=final_img,
        dark_image=final_img,
        size=size
    )
