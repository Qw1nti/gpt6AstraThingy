"""Map physical capture rectangles to Qt displays by Windows device identity."""
from __future__ import annotations

import ctypes
from ctypes import wintypes


def display_devices() -> dict[tuple[int, int, int, int], str]:
    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                    ("szDevice", wintypes.WCHAR * 32)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                      ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.EnumDisplayMonitors.argtypes = (wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                         callback_type, wintypes.LPARAM)
    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    devices, errors = {}, []

    def collect(handle, dc, rect, data):
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if not user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            errors.append(ctypes.get_last_error())
            return False
        r = info.rcMonitor
        devices[(r.left, r.top, r.right-r.left, r.bottom-r.top)] = info.szDevice
        return True

    if not user32.EnumDisplayMonitors(None, None, callback_type(collect), 0) or errors:
        raise ctypes.WinError(errors[0] if errors else ctypes.get_last_error())
    return devices


def match_screens(monitors: dict[int, dict], screens, devices) -> dict[int, object]:
    def identity(name):
        return name.upper().removeprefix("\\\\.\\")
    by_name = {identity(screen.name()): screen for screen in screens}
    matched = {}
    for index, monitor in monitors.items():
        rect = tuple(monitor[key] for key in ("left", "top", "width", "height"))
        name = devices.get(rect)
        screen = by_name.get(identity(name)) if name else None
        if screen is None or screen in matched.values():
            raise RuntimeError("Display layout changed or could not be mapped. Restart protection after checking Windows display settings.")
        matched[index] = screen
    return matched
