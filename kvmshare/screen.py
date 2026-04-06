"""Cross-platform screen-size helper."""

import sys


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the primary screen in pixels."""
    if sys.platform == "win32":
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    if sys.platform == "darwin":
        try:
            from AppKit import NSScreen  # type: ignore
            frame = NSScreen.mainScreen().frame()
            return int(frame.size.width), int(frame.size.height)
        except ImportError:
            pass

    # Fallback: tkinter (works on both platforms if above fails)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        return 1920, 1080  # last resort default
