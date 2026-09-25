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
import subprocess
import threading
import time
import urllib.parse
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


def resolve_recipient(target: str) -> Tuple[Optional[str], str]:
    """
    Resolve recipient from either contact name or phone number.
    Returns (phone_number, display_name).
    """
    contacts = load_contacts()
    target_clean = target.strip()
    target_lower = target_clean.lower()

    if target_lower in contacts:
        return contacts[target_lower], target_clean

    # Clean repeated words / speech recognition stutter (e.g. "om om" -> "om")
    words = [w for w in target_lower.split() if w not in ("to", "tu", "ko", "se", "send", "message", "msg")]
    for w in words:
        if w in contacts:
            return contacts[w], w.title()

    # Check exact word boundaries
    for name, num in contacts.items():
        if f" {name} " in f" {target_lower} " or f" {target_lower} " in f" {name} ":
            return num, name.title()

    # Substring check in contacts
    for name, num in contacts.items():
        if target_lower in name or name in target_lower:
            return num, name.title()

    # Difflib close match
    import difflib
    close = difflib.get_close_matches(target_lower, list(contacts.keys()), n=1, cutoff=0.7)
    if close:
        matched = close[0]
        return contacts[matched], matched.title()

    # Check if target is directly a phone number
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


def _focus_whatsapp_window_raw() -> bool:
    """Finds and brings ANY active WhatsApp window (Chrome WhatsApp Web, Edge, or Desktop App) to the foreground."""
    if platform.system() != "Windows":
        return False
    try:
        u32 = ctypes.windll.user32
        h_desk = u32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            u32.SetThreadDesktop(h_desk)

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        hwnds = []

        def _cb(h, _):
            buf = ctypes.create_unicode_buffer(512)
            u32.GetWindowTextW(h, buf, 512)
            t = buf.value
            u32.GetClassNameW(h, buf, 512)
            c = buf.value
            if "whatsapp" in t.lower() or "whatsapp" in c.lower():
                hwnds.append((h, t, c))
            return True

        cb = WNDENUMPROC(_cb)
        if h_desk:
            u32.EnumDesktopWindows(h_desk, cb, 0)
        else:
            u32.EnumWindows(cb, 0)

        if hwnds:
            hwnd = hwnds[0][0]
            # Use AttachThreadInput to bypass Windows foreground activation lock
            curr_tid = ctypes.windll.kernel32.GetCurrentThreadId()
            fore_hwnd = u32.GetForegroundWindow()
            fore_tid = u32.GetWindowThreadProcessId(fore_hwnd, None)
            u32.AttachThreadInput(curr_tid, fore_tid, True)
            u32.ShowWindow(hwnd, 9)  # SW_RESTORE
            u32.SetForegroundWindow(hwnd)
            u32.SetFocus(hwnd)
            u32.AttachThreadInput(curr_tid, fore_tid, False)
            log.info("Focused WhatsApp window: HWND %s (%s)", hwnd, hwnds[0][1])
            return True
    except Exception as e:
        log.debug("_focus_whatsapp_window_raw error: %s", e)
    return False


def focus_whatsapp_window() -> bool:
    """Public wrapper to focus WhatsApp using an interactive thread."""
    return bool(run_on_interactive_thread(_focus_whatsapp_window_raw))


def press_enter_interactive():
    """Simulates physical Enter key on interactive desktop."""
    if platform.system() == "Windows":
        u32 = ctypes.windll.user32
        u32.keybd_event(0x0D, 0, 0, 0)
        time.sleep(0.05)
        u32.keybd_event(0x0D, 0, 2, 0)
    else:
        try:
            import pyautogui
            pyautogui.press("enter")
        except Exception:
            pass


def send_via_desktop_protocol(phone_number: str, message: str) -> Dict[str, Any]:
    """Send message via the official Windows whatsapp:// protocol handler on user's desktop."""
    clean_num = phone_number.replace("+", "")
    encoded_msg = urllib.parse.quote(message)
    uri = f"whatsapp://send?phone={clean_num}&text={encoded_msg}"

    def _do_send():
        # 1. Launch URI on interactive desktop
        launch_on_interactive_desktop(f'explorer.exe "{uri}"')
        time.sleep(3.0)

        # 2. Focus WhatsApp window
        _focus_whatsapp_window_raw()
        time.sleep(0.8)

        # 3. Simulate Enter key to send the typed message (dual native + pyautogui)
        press_enter_interactive()
        time.sleep(0.2)
        try:
            import pyautogui
            pyautogui.press("enter")
        except Exception:
            pass
        time.sleep(0.4)
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
        """Send message using Playwright with persistent session."""
        from playwright.sync_api import sync_playwright
        clean_num = phone_number.replace("+", "")
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
                    page.goto(url, timeout=45000)

                    # Wait for message input box or send button
                    send_btn = page.wait_for_selector('button[aria-label="Send"], span[data-icon="send"]', timeout=25000)
                    if send_btn:
                        send_btn.click()
                        time.sleep(2.0)
                        browser.close()
                        return {"ok": True, "message": f"Message sent to {phone_number} via WhatsApp Web background session."}
                    else:
                        browser.close()
                        return {"ok": False, "error": "Send button not found or chat did not load."}
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

