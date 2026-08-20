import os
import sys

# Panggil Explicit AppUserModelID di baris PALING AWAL sebelum modul UI diinisialisasi
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SayMaven.JapaneseASMR.Downloader.App")
    except Exception:
        pass

from gui import JapaneseASMRApp


def main():
    """Entry point utama aplikasi (Desktop GUI)."""
    app = JapaneseASMRApp()
    app.mainloop()


if __name__ == "__main__":
    main()
