"""Cross-platform screen-size helper."""

import sys


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the primary screen in pixels."""
    r = get_screen_rect()
    return r[2] - r[0], r[3] - r[1]


def get_screen_rect() -> tuple[int, int, int, int]:
    """Return (left, top, right, bottom) of the primary screen in virtual desktop coords."""
    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes as wintypes

            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", ctypes.c_ulong),
                ]

            # MonitorFromPoint(0,0) with MONITOR_DEFAULTTOPRIMARY=1
            pt = wintypes.POINT(0, 0)
            hmon = user32.MonitorFromPoint(pt, 1)
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(hmon, ctypes.byref(info))
            r = info.rcMonitor
            return (r.left, r.top, r.right, r.bottom)
        except Exception:
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            return (0, 0, w, h)

    if sys.platform == "darwin":
        try:
            from AppKit import NSScreen  # type: ignore
            frame = NSScreen.mainScreen().frame()
            w, h = int(frame.size.width), int(frame.size.height)
            return (0, 0, w, h)
        except ImportError:
            pass

    # Fallback: tkinter
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return (0, 0, w, h)
    except Exception:
        return (0, 0, 1920, 1080)
