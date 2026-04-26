import sys
import os

def is_windows():
    return sys.platform == "win32"

if is_windows():
    import winreg

def set_autostart(enabled=True):
    if not is_windows():
        return False

    app_name = "WPMonitor"

    # Get path to current executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_path = sys.executable
    else:
        # Running as script
        app_path = os.path.abspath(sys.argv[0])
        # If running as script, we might want to include the python interpreter
        # but for startup it's better if it's the .exe

    # Add --minimized flag to start hidden
    cmd = f'"{app_path}" --minimized'

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass # Already deleted
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error setting registry: {e}")
        return False
