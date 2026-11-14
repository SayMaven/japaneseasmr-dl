"""
GUI Module untuk JapaneseASMR Downloader.
Modul-modul antarmuka telah dipecah ke dalam package `ui/` agar lebih terorganisir dan mudah dirawat:
- `ui.app`: JapaneseASMRApp (Window utama & lifecycle)
- `ui.dialogs`: InAppModal & dark alert dialogs
- `ui.downloader`: DownloadWorkerMixin (worker thread & subprocess yt-dlp/aria2c)
- `ui.player_engine`: NativeMFPlayer (Windows Media Foundation native audio engine)
- `ui.settings_dialog`: SettingsDialog (dialog pengaturan lengkap)
- `ui.tab_queue`: QueueTabMixin (antarmuka tab antrean & metadata)
- `ui.tab_history`: HistoryTabMixin (antarmuka tab riwayat)
- `ui.tab_player`: PlayerTabMixin (antarmuka tab pemutar & chapters)
- `ui.constants`: Referer, User-Agent, Regex progress
"""
from ui import (
    JapaneseASMRApp,
    InAppModal,
    apply_dark_titlebar,
    ask_dark_yesno,
    show_dark_error,
    show_dark_info,
    show_dark_warning,
)
from ui.player_engine import NativeMFPlayer
from ui.settings_dialog import SettingsDialog

__all__ = [
    "JapaneseASMRApp",
    "InAppModal",
    "apply_dark_titlebar",
    "ask_dark_yesno",
    "show_dark_error",
    "show_dark_info",
    "show_dark_warning",
    "NativeMFPlayer",
    "SettingsDialog",
]

if __name__ == "__main__":
    app = JapaneseASMRApp()
    app.mainloop()
