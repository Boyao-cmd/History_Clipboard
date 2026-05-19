"""Windows auto-start management via registry."""
import os
import sys
import winreg


APP_NAME = "HistoryClipboard"


def get_startup_path():
    """Get the path that would be used for auto-start."""
    # When running as script
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def _get_run_key():
    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
    )


def enable():
    """Add to Windows startup registry."""
    try:
        key = _get_run_key()
        # Use pythonw.exe to avoid console window
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        script = get_startup_path()
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                          f'"{pythonw}" "{script}"')
        winreg.CloseKey(key)
        print("[AutoStart] Enabled", flush=True)
        return True
    except Exception as e:
        print(f"[AutoStart] Enable failed: {e}", flush=True)
        return False


def disable():
    """Remove from Windows startup registry."""
    try:
        key = _get_run_key()
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[AutoStart] Disable failed: {e}", flush=True)
        return False


def is_enabled():
    """Check if auto-start is currently enabled."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False
