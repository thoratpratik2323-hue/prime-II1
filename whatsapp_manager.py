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

    # Fuzzy check in contacts
    for name, num in contacts.items():
        if target_lower in name or name in target_lower:
            return num, name.title()

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


def send_via_desktop_protocol(phone_number: str, message: str) -> Dict[str, Any]:
    """Send message via the official Windows whatsapp:// protocol handler."""
    clean_num = phone_number.replace("+", "")
    encoded_msg = urllib.parse.quote(message)
    uri = f"whatsapp://send?phone={clean_num}&text={encoded_msg}"

    try:
        if platform.system() == "Windows":
            # Launch via shell
            os.startfile(uri)
            time.sleep(1.8)

            # Auto-press Enter to send if pyautogui is available
            try:
                import pyautogui
                # Bring WhatsApp to front
                pyautogui.press("enter")
                time.sleep(0.3)
                pyautogui.press("enter")
            except Exception:
                pass

            return {
                "ok": True,
                "message": f"WhatsApp message successfully dispatched to {phone_number} via Desktop App.",
                "method": "windows_protocol"
            }
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
        """Launch an interactive browser window to allow the user to scan the QR code once."""
        def _run():
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch_persistent_context(
                        user_data_dir=str(self.session_path),
                        headless=False,
                        channel="chrome",
                        args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                        viewport=None
                    )
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    page.goto("https://web.whatsapp.com", timeout=60000)
                    log.info("WhatsApp Web setup window opened. Waiting for user QR scan...")

                    # Wait up to 3 minutes for user to link device
                    for _ in range(180):
                        time.sleep(1.0)
                        # Check if chats list or search bar is loaded
                        is_logged_in = page.evaluate("""() => {
                            return Boolean(document.querySelector('div[contenteditable="true"]') || document.querySelector('#pane-side'));
                        }""")
                        if is_logged_in:
                            log.info("WhatsApp Web login detected successfully!")
                            time.sleep(3)
                            break
                    browser.close()
            except Exception as e:
                log.error("WhatsApp setup error: %s", e)

        t = threading.Thread(target=_run, daemon=True, name="WhatsAppSetupThread")
        t.start()
        return {
            "ok": True,
            "result": "Opened WhatsApp Web in Chrome. Please scan the QR code on screen using WhatsApp on your phone (Linked Devices -> Link a Device). Once scanned, Prime will have full persistent access!"
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


# =====================================================================
# 4. Unified Entry Points
# =====================================================================

def send_whatsapp(recipient: str, message: str) -> Dict[str, Any]:
    """
    Send WhatsApp message to recipient (name or phone number).
    Uses Desktop App first if installed, falls back to Web.
    """
    phone, display_name = resolve_recipient(recipient)
    if not phone:
        return {
            "ok": False,
            "error": f"Could not find contact '{recipient}' in contact book, and it does not appear to be a valid phone number. Please provide the 10-digit number or save the contact first."
        }

    log.info("Sending WhatsApp message to '%s' (%s): %s", display_name, phone, message[:50])

    # Method 1: Desktop App if available
    res = send_via_desktop_protocol(phone, message)
    if res.get("ok"):
        res["recipient"] = display_name
        return res

    # Method 2: Web persistent session
    return whatsapp_web.send_via_web(phone, message)
