"""
actions/android_manager.py — Autonomous Android Device Control Engine for Prime AI.
Inherits the Tony Stark / Ultron "A Voice with Hands" architecture:
- Connects to Android devices wirelessly over ADB (Wi-Fi or USB)
- Device status: battery, thermals, lock screen state, notifications
- Screen unlock & power management
- App launcher & navigation (YouTube, WhatsApp, Spotify, Camera, Settings, etc.)
- Touch, typing, media control, calls, and SMS
- Auto-installs Android platform-tools if not found on Windows
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("prime.android")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = PROJECT_ROOT / "bin" / "platform-tools"
GOOGLE_PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

APP_PACKAGE_MAP: Dict[str, Dict[str, str]] = {
    "youtube": {"pkg": "com.google.android.youtube", "label": "YouTube"},
    "whatsapp": {"pkg": "com.whatsapp", "label": "WhatsApp"},
    "spotify": {"pkg": "com.spotify.music", "label": "Spotify"},
    "chrome": {"pkg": "com.android.chrome", "label": "Google Chrome"},
    "camera": {"action": "android.media.action.STILL_IMAGE_CAMERA", "label": "Camera"},
    "maps": {"pkg": "com.google.android.apps.maps", "label": "Google Maps"},
    "instagram": {"pkg": "com.instagram.android", "label": "Instagram"},
    "settings": {"pkg": "com.android.settings", "label": "Settings"},
    "phone": {"action": "android.intent.action.DIAL", "label": "Phone Dialer"},
    "photos": {"pkg": "com.google.android.apps.photos", "label": "Google Photos"},
    "files": {"pkg": "com.google.android.documentsui", "label": "Files"},
    "calculator": {"pkg": "com.google.android.calculator", "label": "Calculator"},
    "telegram": {"pkg": "org.telegram.messenger", "label": "Telegram"},
}


class AndroidManager:
    """Universal Android Device Controller via ADB."""

    def __init__(self):
        self._adb_path: Optional[str] = None
        self._active_serial: Optional[str] = None
        self.default_port: int = 5555
        self._resolve_adb()

    def _resolve_adb(self) -> Optional[str]:
        """Locate adb.exe executable on the host system."""
        # 1. System PATH
        which = shutil.which("adb")
        if which:
            self._adb_path = which
            return which

        # 2. Local project bin
        local_adb = BIN_DIR / "adb.exe"
        if local_adb.exists():
            self._adb_path = str(local_adb)
            return self._adb_path

        # 3. Standard Android SDK locations
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            Path("C:/platform-tools/adb.exe"),
            Path.home() / "platform-tools" / "adb.exe",
        ]
        for c in candidates:
            if c.exists():
                self._adb_path = str(c)
                return self._adb_path

        self._adb_path = None
        return None

    def ensure_adb(self) -> Tuple[bool, str]:
        """Ensure ADB executable is available, downloading from Google if missing."""
        if self._adb_path and Path(self._adb_path).exists():
            return True, self._adb_path

        # Attempt auto-downloading Google official platform-tools
        log.info("ADB not detected. Downloading official Android platform-tools...")
        try:
            BIN_DIR.parent.mkdir(parents=True, exist_ok=True)
            zip_dest = BIN_DIR.parent / "platform-tools.zip"

            req = urllib.request.Request(GOOGLE_PLATFORM_TOOLS_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(zip_dest, "wb") as out_f:
                shutil.copyfileobj(resp, out_f)

            with zipfile.ZipFile(zip_dest, "r") as z:
                z.extractall(BIN_DIR.parent)

            if zip_dest.exists():
                zip_dest.unlink()

            local_adb = BIN_DIR / "adb.exe"
            if local_adb.exists():
                self._adb_path = str(local_adb)
                log.info("Successfully installed Android platform-tools at %s", self._adb_path)
                return True, self._adb_path
        except Exception as e:
            log.warning("Could not auto-download platform-tools: %s", e)

        return False, "ADB executable not found. Enable USB debugging on your Android phone and install platform-tools."

    def run_adb(self, *args: str, timeout: int = 15) -> Dict[str, Any]:
        """Execute an ADB command against active or connected device."""
        ok, path_or_err = self.ensure_adb()
        if not ok:
            return {"ok": False, "error": path_or_err}

        cmd = [self._adb_path]
        if self._active_serial and args and args[0] not in ("devices", "connect", "disconnect", "kill-server", "start-server"):
            cmd.extend(["-s", self._active_serial])
        cmd.extend(args)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "output": stdout or stderr,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"ADB command timed out after {timeout}s."}
        except Exception as e:
            return {"ok": False, "error": f"ADB execution failed: {e}"}

    def list_devices(self) -> Dict[str, Any]:
        """List all connected Android devices (USB and Wi-Fi)."""
        res = self.run_adb("devices", "-l")
        if not res["ok"]:
            return res

        devices = []
        for line in res.get("stdout", "").splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            serial = parts[0]
            status = parts[1] if len(parts) > 1 else "unknown"
            info = " ".join(parts[2:]) if len(parts) > 2 else ""
            devices.append({"serial": serial, "status": status, "info": info})

        if devices and not self._active_serial:
            self._active_serial = devices[0]["serial"]

        return {
            "ok": True,
            "count": len(devices),
            "devices": devices,
            "active_device": self._active_serial,
            "connected": len(devices) > 0 and any(d["status"] == "device" for d in devices),
        }

    def connect_device(self, host: str, port: int = 5555) -> Dict[str, Any]:
        """Connect to an Android device over local Wi-Fi (e.g., 192.168.1.100:5555)."""
        clean_host = host.strip()
        if ":" in clean_host:
            target = clean_host
        else:
            target = f"{clean_host}:{port}"

        res = self.run_adb("connect", target)
        out = res.get("output", "")
        connected = "connected to" in out.lower() and "unable" not in out.lower()
        if connected:
            self._active_serial = target

        return {
            "ok": connected,
            "target": target,
            "message": out,
            "connected": connected,
        }

    def get_battery_status(self) -> Dict[str, Any]:
        """Get phone battery percentage, charging state, and thermals."""
        res = self.run_adb("shell", "dumpsys", "battery")
        if not res["ok"]:
            return res

        data: Dict[str, Any] = {"ok": True}
        text = res.get("stdout", "")
        for line in text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if k == "level":
                    data["level"] = int(v) if v.isdigit() else v
                elif k == "temperature":
                    data["temperature_c"] = round(int(v) / 10.0, 1) if v.isdigit() else v
                elif k == "status":
                    # 2: Charging, 3: Discharging, 5: Full
                    data["charging"] = (v == "2")
                    data["status"] = "Charging" if v == "2" else ("Full" if v == "5" else "Discharging")
                elif k == "AC powered":
                    data["ac_powered"] = (v == "true")
                elif k == "USB powered":
                    data["usb_powered"] = (v == "true")

        level = data.get("level", "Unknown")
        state = "Charging" if data.get("charging") else "Discharging"
        data["summary"] = f"Battery: {level}% ({state}, {data.get('temperature_c', '?')}°C)"
        return data

    def wake_and_unlock(self) -> Dict[str, Any]:
        """Wake up device screen and dismiss the lock screen."""
        # 1. Wake screen
        self.run_adb("shell", "input", "keyevent", "224")  # KEYCODE_WAKEUP
        time.sleep(0.3)
        # 2. Dismiss lockscreen / swipe up
        self.run_adb("shell", "input", "keyevent", "82")   # KEYCODE_MENU
        time.sleep(0.2)
        # 3. Supplemental swipe up from bottom to top
        self.run_adb("shell", "input", "swipe", "500", "1600", "500", "300", "250")
        return {"ok": True, "message": "Woke screen and dismissed lock screen on Android device, Sir."}

    def lock_screen(self) -> Dict[str, Any]:
        """Put Android screen to sleep."""
        self.run_adb("shell", "input", "keyevent", "26")   # KEYCODE_POWER
        return {"ok": True, "message": "Turned off Android device screen, Sir."}

    def open_app(self, app_name: str) -> Dict[str, Any]:
        """Open any application on Android by common name or package."""
        clean = app_name.lower().strip()
        info = APP_PACKAGE_MAP.get(clean)

        if info and "action" in info:
            res = self.run_adb("shell", "am", "start", "-a", info["action"])
            return {"ok": res["ok"], "message": f"Opened {info['label']} on your phone, Sir."}

        pkg = info["pkg"] if info else clean
        # Use Android monkey tool to launch default intent
        res = self.run_adb("shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1")
        label = info["label"] if info else pkg
        if "No activities found" in res.get("output", "") or not res["ok"]:
            # Fallback to am start
            res_am = self.run_adb("shell", "am", "start", "-n", f"{pkg}/.MainActivity")
            return {
                "ok": res_am["ok"],
                "message": f"Attempted to launch {label} on Android.",
                "details": res_am.get("output"),
            }

        return {"ok": True, "message": f"Opened {label} on your Android device, Sir."}

    def read_notifications(self, limit: int = 5) -> Dict[str, Any]:
        """Read recent incoming notifications (messages, alerts, OTPs) from phone."""
        res = self.run_adb("shell", "dumpsys", "notification", "--noredact")
        if not res["ok"]:
            return res

        text = res.get("stdout", "")
        # Extract notification titles and text
        notifications = []
        pattern = re.compile(r'NotificationRecord\{[^\}]+\}:[^\n]+\n\s+pkg=([\w\.]+)[^\n]+\n\s+tickerText=([^\n]*)')
        for match in pattern.finditer(text):
            pkg = match.group(1)
            ticker = match.group(2).strip()
            if ticker and ticker != "null":
                notifications.append({"package": pkg, "text": ticker})
            if len(notifications) >= limit:
                break

        if not notifications:
            # Fallback regex for standard text fields
            titles = re.findall(r'android.title=String \((.*?)\)', text)
            bodies = re.findall(r'android.text=String \((.*?)\)', text)
            for t, b in zip(titles[:limit], bodies[:limit]):
                if t and b:
                    notifications.append({"title": t, "body": b})

        count = len(notifications)
        summary = f"Retrieved {count} recent notifications from phone." if count > 0 else "No active notifications on phone."
        return {
            "ok": True,
            "count": count,
            "notifications": notifications,
            "summary": summary,
        }

    def tap(self, x: int, y: int) -> Dict[str, Any]:
        """Tap specific screen coordinates on Android."""
        res = self.run_adb("shell", "input", "tap", str(x), str(y))
        return {"ok": res["ok"], "message": f"Tapped screen at ({x}, {y})."}

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> Dict[str, Any]:
        """Swipe across screen coordinates on Android."""
        res = self.run_adb("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        return {"ok": res["ok"], "message": f"Swiped from ({x1}, {y1}) to ({x2}, {y2})."}

    def type_text(self, text: str) -> Dict[str, Any]:
        """Type text into active focused input field on Android."""
        safe_text = re.sub(r'[^\w\s\.,!\?@_-]', '', text).replace(" ", "%s")
        res = self.run_adb("shell", "input", "text", safe_text)
        return {"ok": res["ok"], "message": f"Typed '{text}' on Android."}

    def media_control(self, action: str) -> Dict[str, Any]:
        """Control media playback or volume on Android."""
        act = action.lower().strip()
        keycodes = {
            "play_pause": "85",
            "play": "126",
            "pause": "127",
            "next": "87",
            "prev": "88",
            "previous": "88",
            "volume_up": "24",
            "volume_down": "25",
            "mute": "164",
            "home": "3",
            "back": "4",
        }
        code = keycodes.get(act, "85")
        res = self.run_adb("shell", "input", "keyevent", code)
        return {"ok": res["ok"], "message": f"Triggered Android {act} (keycode {code})."}

    def make_call(self, phone_number: str) -> Dict[str, Any]:
        """Dial a phone number directly on the Android phone."""
        clean_num = re.sub(r'[^\d\+]', '', phone_number)
        res = self.run_adb("shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{clean_num}")
        return {"ok": res["ok"], "message": f"Initiated phone call to {clean_num} on your Android device."}


# Process-wide singleton
android_manager = AndroidManager()
