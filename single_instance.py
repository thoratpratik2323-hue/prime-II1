"""
Cross-process single instance mutex for Prime AI on Windows.
Prevents multiple instances of Prime AI from running simultaneously,
which causes audio echo, dual microphone capture, and duplicate TTS voices.
"""
from __future__ import annotations

import sys

_MUTEX_HANDLE = None


def acquire_single_instance(name: str = "Global\\PrimeAI_SingleInstance_Mutex") -> bool:
    """
    Acquire a system-wide named mutex on Windows.
    Returns True if this is the ONLY running instance.
    Returns False if another Prime AI process already holds the mutex.
    """
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True

    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, name)
        last_error = kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if last_error == ERROR_ALREADY_EXISTS:
            if mutex:
                kernel32.CloseHandle(mutex)
            return False
        _MUTEX_HANDLE = mutex
        return True
    except Exception:
        return True


def release_single_instance() -> None:
    """Explicitly release the mutex handle."""
    global _MUTEX_HANDLE
    if _MUTEX_HANDLE and sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_MUTEX_HANDLE)
        except Exception:
            pass
        _MUTEX_HANDLE = None
