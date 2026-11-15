"""
SettingsDialog compatibility module for JapaneseASMR Downloader.
Redirects external SettingsDialog calls to the integrated Settings tab.
"""

class SettingsDialog:
    """Compatibility shim: navigates to the integrated settings tab in the main application."""
    def __init__(self, parent):
        self.parent = parent
        if hasattr(parent, "_select_page"):
            parent._select_page("settings")
        elif hasattr(parent, "open_settings_dialog"):
            parent.open_settings_dialog()

    def winfo_exists(self):
        return False

    def lift(self):
        pass

    def focus_force(self):
        pass

    def destroy(self):
        pass
