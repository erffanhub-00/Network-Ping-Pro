"""Terminal colours (ANSI), with Windows support and a global off switch."""

import platform


class Color:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

    @classmethod
    def enable_windows_ansi(cls):
        """Enable ANSI on Windows 10+ without clobbering other console flags."""
        if platform.system().lower() != 'windows':
            return
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                raise OSError("GetConsoleMode failed")
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            cls.disable()

    @classmethod
    def disable(cls):
        for attr in dir(cls):
            if attr.isupper() and isinstance(getattr(cls, attr), str):
                setattr(cls, attr, '')
