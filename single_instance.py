"""
Cross-process single instance mutex for Prime AI on Windows.
Prevents multiple instances of Prime AI from running simultaneously,
which causes audio echo, dual microphone capture, and duplicate TTS voices.
"""
from __future__ import annotations

import os
import sys
import time

_MUTEX_HANDLE = None
PID_FILE = os.path.join(os.path.dirname(__file__), "memory", "prime_process.pid")


def get_running_instance_pid() -> int | None:
    """Return the PID of the currently active Prime AI process if alive."""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid_str = f.read().strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    import psutil
                    if psutil.pid_exists(pid):
                        return pid
    except Exception:
        pass
    return None


def terminate_existing_instance() -> bool:
    """Terminates any previously running Prime AI instance to release ports, mutex, and mic."""
    pid = get_running_instance_pid()
    if pid and pid != os.getpid():
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=2.0)
            time.sleep(0.5)
            return True
        except Exception:
            try:
                os.kill(pid, 9)
                time.sleep(0.5)
                return True
            except Exception:
                pass
    return False


def acquire_single_instance(name: str = "Global\\PrimeAI_SingleInstance_Mutex", force: bool = False) -> bool:
    """
    Acquire a system-wide named mutex on Windows.
    Returns True if this is the ONLY running instance.
    Returns False if another Prime AI process already holds the mutex.
    If force=True, attempts to terminate the existing instance first.
    """
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True

    if force:
        terminate_existing_instance()

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

        # Record our PID
        try:
            os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
            with open(PID_FILE, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass

        return True
    except Exception:
        return True


def release_single_instance() -> None:
    """Explicitly release the mutex handle and clear PID lockfile."""
    global _MUTEX_HANDLE
    if _MUTEX_HANDLE and sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_MUTEX_HANDLE)
        except Exception:
            pass
        _MUTEX_HANDLE = None

    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass


def prevent_system_sleep(enable: bool = True) -> bool:
    """
    Prevents Windows from entering sleep or suspending background processes
    while Prime AI is running. Keeps the CPU, network, audio, and background tasks
    awake 24/7 without forcing the monitor to stay lit.
    """
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_AWAYMODE_REQUIRED = 0x00000040
        if enable:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            )
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        return True
    except Exception:
        return False
