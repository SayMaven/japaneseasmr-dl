"""
GUI package compatibility entry point for JapaneseASMR Downloader.
Interface modules are organized within the `ui/` package:
- `ui.app`: JapaneseASMRApp (Main window and application lifecycle)
- `ui.dialogs`: InAppModal and dark-themed alert dialogs
- `ui.downloader`: DownloadWorkerMixin (worker thread and yt-dlp/aria2c subprocesses)
- `ui.player_engine`: NativeMFPlayer (Windows Media Foundation native audio engine)
- `ui.settings_dialog`: SettingsDialog (integrated settings tab shim)
- `ui.tab_queue`: QueueTabMixin (download queue and metadata preview interface)
- `ui.tab_history`: HistoryTabMixin (download history interface)
- `ui.tab_player`: PlayerTabMixin (integrated audio player and chapters interface)
- `ui.constants`: HTTP headers and regex patterns
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
