"""
GUI & Desktop Automation Tools for Prime AI.
Enables full OS-level control: mouse clicks, movement, scrolling, typing text,
hotkeys, window enumeration, and window focusing.
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Optional

from .registry import ToolError, register


def _is_windows() -> bool:
    return sys.platform.startswith("win") or os.name == "nt"


@register("mouseClick")
def mouse_click(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Click at specific (x, y) screen coordinates or current cursor location.
    Args:
        x (int, optional): X coordinate on screen
        y (int, optional): Y coordinate on screen
        button (str, optional): 'left', 'right', or 'middle'. Default 'left'.
        clicks (int, optional): 1 for single click, 2 for double click. Default 1.
    """
    args = args or {}
    x = args.get("x")
    y = args.get("y")
    button = str(args.get("button", "left")).lower()
    clicks = int(args.get("clicks", 1))

    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y), duration=0.15)

        if clicks == 2:
            pyautogui.doubleClick(button=button)
        else:
            pyautogui.click(button=button)

        cur_x, cur_y = pyautogui.position()
        return {
            "result": f"Successfully performed {button} click ({clicks}x) at ({cur_x}, {cur_y}).",
            "x": cur_x,
            "y": cur_y,
            "button": button,
        }
    except Exception as e:
        raise ToolError(f"Mouse click failed: {e}") from e


@register("mouseMove")
def mouse_move(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Move the mouse cursor smoothly to (x, y) coordinates.
    Args:
        x (int): Target X coordinate
        y (int): Target Y coordinate
        duration (float, optional): Move animation duration in seconds. Default 0.2.
    """
    args = args or {}
    x = args.get("x")
    y = args.get("y")
    if x is None or y is None:
        raise ToolError("Both 'x' and 'y' coordinates are required for mouseMove.")

    duration = float(args.get("duration", 0.2))

    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.moveTo(int(x), int(y), duration=duration)
        cur_x, cur_y = pyautogui.position()
        return {"result": f"Mouse moved to ({cur_x}, {cur_y}).", "x": cur_x, "y": cur_y}
    except Exception as e:
        raise ToolError(f"Mouse move failed: {e}") from e


@register("mouseScroll")
def mouse_scroll(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Scroll the mouse wheel up or down at current position.
    Args:
        amount (int): Positive to scroll up, negative to scroll down (e.g. 500 or -500).
    """
    args = args or {}
    amount = int(args.get("amount", -300))

    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.scroll(amount)
        direction = "up" if amount > 0 else "down"
        return {"result": f"Scrolled mouse wheel {direction} by {abs(amount)} units."}
    except Exception as e:
        raise ToolError(f"Mouse scroll failed: {e}") from e


@register("typeText")
def type_text(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Type text into the currently active window or input field.
    Handles Unicode, Hindi, symbols, and multilingual text cleanly via clipboard paste.
    Args:
        text (str): The text to type or paste into the active window.
        press_enter (bool, optional): Whether to press Enter after typing. Default False.
    """
    args = args or {}
    text = args.get("text", "")
    if not text:
        raise ToolError("'text' parameter is required for typeText.")

    press_enter = bool(args.get("press_enter", False))

    try:
        import pyautogui
        import pyperclip

        pyautogui.FAILSAFE = False

        # If plain ASCII without special characters, type directly; otherwise use clipboard paste
        is_ascii = all(ord(c) < 128 and c != '\n' for c in text)
        if is_ascii and len(text) < 100:
            pyautogui.write(text, interval=0.01)
        else:
            old_clip = ""
            try:
                old_clip = pyperclip.paste()
            except Exception:
                pass

            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.05)

            # Restore original clipboard
            if old_clip:
                try:
                    pyperclip.copy(old_clip)
                except Exception:
                    pass

        if press_enter:
            time.sleep(0.05)
            pyautogui.press("enter")

        return {
            "result": f"Typed {len(text)} characters into active window{' and pressed Enter' if press_enter else ''}.",
            "text": text[:50] + ("..." if len(text) > 50 else "")
        }
    except Exception as e:
        raise ToolError(f"Typing text failed: {e}") from e


@register("pressHotkey")
def press_hotkey(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Press keyboard shortcut keys or combinations (e.g. ['ctrl', 'c'], ['alt', 'tab'], ['win', 'd'], 'enter', 'esc').
    Args:
        keys (list[str] | str): Key or list of keys to press together (e.g. ['ctrl', 'v'] or 'ctrl+v' or 'enter').
    """
    args = args or {}
    raw_keys = args.get("keys", [])

    if isinstance(raw_keys, str):
        if "+" in raw_keys:
            key_list = [k.strip().lower() for k in raw_keys.split("+")]
        else:
            key_list = [raw_keys.strip().lower()]
    elif isinstance(raw_keys, list):
        key_list = [str(k).strip().lower() for k in raw_keys]
    else:
        raise ToolError("'keys' must be a list of strings or '+'-separated string.")

    if not key_list:
        raise ToolError("No keys specified to press.")

    # Normalize key names
    key_map = {
        "ctrl": "ctrl",
        "control": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "win": "win",
        "windows": "win",
        "super": "win",
        "cmd": "win",
        "enter": "enter",
        "return": "enter",
        "esc": "esc",
        "escape": "esc",
        "tab": "tab",
        "backspace": "backspace",
        "delete": "delete",
        "space": "space",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
    }
    normalized = [key_map.get(k, k) for k in key_list]

    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        if len(normalized) == 1:
            pyautogui.press(normalized[0])
        else:
            pyautogui.hotkey(*normalized)

        return {"result": f"Pressed hotkey: {' + '.join(normalized)}"}
    except Exception as e:
        raise ToolError(f"Pressing hotkey failed: {e}") from e


@register("getCursorPosition")
def get_cursor_position(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Get current mouse cursor position and screen dimensions."""
    try:
        import pyautogui
        x, y = pyautogui.position()
        w, h = pyautogui.size()
        return {
            "result": f"Mouse cursor at ({x}, {y}) on screen resolution {w}x{h}.",
            "x": x,
            "y": y,
            "screen_width": w,
            "screen_height": h,
        }
    except Exception as e:
        raise ToolError(f"Could not get cursor position: {e}") from e


@register("listOpenWindows")
def list_open_windows(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    List all currently open and visible application windows on the desktop.
    """
    windows = []
    try:
        import win32gui
        import win32process
        import psutil

        def enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    pname = ""
                    try:
                        pname = psutil.Process(pid).name()
                    except Exception:
                        pass
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 50 and h > 50:
                        windows.append({
                            "title": title,
                            "process": pname,
                            "pid": pid,
                            "hwnd": hwnd,
                            "bounds": {"x": rect[0], "y": rect[1], "width": w, "height": h}
                        })
            return True

        win32gui.EnumWindows(enum_cb, None)
    except Exception as e:
        # Fallback using powershell
        try:
            import subprocess
            cmd = 'powershell "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object Id, ProcessName, MainWindowTitle"'
            out = subprocess.check_output(cmd, shell=True, text=True, timeout=5)
            return {"result": "Open Windows:\n" + out.strip(), "windows": []}
        except Exception:
            raise ToolError(f"Failed to list open windows: {e}") from e

    summary_lines = [f"• [{w['process']}] \"{w['title']}\" (PID {w['pid']})" for w in windows[:20]]
    return {
        "result": f"Found {len(windows)} open windows:\n" + "\n".join(summary_lines),
        "windows": windows[:25],
        "count": len(windows),
    }


@register("focusWindow")
def focus_window(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Bring a specific application or window to the foreground by matching its title or app name.
    Args:
        query (str): Partial title or application name to search for (e.g. 'Chrome', 'Visual Studio Code', 'Notepad', 'Discord').
    """
    args = args or {}
    query = str(args.get("query", "")).lower().strip()
    if not query:
        raise ToolError("'query' parameter is required for focusWindow.")

    try:
        import win32gui
        import win32con

        target_hwnd = None
        target_title = ""

        def enum_cb(hwnd, _):
            nonlocal target_hwnd, target_title
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title and query in title.lower():
                    target_hwnd = hwnd
                    target_title = title
                    return False
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass

        if not target_hwnd:
            raise ToolError(f"No open window found matching '{query}'.")

        # Restore if minimized
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        time.sleep(0.05)
        win32gui.SetForegroundWindow(target_hwnd)

        return {
            "result": f"Window '{target_title}' is now in foreground and focused.",
            "title": target_title,
            "hwnd": target_hwnd,
        }
    except Exception as e:
        raise ToolError(f"Failed to focus window: {e}") from e
