"""
Modul kompatibilitas SettingsDialog untuk JapaneseASMR Downloader.
Mengarahkan pemanggilan SettingsDialog ke Tab Pengaturan terintegrasi.
"""
from ui.tab_settings import SettingsTabMixin

class SettingsDialog:
    """Shim kompatibilitas: membuka tab pengaturan terintegrasi pada aplikasi utama."""
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
