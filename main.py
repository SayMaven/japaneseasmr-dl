import os
import sys

# Set Explicit AppUserModelID as early as possible before any UI modules initialize
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SayMaven.JapaneseASMR.Downloader.App")
    except Exception:
        pass

from ui import JapaneseASMRApp


def main():
    """Main application entry point for the desktop GUI."""
    app = JapaneseASMRApp()
    app.mainloop()


if __name__ == "__main__":
    main()
