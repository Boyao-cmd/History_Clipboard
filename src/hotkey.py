"""Global hotkey registration for Windows (Ctrl+Shift+V)."""
import ctypes
from ctypes import wintypes

# Windows API constants
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_V = 0x56
WM_HOTKEY = 0x0312

# Keep references to prevent garbage collection
_hotkey_ids = {}
_callback = None


def register_hotkey(hwnd, callback):
    """
    Register Ctrl+Shift+V as a global hotkey.
    hwnd should be the native window handle (int(win.winId())).
    callback is called when the hotkey is pressed.
    """
    global _callback
    _callback = callback

    # Register hotkey with Windows
    user32 = ctypes.windll.user32
    hotkey_id = 1

    result = user32.RegisterHotKey(
        wintypes.HWND(hwnd),
        hotkey_id,
        MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT,
        VK_V
    )

    if result:
        _hotkey_ids[hotkey_id] = True
        print("[Hotkey] Ctrl+Shift+V registered", flush=True)
    else:
        err = ctypes.get_last_error()
        print(f"[Hotkey] Failed to register (error {err})", flush=True)

    return bool(result)


def unregister_hotkey(hwnd):
    """Unregister all hotkeys for the given window."""
    user32 = ctypes.windll.user32
    for hotkey_id in list(_hotkey_ids.keys()):
        user32.UnregisterHotKey(wintypes.HWND(hwnd), hotkey_id)
        del _hotkey_ids[hotkey_id]
