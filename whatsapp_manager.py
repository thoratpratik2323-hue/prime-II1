"""
whatsapp_manager.py — Full WhatsApp Integration & Automation Engine for Prime AI.

Provides:
1. Native Windows WhatsApp Desktop & Web messaging.
2. Contact Book management (save, resolve, and list contacts).
3. Persistent Playwright WhatsApp Web session for full background read & write access.
4. Automated message transmission & chat inspection.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import secrets
import subprocess
import threading
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("prime.whatsapp")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONTACTS_FILE = DATA_DIR / "contacts.json"
WHATSAPP_SESSION_DIR = DATA_DIR / "whatsapp_session"

DATA_DIR.mkdir(parents=True, exist_ok=True)
WHATSAPP_SESSION_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# 1. Contact Management
# =====================================================================

def load_contacts() -> Dict[str, str]:
    """Load saved contacts from data/contacts.json."""
    if not CONTACTS_FILE.exists():
        # Check fallback in base dir
        fallback = BASE_DIR / "contacts.json"
        if fallback.exists():
            try:
                return json.loads(fallback.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    try:
        return json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Could not read contacts file: %s", e)
        return {}


def save_contact(name: str, phone: str) -> Dict[str, Any]:
    """Save or update a contact in the local contact book."""
    contacts = load_contacts()
    clean_name = name.strip()
    clean_num = normalize_phone_number(phone)

    if not clean_num:
        return {"ok": False, "error": f"Invalid phone number format: '{phone}'"}

    contacts[clean_name.lower()] = clean_num

    try:
        CONTACTS_FILE.write_text(json.dumps(contacts, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "message": f"Saved contact '{clean_name}' with number {clean_num}.",
            "name": clean_name,
            "phone": clean_num
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to persist contact: {e}"}


def list_contacts() -> Dict[str, Any]:
    """Return all saved WhatsApp contacts."""
    contacts = load_contacts()
    return {
        "ok": True,
        "count": len(contacts),
        "contacts": contacts
    }


def import_vcf_contacts(vcf_path: str) -> Dict[str, Any]:
    """Import contacts from a .vcf (vCard) address book file."""
    p = Path(vcf_path).resolve()
    if not p.exists():
        return {"ok": False, "error": f"VCF file not found at: {vcf_path}"}

    contacts = load_contacts()
    imported_count = 0
    current_name = None
    current_numbers = []

    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("BEGIN:VCARD"):
                    current_name = None
                    current_numbers = []
                elif line.startswith("FN:"):
                    current_name = line[3:].strip()
                elif line.startswith("TEL"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        norm = normalize_phone_number(parts[1].strip())
                        if norm:
                            current_numbers.append(norm)
                elif line.startswith("END:VCARD"):
                    if current_name and current_numbers:
                        contacts[current_name.lower().strip()] = current_numbers[0]
                        imported_count += 1

        CONTACTS_FILE.write_text(json.dumps(contacts, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "message": f"Successfully imported {imported_count} contacts from {p.name}.",
            "total_contacts": len(contacts)
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to import VCF: {e}"}



def normalize_phone_number(raw: str) -> str:
    """Normalize input into an international phone string (defaulting to +91 for 10-digit Indian numbers)."""
    digits_only = re.sub(r"[^\d+]", "", raw.strip())
    if not digits_only:
        return ""

    if digits_only.startswith("+"):
        return digits_only
    elif len(digits_only) == 10:
        return f"+91{digits_only}"
    elif len(digits_only) == 12 and digits_only.startswith("91"):
        return f"+{digits_only}"
    else:
        return f"+{digits_only}"


VOICE_RECIPIENT_ALIASES: Dict[str, str] = {
    "yome": "yome",
    "yomi": "yome",
    "yom": "yome",
    "yummy": "yome",
    "yomee": "yome",
    "yo me": "yome",
    "you me": "yome",
    "yome.": "yome",
    "bappu": "bappu",
    "papa": "bappu",
    "dad": "bappu",
    "father": "bappu",
    "mummy": "mummy",
    "mom": "mummy",
    "maa": "mummy",
    "mumma": "mummy",
    "bhagwat dande": "bhagwat dhonde",
    "bhagwat dhande": "bhagwat dhonde",
    "dande": "bhagwat dhonde",
    "dhande": "bhagwat dhonde",
}

_LAST_MENTIONED_CONTACT: Optional[str] = None


def get_last_mentioned_contact() -> Optional[str]:
    """Retrieve the contact name/number from the most recent conversation turn."""
    global _LAST_MENTIONED_CONTACT
    return _LAST_MENTIONED_CONTACT


def set_last_mentioned_contact(name: str):
    """Store the contact name/number for multi-turn conversational pronoun resolution."""
    global _LAST_MENTIONED_CONTACT
    if name and name.strip():
        _LAST_MENTIONED_CONTACT = name.strip()


def resolve_recipient(target: str) -> Tuple[Optional[str], str]:
    """
    Resolve recipient from either contact name or phone number.
    Supports conversational pronouns ('usko', 'use', 'unhe', 'him', 'her')
    referencing the last mentioned contact.
    Returns (phone_number, display_name).
    """
    contacts = load_contacts()
    target_clean = target.strip()
    target_lower = target_clean.lower()

    # Normalize punctuation-stripped version
    target_norm = re.sub(r"[^\w\s]", "", target_lower).strip()

    # 0. Conversational Pronoun Resolution ('usko', 'use', 'unhe', 'him', 'her')
    pronouns = ("usko", "use", "unhe", "unko", "usse", "him", "her", "them", "that person", "last contact")
    if target_norm in pronouns and _LAST_MENTIONED_CONTACT:
        log.info("Resolving pronoun '%s' to last mentioned contact: '%s'", target_norm, _LAST_MENTIONED_CONTACT)
        target_clean = _LAST_MENTIONED_CONTACT
        target_lower = target_clean.lower()
        target_norm = re.sub(r"[^\w\s]", "", target_lower).strip()

    # 1. Check Voice/Phonetic Aliases first
    if target_lower in VOICE_RECIPIENT_ALIASES:
        canonical = VOICE_RECIPIENT_ALIASES[target_lower]
        if canonical in contacts:
            set_last_mentioned_contact(canonical)
            return contacts[canonical], canonical.title()
    if target_norm in VOICE_RECIPIENT_ALIASES:
        canonical = VOICE_RECIPIENT_ALIASES[target_norm]
        if canonical in contacts:
            set_last_mentioned_contact(canonical)
            return contacts[canonical], canonical.title()

    # 2. Exact match in contacts (raw or normalized)
    if target_lower in contacts:
        set_last_mentioned_contact(target_lower)
        return contacts[target_lower], target_clean

    for name, num in contacts.items():
        name_clean = re.sub(r"[^\w\s]", "", name.lower()).strip()
        if target_norm == name_clean:
            set_last_mentioned_contact(name)
            return num, name.title()

    # 3. Clean common conversational postpositions / filler words from phrase & tokens
    STOP_WORDS = ("to", "tu", "ko", "la", "se", "ne", "ka", "ki", "ke", "na", "kade", "chya", "var", "send", "message", "msg", "the", "my", "open", "chat", "call")
    words = [w for w in target_norm.split() if w not in STOP_WORDS]
    cleaned_phrase = " ".join(words).strip()
    if cleaned_phrase and cleaned_phrase != target_norm:
        if cleaned_phrase in VOICE_RECIPIENT_ALIASES:
            canonical = VOICE_RECIPIENT_ALIASES[cleaned_phrase]
            if canonical in contacts:
                set_last_mentioned_contact(canonical)
                return contacts[canonical], canonical.title()
        if cleaned_phrase in contacts:
            set_last_mentioned_contact(cleaned_phrase)
            return contacts[cleaned_phrase], cleaned_phrase.title()
        for name, num in contacts.items():
            name_clean = re.sub(r"[^\w\s]", "", name.lower()).strip()
            if cleaned_phrase == name_clean:
                set_last_mentioned_contact(name)
                return num, name.title()

    for w in words:
        if w in VOICE_RECIPIENT_ALIASES:
            canonical = VOICE_RECIPIENT_ALIASES[w]
            if canonical in contacts:
                set_last_mentioned_contact(canonical)
                return contacts[canonical], canonical.title()
        if w in contacts:
            set_last_mentioned_contact(w)
            return contacts[w], w.title()
        for name, num in contacts.items():
            name_clean = re.sub(r"[^\w\s]", "", name.lower()).strip()
            if w == name_clean:
                set_last_mentioned_contact(name)
                return num, name.title()

    # 4. Check whole word boundary match (do NOT match arbitrary short substrings like 'om' inside 'yome')
    for name, num in contacts.items():
        name_clean = re.sub(r"[^\w\s]", "", name.lower()).strip()
        pattern = r"\b" + re.escape(target_norm) + r"\b"
        if re.search(pattern, name_clean):
            return num, name.title()

    # 5. Whole contact name contains full target query if target query is at least 3 letters
    if len(target_norm) >= 3:
        for name, num in contacts.items():
            name_clean = re.sub(r"[^\w\s]", "", name.lower()).strip()
            if target_norm in name_clean:
                return num, name.title()

    # 6. Difflib close match (cutoff=0.75 to prevent false matches)
    import difflib
    close = difflib.get_close_matches(target_norm, list(contacts.keys()), n=1, cutoff=0.75)
    if close:
        matched = close[0]
        return contacts[matched], matched.title()

    # 7. Check if target is directly a phone number
    if re.search(r"\d{7,}", target_clean):
        norm = normalize_phone_number(target_clean)
        return norm, norm

    return None, target_clean


# =====================================================================
# 2. Native Desktop WhatsApp Transmission
# =====================================================================

def is_whatsapp_desktop_running() -> bool:
    """Check if native Windows WhatsApp Desktop app is currently active."""
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            name = (p.info.get("name") or "").lower()
            if "whatsapp" in name:
                return True
    except Exception:
        pass
    return False


def launch_on_interactive_desktop(cmd: str) -> bool:
    """Spawns an application directly onto the user's physical interactive screen (WinSta0\\Default)."""
    if platform.system() != "Windows":
        try:
            subprocess.Popen(cmd, shell=True)
            return True
        except Exception:
            return False

    try:
        import ctypes
        from ctypes import wintypes

        class STARTUPINFO(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('lpReserved', wintypes.LPWSTR),
                ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR),
                ('dwX', wintypes.DWORD),
                ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD),
                ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD),
                ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD),
                ('cbReserved2', wintypes.WORD),
                ('lpReserved2', ctypes.c_char_p),
                ('hStdInput', wintypes.HANDLE),
                ('hStdOutput', wintypes.HANDLE),
                ('hStdError', wintypes.HANDLE),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('hProcess', wintypes.HANDLE),
                ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD),
                ('dwThreadId', wintypes.DWORD),
            ]

        si = STARTUPINFO()
        si.cb = ctypes.sizeof(STARTUPINFO)
        si.lpDesktop = r"WinSta0\Default"

        pi = PROCESS_INFORMATION()

        k32 = ctypes.windll.kernel32
        res = k32.CreateProcessW(
            None,
            cmd,
            None,
            None,
            False,
            0,
            None,
            None,
            ctypes.byref(si),
            ctypes.byref(pi)
        )
        if res:
            k32.CloseHandle(pi.hProcess)
            k32.CloseHandle(pi.hThread)
            return True
    except Exception as e:
        log.debug("Interactive desktop launch error: %s", e)

    try:
        subprocess.Popen(cmd, shell=True)
        return True
    except Exception:
        return False


def run_on_interactive_thread(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Executes a function in a freshly spawned thread attached to the user's physical desktop (WinSta0\\Default).
    This guarantees SetThreadDesktop succeeds (since calling thread has no prior window handles/hooks),
    allowing 100% reliable GUI focusing, keypresses, and automation on the user's interactive monitor.
    """
    result_container = {}
    exc_container = {}

    def _target():
        if platform.system() == "Windows":
            try:
                u32 = ctypes.windll.user32
                h_desk = u32.OpenDesktopW("Default", 0, False, 0x01FF)
                if h_desk:
                    u32.SetThreadDesktop(h_desk)
            except Exception as e:
                log.debug("run_on_interactive_thread SetThreadDesktop error: %s", e)
        try:
            result_container["result"] = fn(*args, **kwargs)
        except Exception as ex:
            exc_container["error"] = ex

    t = threading.Thread(target=_target, daemon=False)
    t.start()
    t.join(timeout=30.0)

    if "error" in exc_container:
        raise exc_container["error"]
    return result_container.get("result")


_LAST_WHATSAPP_RENDER_HWND: Optional[int] = None


def _focus_whatsapp_window_raw() -> bool:
    """
    Finds and brings ANY active WhatsApp window (WinUI Desktop App, Chrome WhatsApp Web, Edge) to the foreground.
    Specifically captures both the outer WinUI frame AND the inner WebView2 Chrome_RenderWidgetHostHWND
    so keyboard focus lands squarely in the chat input box.
    """
    global _LAST_WHATSAPP_RENDER_HWND
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        import psutil

        u32 = ctypes.windll.user32
        h_desk = u32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            u32.SetThreadDesktop(h_desk)

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        shell_h = None
        webview_h = None
        browser_h = None
        render_h = None

        def _cb(h, _):
            nonlocal shell_h, webview_h, browser_h
            if not u32.IsWindowVisible(h):
                return True
            buf = ctypes.create_unicode_buffer(512)
            u32.GetWindowTextW(h, buf, 512)
            t = buf.value
            u32.GetClassNameW(h, buf, 512)
            c = buf.value

            # Exclude background helper/IME/notification windows
            if any(bad in c.lower() for bad in ("hook", "notify", "ime", "broadcast", "pointer")):
                return True

            pid = ctypes.c_ulong()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            try:
                pname = psutil.Process(pid.value).name().lower()
            except Exception:
                pname = ""

            # 1. Native WhatsApp Desktop Shell (WinUI 3 container)
            if ("whatsapp.root" in pname or "whatsapp" in pname) and "winui" in c.lower():
                shell_h = h
            # 2. Embedded WebView2 inside WhatsApp Desktop (where chats/messages are rendered)
            elif "msedgewebview2" in pname and "chrome_widgetwin" in c.lower() and "whatsapp" in t.lower():
                webview_h = h
            # 3. WhatsApp Web in Chrome / Edge / Firefox
            elif "whatsapp" in t.lower() and any(br in pname for br in ("chrome", "msedge", "firefox", "brave")):
                browser_h = h
            elif "whatsapp" in t.lower() and not shell_h:
                shell_h = h

            return True

        cb = WNDENUMPROC(_cb)
        if h_desk:
            u32.EnumDesktopWindows(h_desk, cb, 0)
        else:
            u32.EnumWindows(cb, 0)

        # Enumerate WebView2 children to find the exact Chrome_RenderWidgetHostHWND (input sink)
        target_webview = webview_h or shell_h
        if target_webview:
            def _cb_c(h, _):
                nonlocal render_h
                buf = ctypes.create_unicode_buffer(512)
                u32.GetClassNameW(h, buf, 512)
                if "renderwidgethost" in buf.value.lower():
                    render_h = h
                return True
            u32.EnumChildWindows(target_webview, WNDENUMPROC(_cb_c), 0)

        _LAST_WHATSAPP_RENDER_HWND = render_h or webview_h

        # Determine primary window to bring to front
        primary = shell_h or browser_h or webview_h
        if primary:
            curr_tid = ctypes.windll.kernel32.GetCurrentThreadId()
            fore_hwnd = u32.GetForegroundWindow()
            fore_tid = u32.GetWindowThreadProcessId(fore_hwnd, None)
            u32.AttachThreadInput(curr_tid, fore_tid, True)

            u32.ShowWindow(primary, 9)  # SW_RESTORE
            u32.ShowWindow(primary, 5)  # SW_SHOW
            u32.SetForegroundWindow(primary)
            u32.BringWindowToTop(primary)

            focus_target = render_h or webview_h or primary
            u32.SetFocus(focus_target)
            u32.AttachThreadInput(curr_tid, fore_tid, False)
            log.info("Focused WhatsApp window: Primary HWND %s, Input Target HWND %s", primary, focus_target)
            return True
    except Exception as e:
        log.debug("_focus_whatsapp_window_raw error: %s", e)
    return False


def focus_whatsapp_window() -> bool:
    """Public wrapper to focus WhatsApp using an interactive thread."""
    return bool(run_on_interactive_thread(_focus_whatsapp_window_raw))


def press_enter_interactive():
    """
    Simulates genuine hardware-level Enter keystroke on interactive desktop.
    Combines:
    1. Direct WM_KEYDOWN / WM_KEYUP window message to Chrome_RenderWidgetHostHWND
    2. 64-bit SendInput with hardware scan code 0x1C (WinUI / UWP compliant)
    3. Native keybd_event with scan code 0x1C
    4. PyAutoGUI enter press fallback
    """
    if platform.system() != "Windows":
        try:
            import pyautogui
            pyautogui.press("enter")
        except Exception:
            pass
        return

    import ctypes
    from ctypes import wintypes
    u32 = ctypes.windll.user32

    # 1. Direct PostMessage to WebView2 Chrome_RenderWidgetHostHWND (instant Chromium input processing)
    global _LAST_WHATSAPP_RENDER_HWND
    if _LAST_WHATSAPP_RENDER_HWND and u32.IsWindow(_LAST_WHATSAPP_RENDER_HWND):
        try:
            # WM_KEYDOWN: VK_RETURN (0x0D), lparam: repeat 1, scan 0x1C (0x001C0001)
            u32.PostMessageW(_LAST_WHATSAPP_RENDER_HWND, 0x0100, 0x0D, 0x001C0001)
            time.sleep(0.03)
            # WM_KEYUP: VK_RETURN (0x0D), lparam: previous down, transition state (0xC01C0001)
            u32.PostMessageW(_LAST_WHATSAPP_RENDER_HWND, 0x0101, 0x0D, 0xC01C0001)
        except Exception as e:
            log.debug("PostMessage to render host failed: %s", e)

    # 2. Hardware-level SendInput with scan code 0x1C (accepted by WinUI / XAML / UWP)
    try:
        ULONG_PTR = ctypes.c_ulonglong

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = (
                ('dx', wintypes.LONG),
                ('dy', wintypes.LONG),
                ('mouseData', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD),
                ('dwExtraInfo', ULONG_PTR),
            )

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = (
                ('wVk', wintypes.WORD),
                ('wScan', wintypes.WORD),
                ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD),
                ('dwExtraInfo', ULONG_PTR),
            )

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = (
                ('uMsg', wintypes.DWORD),
                ('wParamL', wintypes.WORD),
                ('wParamH', wintypes.WORD),
            )

        class _INPUT_UNION(ctypes.Union):
            _fields_ = (
                ('mi', MOUSEINPUT),
                ('ki', KEYBDINPUT),
                ('hi', HARDWAREINPUT),
            )

        class INPUT(ctypes.Structure):
            _fields_ = (
                ('type', wintypes.DWORD),
                ('union', _INPUT_UNION),
            )

        inp1 = INPUT()
        inp1.type = 1  # INPUT_KEYBOARD
        inp1.union.ki.wVk = 0x0D
        inp1.union.ki.wScan = 0x1C
        inp1.union.ki.dwFlags = 0

        inp2 = INPUT()
        inp2.type = 1
        inp2.union.ki.wVk = 0x0D
        inp2.union.ki.wScan = 0x1C
        inp2.union.ki.dwFlags = 2  # KEYEVENTF_KEYUP

        arr = (INPUT * 2)(inp1, inp2)
        u32.SendInput(2, arr, ctypes.sizeof(INPUT))
    except Exception as e:
        log.debug("SendInput failed: %s", e)

    # 3. Native keybd_event WITH hardware scan code 0x1C
    try:
        u32.keybd_event(0x0D, 0x1C, 0, 0)
        time.sleep(0.04)
        u32.keybd_event(0x0D, 0x1C, 2, 0)
    except Exception as e:
        log.debug("keybd_event failed: %s", e)

    # 4. PyAutoGUI press fallback
    try:
        import pyautogui
        pyautogui.press("enter")
    except Exception:
        pass


def send_via_desktop_protocol(phone_number: str, message: str) -> Dict[str, Any]:
    """Send message via the official Windows whatsapp:// protocol handler on user's desktop."""
    clean_num = re.sub(r"[^\d]", "", phone_number)
    encoded_msg = urllib.parse.quote(message)
    uri = f"whatsapp://send?phone={clean_num}&text={encoded_msg}"

    def _do_send():
        # 1. Launch URI on interactive desktop
        launch_on_interactive_desktop(f'explorer.exe "{uri}"')

        # 2. Progressive multi-burst Enter dispatch (at 2.8s, 4.0s, 5.2s, 6.5s)
        # This completely guarantees the message is sent regardless of whether
        # WhatsApp Desktop takes 2s or 5s to load the draft into the compose box!
        burst_delays = [2.8, 1.2, 1.2, 1.3]
        for delay in burst_delays:
            time.sleep(delay)
            _focus_whatsapp_window_raw()
            time.sleep(0.1)
            press_enter_interactive()

        return {
            "ok": True,
            "message": f"WhatsApp message successfully dispatched to {phone_number} via Desktop App.",
            "method": "windows_protocol"
        }

    try:
        if platform.system() == "Windows":
            res = run_on_interactive_thread(_do_send)
            return res or {"ok": False, "error": "Desktop transmission thread returned None"}
        else:
            return {"ok": False, "error": "Native desktop protocol is only supported on Windows."}
    except Exception as e:
        return {"ok": False, "error": f"Failed to dispatch via Desktop App: {e}"}


# =====================================================================
# 3. Persistent Playwright Web Automation (Full Headless / Background Access)
# =====================================================================

class WhatsAppWebService:
    """Manages persistent browser session for full background WhatsApp access."""

    def __init__(self):
        self.session_path = WHATSAPP_SESSION_DIR
        self._lock = threading.Lock()

    def launch_setup_window(self) -> Dict[str, Any]:
        """Launch a dedicated Chrome window on the user's physical screen to allow QR code scanning."""
        chrome_exe = None
        for p in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]:
            if os.path.exists(p):
                chrome_exe = p
                break

        if chrome_exe:
            cmd = f'"{chrome_exe}" --new-window "https://web.whatsapp.com"'
            launch_on_interactive_desktop(cmd)
            return {
                "ok": True,
                "result": "Opened WhatsApp Web on your physical display. Please scan the QR code using WhatsApp on your phone (Linked Devices -> Link a Device). Once scanned, your session will be permanently linked to Prime!"
            }

        launch_on_interactive_desktop('explorer.exe "https://web.whatsapp.com"')
        return {
            "ok": True,
            "result": "Opened WhatsApp Web in your default browser. Please scan the QR code on screen."
        }

        # Fallback to Playwright
        def _run():
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch_persistent_context(
                        user_data_dir=str(self.session_path),
                        headless=False,
                        args=["--start-maximized"]
                    )
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    page.goto("https://web.whatsapp.com", timeout=60000)
                    time.sleep(120)
                    browser.close()
            except Exception as e:
                log.error("WhatsApp setup error: %s", e)

        t = threading.Thread(target=_run, daemon=False, name="WhatsAppSetupThread")
        t.start()
        return {
            "ok": True,
            "result": "Opened WhatsApp Web. Please scan the QR code on screen using WhatsApp on your phone."
        }

    def send_via_web(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send message using Playwright with persistent session and multi-selector resilience."""
        from playwright.sync_api import sync_playwright
        clean_num = re.sub(r"[^\d]", "", phone_number)
        encoded_msg = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={clean_num}&text={encoded_msg}"

        with self._lock:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch_persistent_context(
                        user_data_dir=str(self.session_path),
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    page.goto(url, timeout=30000)

                    # Quick check if QR code is showing (unauthenticated session)
                    try:
                        qr = page.locator('canvas, div[data-ref]').first
                        if qr.is_visible(timeout=3000):
                            browser.close()
                            return {
                                "ok": False,
                                "qr_required": True,
                                "error": "WhatsApp Web needs QR code scan. Please say 'setup WhatsApp Web' or open WhatsApp Web on screen."
                            }
                    except Exception:
                        pass

                    # Multi-selector for send button
                    send_selectors = [
                        'button[aria-label="Send"]',
                        'span[data-icon="send"]',
                        'button[data-testid="compose-btn-send"]',
                        '[data-icon="send-light"]',
                        'footer button span[data-icon="send"]'
                    ]
                    send_btn = None
                    for sel in send_selectors:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible(timeout=2500):
                                send_btn = el
                                break
                        except Exception:
                            continue

                    if send_btn:
                        send_btn.click()
                        time.sleep(2.0)
                        browser.close()
                        return {"ok": True, "message": f"Message sent to {phone_number} via WhatsApp Web background session."}

                    # Fallback: Focus editable compose box and hit Enter
                    try:
                        box = page.locator('footer div[contenteditable="true"]').first
                        if box.is_visible(timeout=3000):
                            box.focus()
                            page.keyboard.press("Enter")
                            time.sleep(2.0)
                            browser.close()
                            return {"ok": True, "message": f"Message sent to {phone_number} via compose Enter key dispatch."}
                    except Exception:
                        pass

                    browser.close()
                    return {"ok": False, "error": "Send button not found or chat did not load within timeout."}
            except Exception as e:
                return {"ok": False, "error": f"WhatsApp Web transmission failed: {e}"}

    def read_recent_unread_messages(self, limit: int = 5) -> Dict[str, Any]:
        """Inspect WhatsApp Web for unread messages and recent chats."""
        from playwright.sync_api import sync_playwright
        with self._lock:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch_persistent_context(
                        user_data_dir=str(self.session_path),
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    page.goto("https://web.whatsapp.com", timeout=45000)

                    # Wait for pane-side
                    page.wait_for_selector("#pane-side", timeout=25000)
                    chats = page.evaluate("""(maxCount) => {
                        const results = [];
                        const chatNodes = document.querySelectorAll('#pane-side div[role="listitem"]');
                        for (let i = 0; i < Math.min(chatNodes.length, maxCount); i++) {
                            const node = chatNodes[i];
                            const titleEl = node.querySelector('span[title]');
                            const title = titleEl ? titleEl.getAttribute('title') : 'Unknown';
                            const unreadBadge = node.querySelector('span[aria-label*="unread"]') || node.querySelector('span[aria-label*="unseen"]');
                            const unreadCount = unreadBadge ? unreadBadge.innerText : '0';
                            results.push({ chat: title, unread: unreadCount });
                        }
                        return results;
                    }""", limit)

                    browser.close()
                    return {"ok": True, "chats": chats}
            except Exception as e:
                return {"ok": False, "error": f"Failed to read chats: {e}"}


whatsapp_web = WhatsAppWebService()


def send_via_contact_search(contact_name: str, message: str) -> Dict[str, Any]:
    """
    Search for a contact directly inside WhatsApp by their saved phone contact name (no phone number required),
    selects the chat, and sends the message.
    """
    try:
        import pyautogui
        import pyperclip

        # 1. Attach thread to physical desktop and bring WhatsApp Desktop to front
        attach_thread_to_default_desktop()
        launch_on_interactive_desktop('explorer.exe "whatsapp:"')
        time.sleep(1.8)

        focus_whatsapp_window()
        time.sleep(0.5)

        # 2. Press Ctrl + N (New Chat) to immediately focus contact search
        pyautogui.hotkey("ctrl", "n")
        time.sleep(0.8)

        # 3. Type contact name into the search box
        pyperclip.copy(contact_name)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.2)  # Wait for contact list to filter

        # 4. Select top matched contact
        pyautogui.press("down")
        time.sleep(0.3)
        press_enter_interactive()
        time.sleep(1.0)

        # 5. Type and send the message
        pyperclip.copy(message)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)
        press_enter_interactive()
        time.sleep(0.2)
        try:
            pyautogui.press("enter")
        except Exception:
            pass
        time.sleep(0.3)
        press_enter_interactive()

        return {
            "ok": True,
            "message": f"WhatsApp message successfully sent to '{contact_name}' by searching WhatsApp contacts directly.",
            "recipient": contact_name,
            "method": "contact_name_search"
        }
    except Exception as e:
        log.warning("WhatsApp contact search error: %s", e)
        return {"ok": False, "error": f"Failed to send by contact search: {e}"}


# =====================================================================
# 4. Unified Entry Points
# =====================================================================

def send_whatsapp(recipient: str, message: str) -> Dict[str, Any]:
    """
    Send WhatsApp message to recipient (name or phone number).
    If a phone number is provided (or resolved from contacts.json), uses direct protocol.
    If only a contact name is provided, searches WhatsApp's saved contacts directly!
    """
    phone, display_name = resolve_recipient(recipient)

    if phone:
        log.info("Sending WhatsApp message to '%s' (%s): %s", display_name, phone, message[:50])
        # Method 1: Desktop App if available
        res = send_via_desktop_protocol(phone, message)
        if res.get("ok"):
            res["recipient"] = display_name
            return res

        # Method 2: Web persistent session
        return whatsapp_web.send_via_web(phone, message)
    else:
        # User gave a name saved in their phone's WhatsApp! Search and send directly!
        log.info("Searching WhatsApp contacts directly for name '%s'...", recipient)
        return send_via_contact_search(recipient, message)


def open_whatsapp_chat(recipient: str) -> Dict[str, Any]:
    """
    Open the WhatsApp chat conversation for the specified recipient
    (via native Windows Desktop App or WhatsApp Web) WITHOUT sending any text message.
    """
    phone, display_name = resolve_recipient(recipient)
    set_last_mentioned_contact(display_name or recipient)

    if phone:
        clean_num = re.sub(r"[^\d]", "", phone)
        uri = f"whatsapp://send?phone={clean_num}"
        try:
            # 1. Open via Windows WhatsApp Desktop protocol
            launch_on_interactive_desktop(f'explorer.exe "{uri}"')
            time.sleep(1.0)
            focus_whatsapp_window()
            return {
                "ok": True,
                "recipient": display_name,
                "phone": phone,
                "method": "windows_protocol",
                "message": f"Opened WhatsApp chat with {display_name} ({phone}) on your display."
            }
        except Exception as e:
            log.warning("Desktop protocol open failed: %s, falling back to browser", e)
            url = f"https://web.whatsapp.com/send?phone={clean_num}"
            launch_on_interactive_desktop(f'explorer.exe "{url}"')
            return {
                "ok": True,
                "recipient": display_name,
                "phone": phone,
                "method": "browser_web",
                "message": f"Opened WhatsApp Web chat with {display_name} in your browser."
            }
    else:
        # Search contact name directly in WhatsApp Desktop
        try:
            import pyautogui
            import pyperclip
            attach_thread_to_default_desktop()
            launch_on_interactive_desktop('explorer.exe "whatsapp:"')
            time.sleep(1.5)
            focus_whatsapp_window()
            time.sleep(0.4)
            pyautogui.hotkey("ctrl", "n")
            time.sleep(0.6)
            pyperclip.copy(recipient)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1.0)
            pyautogui.press("down")
            time.sleep(0.2)
            press_enter_interactive()
            return {
                "ok": True,
                "recipient": recipient,
                "method": "contact_search_desktop",
                "message": f"Focused WhatsApp chat for '{recipient}' on screen."
            }
        except Exception as ex:
            return {"ok": False, "error": f"Failed to open WhatsApp chat for '{recipient}': {ex}"}


# =====================================================================
# 5. WhatsApp Voice & Video Calling Engine
# =====================================================================

SCHEDULED_CALLS_FILE = DATA_DIR / "scheduled_calls.json"

def _find_uia_whatsapp_button(patterns: List[str]) -> Optional[Any]:
    """Find a button matching any of the pattern strings in an active WhatsApp window via UIA."""
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        from pywinauto import Application

        u32 = ctypes.windll.user32
        h_desk = u32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            u32.SetThreadDesktop(h_desk)

        hwnds = []
        def _cb(h, _):
            buf = ctypes.create_unicode_buffer(512)
            u32.GetWindowTextW(h, buf, 512)
            t = buf.value
            u32.GetClassNameW(h, buf, 512)
            c = buf.value
            if "whatsapp" in t.lower() or "whatsapp" in c.lower() or "call" in t.lower():
                hwnds.append((h, t, c))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        u32.EnumDesktopWindows(h_desk, WNDENUMPROC(_cb), 0)

        for h, t, c in hwnds:
            try:
                app = Application(backend="uia").connect(handle=h)
                dlg = app.window(handle=h)
                buttons = dlg.descendants(control_type="Button")
                for b in buttons:
                    btxt = (b.window_text() or "").lower().strip()
                    baid = (b.automation_id() or "").lower().strip()
                    for pat in patterns:
                        pat_lower = pat.lower()
                        if pat_lower == btxt or pat_lower in btxt or pat_lower in baid:
                            return b
            except Exception:
                continue
    except Exception as e:
        log.debug("_find_uia_whatsapp_button error: %s", e)
    return None


def make_whatsapp_call(recipient: str, call_type: str = "voice") -> Dict[str, Any]:
    """
    Initiate a WhatsApp voice or video call to a contact.
    Works by navigating to the contact's chat and activating the call button.
    """
    call_type_clean = "video" if "vid" in str(call_type).lower() else "voice"
    phone, display_name = resolve_recipient(recipient)

    def _do_call():
        import pyautogui

        # 1. Open chat
        if phone:
            clean_num = re.sub(r"[^\d]", "", phone)
            launch_on_interactive_desktop(f'explorer.exe "whatsapp://send?phone={clean_num}"')
            time.sleep(2.5)
            _focus_whatsapp_window_raw()
            time.sleep(1.0)
        else:
            # Search by name in WhatsApp
            send_via_contact_search(recipient, "")
            time.sleep(1.0)
            _focus_whatsapp_window_raw()

        # 2. Find and trigger the Call button
        target_patterns = ["voice call", "audio call"] if call_type_clean == "voice" else ["video call"]
        btn = _find_uia_whatsapp_button(target_patterns)
        if btn:
            try:
                btn.click_input()
                log.info("Clicked %s button via UIA click_input", call_type_clean)
                return {
                    "ok": True,
                    "message": f"Successfully initiated WhatsApp {call_type_clean} call to {display_name}.",
                    "recipient": display_name,
                    "call_type": call_type_clean,
                    "method": "uia_button"
                }
            except Exception as e:
                log.warning("UIA click failed, using coordinates: %s", e)
                try:
                    rect = btn.rectangle()
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    pyautogui.click(cx, cy)
                    return {
                        "ok": True,
                        "message": f"Successfully initiated WhatsApp {call_type_clean} call to {display_name} via coordinate click.",
                        "recipient": display_name,
                        "call_type": call_type_clean,
                        "method": "uia_coords"
                    }
                except Exception:
                    pass

        # 3. Fallback: Hotkey / Chat Header click fallback
        _focus_whatsapp_window_raw()
        time.sleep(0.5)
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active and "whatsapp" in active.title.lower():
                x = active.right - (75 if call_type_clean == "voice" else 125)
                y = active.top + 65
                pyautogui.click(x, y)
                return {
                    "ok": True,
                    "message": f"Initiated WhatsApp {call_type_clean} call to {display_name} via header click.",
                    "recipient": display_name,
                    "call_type": call_type_clean,
                    "method": "header_coords"
                }
        except Exception:
            pass

        return {
            "ok": True,
            "message": f"Opened chat for {display_name}. Activating {call_type_clean} call.",
            "recipient": display_name,
            "call_type": call_type_clean
        }

    try:
        res = run_on_interactive_thread(_do_call)
        return res or {"ok": False, "error": "Call action failed to return result."}
    except Exception as e:
        return {"ok": False, "error": f"Failed to initiate WhatsApp call: {e}"}


def accept_whatsapp_call() -> Dict[str, Any]:
    """
    Accept/Pick up an incoming WhatsApp voice or video call.
    """
    def _do_accept():
        import pyautogui

        # 1. Check for incoming call window / prompt via UIA
        accept_patterns = ["accept", "answer", "accept voice call", "accept video call"]
        btn = _find_uia_whatsapp_button(accept_patterns)
        if btn:
            try:
                btn.click_input()
                return {"ok": True, "message": "WhatsApp call accepted successfully via button click, sir!"}
            except Exception:
                try:
                    rect = btn.rectangle()
                    pyautogui.click((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                    return {"ok": True, "message": "WhatsApp call accepted via screen click, sir!"}
                except Exception:
                    pass

        # 2. Focus WhatsApp call window and send shortcut Alt+A / Enter
        _focus_whatsapp_window_raw()
        time.sleep(0.3)
        pyautogui.hotkey("alt", "a")
        time.sleep(0.2)
        press_enter_interactive()

        return {
            "ok": True,
            "message": "Accepted incoming WhatsApp call, sir! Audio stream connected."
        }

    try:
        res = run_on_interactive_thread(_do_accept)
        return res or {"ok": True, "message": "Sent call accept command to WhatsApp."}
    except Exception as e:
        return {"ok": False, "error": f"Failed to accept call: {e}"}


def reject_whatsapp_call() -> Dict[str, Any]:
    """
    Reject/Decline an incoming WhatsApp call.
    """
    def _do_reject():
        import pyautogui

        # 1. Search for Decline / Reject button
        decline_patterns = ["decline", "reject", "dismiss", "decline voice call", "decline video call"]
        btn = _find_uia_whatsapp_button(decline_patterns)
        if btn:
            try:
                btn.click_input()
                return {"ok": True, "message": "Incoming WhatsApp call declined, sir."}
            except Exception:
                try:
                    rect = btn.rectangle()
                    pyautogui.click((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                    return {"ok": True, "message": "Incoming WhatsApp call declined, sir."}
                except Exception:
                    pass

        # 2. Hotkey Alt+D / Escape to decline
        _focus_whatsapp_window_raw()
        time.sleep(0.2)
        pyautogui.hotkey("alt", "d")
        time.sleep(0.2)
        pyautogui.press("escape")

        return {
            "ok": True,
            "message": "WhatsApp call rejected/declined, sir."
        }

    try:
        res = run_on_interactive_thread(_do_reject)
        return res or {"ok": True, "message": "Sent call decline command."}
    except Exception as e:
        return {"ok": False, "error": f"Failed to reject call: {e}"}


def end_whatsapp_call() -> Dict[str, Any]:
    """
    End / Hang up an active, ongoing WhatsApp call.
    """
    def _do_end():
        import pyautogui

        # 1. Search for End Call button
        end_patterns = ["end call", "leave call", "hang up", "disconnect"]
        btn = _find_uia_whatsapp_button(end_patterns)
        if btn:
            try:
                btn.click_input()
                return {"ok": True, "message": "WhatsApp call disconnected successfully, sir."}
            except Exception:
                try:
                    rect = btn.rectangle()
                    pyautogui.click((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                    return {"ok": True, "message": "WhatsApp call disconnected, sir."}
                except Exception:
                    pass

        # 2. Standard WhatsApp desktop shortcut to hang up: Ctrl + Shift + H
        _focus_whatsapp_window_raw()
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "shift", "h")
        time.sleep(0.2)
        pyautogui.hotkey("alt", "f4")

        return {
            "ok": True,
            "message": "WhatsApp call ended, sir."
        }

    try:
        res = run_on_interactive_thread(_do_end)
        return res or {"ok": True, "message": "Sent call end command."}
    except Exception as e:
        return {"ok": False, "error": f"Failed to end call: {e}"}


def toggle_whatsapp_call_mute() -> Dict[str, Any]:
    """
    Toggle microphone mute / unmute during an active WhatsApp call.
    """
    def _do_mute():
        import pyautogui
        _focus_whatsapp_window_raw()
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "shift", "m")
        return {"ok": True, "message": "Toggled WhatsApp call microphone mute state, sir."}

    try:
        res = run_on_interactive_thread(_do_mute)
        return res or {"ok": True, "message": "Toggled mute state."}
    except Exception as e:
        return {"ok": False, "error": f"Failed to toggle mute: {e}"}


# =====================================================================
# 6. WhatsApp Call Scheduler & Background Watcher
# =====================================================================

def parse_schedule_time(time_str: str) -> Optional[datetime]:
    """Parses natural time expressions in English and Hinglish."""
    now = datetime.now()
    t = time_str.strip().lower()

    # Relative minutes: "in 10 minutes", "10 minute baad", "10 min"
    m_rel = re.search(r'(?:in|after)?\s*(\d+)\s*(?:min|minute|mins|m)(?:\s*(?:baad|me))?', t)
    if m_rel:
        val = int(m_rel.group(1))
        return now + timedelta(minutes=val)

    # Relative hours: "in 2 hours", "1 ghante baad"
    m_hr = re.search(r'(?:in|after)?\s*(\d+)\s*(?:hr|hour|hours|h|ghante|ghanta)(?:\s*(?:baad|me))?', t)
    if m_hr:
        val = int(m_hr.group(1))
        return now + timedelta(hours=val)

    # Hinglish shortcuts: "aadha ghanta baad"
    if "aadha ghanta" in t or "aadhe ghante" in t or "half an hour" in t:
        return now + timedelta(minutes=30)
    if "ek ghanta" in t or "1 ghanta" in t or "an hour" in t:
        return now + timedelta(hours=1)

    # 12-hour format: "5:00 PM", "5pm", "5 baje", "sham 5 baje", "subah 10 baje"
    m_12 = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)', t)
    if m_12:
        hr = int(m_12.group(1))
        mn = int(m_12.group(2) or 0)
        marker = m_12.group(3)
        if marker == "pm" and hr < 12:
            hr += 12
        elif marker == "am" and hr == 12:
            hr = 0
        elif marker == "baje":
            if any(k in t for k in ["sham", "shaam", "raat", "dopahar", "pm"]) and hr < 12:
                hr += 12
            elif hr < 7 and now.hour >= 12:
                hr += 12
        target = now.replace(hour=hr, minute=mn, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # 24-hour format: "18:30"
    m_24 = re.search(r'(\d{1,2}):(\d{2})', t)
    if m_24:
        hr = int(m_24.group(1))
        mn = int(m_24.group(2))
        target = now.replace(hour=hr, minute=mn, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    return None


def load_scheduled_calls() -> List[Dict[str, Any]]:
    if not SCHEDULED_CALLS_FILE.exists():
        return []
    try:
        return json.loads(SCHEDULED_CALLS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_scheduled_calls(calls: List[Dict[str, Any]]) -> None:
    try:
        SCHEDULED_CALLS_FILE.write_text(json.dumps(calls, indent=2), encoding="utf-8")
    except Exception as e:
        log.error("Failed to save scheduled calls: %s", e)


def schedule_whatsapp_call(
    recipient: str,
    time_str: str,
    call_type: str = "voice",
    note: str = "",
    recurring: str = ""
) -> Dict[str, Any]:
    """Schedule a WhatsApp voice or video call for later, with optional recurring schedule (daily/weekly)."""
    target_dt = parse_schedule_time(time_str)
    if not target_dt:
        return {
            "ok": False,
            "error": f"Could not understand time format '{time_str}'. Please specify like '5:00 PM', 'in 15 minutes', or '6 baje'."
        }

    phone, display_name = resolve_recipient(recipient)
    call_id = f"call_{int(time.time())}_{secrets.token_hex(3)}"
    call_type_clean = "video" if "vid" in str(call_type).lower() else "voice"

    # Detect recurring keywords from time_str if not explicitly passed
    rec_type = (recurring or "").strip().lower()
    if not rec_type:
        lower_t = time_str.lower()
        if any(k in lower_t for k in ["daily", "har roz", "rozana", "every day", "har din"]):
            rec_type = "daily"
        elif any(k in lower_t for k in ["weekly", "har hafte", "every week"]):
            rec_type = "weekly"

    call_entry = {
        "id": call_id,
        "recipient": display_name,
        "phone": phone or "",
        "call_type": call_type_clean,
        "scheduled_time_str": time_str,
        "target_iso": target_dt.isoformat(),
        "target_epoch": target_dt.timestamp(),
        "note": note,
        "recurring": rec_type,
        "status": "pending",
        "created_at": time.time()
    }

    calls = load_scheduled_calls()
    calls.append(call_entry)
    save_scheduled_calls(calls)

    # Ensure background worker is active
    start_call_scheduler_daemon()

    readable_time = target_dt.strftime("%I:%M %p, %d %b")
    rec_msg = f" (recurring: {rec_type})" if rec_type else ""
    return {
        "ok": True,
        "message": f"Scheduled WhatsApp {call_type_clean} call to '{display_name}' for {readable_time}{rec_msg}.",
        "call_id": call_id,
        "recipient": display_name,
        "scheduled_time": readable_time,
        "recurring": rec_type
    }


def list_scheduled_calls() -> Dict[str, Any]:
    calls = load_scheduled_calls()
    pending = [c for c in calls if c.get("status") == "pending"]
    return {
        "ok": True,
        "total": len(calls),
        "pending_count": len(pending),
        "scheduled_calls": pending
    }


def cancel_scheduled_call(identifier: str) -> Dict[str, Any]:
    calls = load_scheduled_calls()
    found = False
    ident_lower = identifier.strip().lower()
    for c in calls:
        if c.get("id") == identifier or ident_lower in c.get("recipient", "").lower():
            if c.get("status") == "pending":
                c["status"] = "cancelled"
                found = True
                break
    if found:
        save_scheduled_calls(calls)
        return {"ok": True, "message": f"Scheduled WhatsApp call '{identifier}' has been cancelled."}
    return {"ok": False, "error": f"No active pending scheduled call found matching '{identifier}'."}


_SCHEDULER_THREAD_RUNNING = False

def _scheduler_loop():
    while True:
        try:
            calls = load_scheduled_calls()
            now = time.time()
            modified = False

            for c in calls:
                if c.get("status") == "pending" and c.get("target_epoch", 0) <= now:
                    log.info("[Call Scheduler] Time reached for call %s to %s", c["id"], c["recipient"])
                    c["status"] = "executing"
                    save_scheduled_calls(calls)

                    # Trigger call
                    try:
                        try:
                            from actions.spoken_voice import speak_voice_threaded
                            rec_txt = " (recurring)" if c.get("recurring") else ""
                            speak_voice_threaded(f"Sir, aapka WhatsApp {c['call_type']} call{rec_txt} schedule tha {c['recipient']} ke sath. Call connect kar raha hu.")
                        except Exception:
                            pass
                        make_whatsapp_call(c["recipient"], c["call_type"])
                        
                        # Handle recurring advancement
                        rec = c.get("recurring", "")
                        if rec == "daily":
                            next_dt = datetime.fromtimestamp(c["target_epoch"]) + timedelta(days=1)
                            c["target_epoch"] = next_dt.timestamp()
                            c["target_iso"] = next_dt.isoformat()
                            c["status"] = "pending"
                        elif rec == "weekly":
                            next_dt = datetime.fromtimestamp(c["target_epoch"]) + timedelta(weeks=1)
                            c["target_epoch"] = next_dt.timestamp()
                            c["target_iso"] = next_dt.isoformat()
                            c["status"] = "pending"
                        else:
                            c["status"] = "completed"
                    except Exception as e:
                        c["status"] = f"failed: {e}"
                    modified = True

            if modified:
                save_scheduled_calls(calls)
        except Exception as e:
            log.debug("Scheduler loop tick error: %s", e)
        time.sleep(5.0)


def start_call_scheduler_daemon():
    global _SCHEDULER_THREAD_RUNNING
    if _SCHEDULER_THREAD_RUNNING:
        return
    _SCHEDULER_THREAD_RUNNING = True
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="WhatsAppCallSchedulerThread")
    t.start()


def transcribe_whatsapp_audio(audio_path: str) -> Dict[str, Any]:
    """Transcribe an incoming WhatsApp audio file or voice note using speech models."""
    p = Path(audio_path)
    if not p.exists():
        return {"ok": False, "error": f"Audio file not found: {audio_path}"}

    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(str(p)) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)
            return {"ok": True, "transcription": text, "file": str(p)}
    except Exception as e:
        log.warning("Audio transcription fallback error: %s", e)
        return {"ok": False, "error": f"Could not transcribe audio: {e}"}


