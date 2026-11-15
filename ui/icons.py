"""
Vector icon management module with pre-rendered transparent assets for CustomTkinter.
Uses in-memory PIL caching for zero-overhead performance without runtime SVG parsing,
fully compatible with Nuitka standalone bundles and multi-window/restart lifecycles on Windows.
"""
import os
from typing import Tuple, Optional
from PIL import Image
import customtkinter as ctk

# Base directory paths for icon assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")

# In-memory pure PIL image cache (decoupled from Tkinter widget state)
_PIL_CACHE = {}
_ICON_CACHE = _PIL_CACHE  # Compatibility alias

def clear_icon_cache():
    """Clear the in-memory PIL image cache."""
    global _PIL_CACHE
    _PIL_CACHE.clear()

def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join([c * 2 for c in hex_str])
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def get_icon(name: str, size: Tuple[int, int] = (18, 18), color: Optional[str] = None) -> ctk.CTkImage:
    """
    Retrieve a cached CTkImage icon by name.
    If color is specified (hex format '#ffffff'), the icon is tinted accordingly.
    Caches the underlying PIL.Image in memory for instant retrieval (<0.01ms)
    independent of Tkinter root window lifecycles.
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
            print(f"[ui.icons] Failed to load icon '{name}': {e}")
            final_img = Image.new("RGBA", (size[0] * 2, size[1] * 2), (0, 0, 0, 0))
            _PIL_CACHE[cache_key] = final_img

    return ctk.CTkImage(
        light_image=final_img,
        dark_image=final_img,
        size=size
    )
