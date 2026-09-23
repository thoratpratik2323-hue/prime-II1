"""
Screenshot & screen-reading: capture, save, OCR, and read on-screen text.

  takeScreenshot    -> capture full screen, return metadata (+ small base64)
  saveScreenshot    -> capture & write to a file under the Screenshots folder
  analyzeScreenshot-> capture, run OCR (pytesseract), return extracted text
  readScreen        -> OCR the active window region + name the active window

OCR requires the Tesseract OCR engine + the pytesseract wrapper. If either is
missing, the OCR tools return a graceful 'unavailable' message instead of
crashing; non-OCR capture still works.
"""

from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .registry import ToolError, register

SCREENSHOTS_DIR = Path(os.path.expanduser("~")) / "Pictures" / "PrimeScreenshots"


def _capture() -> "Any":
    """Capture the full virtual screen as a PIL Image with multiple fallbacks."""
    errors = []
    # 1. PIL ImageGrab with all_screens
    try:
        from PIL import ImageGrab
        return ImageGrab.grab(all_screens=True)
    except Exception as e:
        errors.append(f"ImageGrab(all): {e}")

    # 2. PIL ImageGrab primary screen
    try:
        from PIL import ImageGrab
        return ImageGrab.grab(all_screens=False)
    except Exception as e:
        errors.append(f"ImageGrab(primary): {e}")

    # 3. pyautogui screenshot
    try:
        import pyautogui
        return pyautogui.screenshot()
    except Exception as e:
        errors.append(f"pyautogui: {e}")

    # 4. MSS capture
    try:
        import mss
        from PIL import Image
        with mss.MSS() as sct:
            sct_img = sct.grab(sct.monitors[0])
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as e:
        errors.append(f"mss: {e}")

    raise ToolError(f"Screen capture currently unavailable in this desktop session ({errors[0] if errors else 'no grabber'}).")


def _capture_region(bbox):
    try:
        from PIL import ImageGrab
        return ImageGrab.grab(bbox=bbox, all_screens=False)
    except Exception:
        # Fallback to cropping full capture
        try:
            full = _capture()
            return full.crop(bbox)
        except Exception as e:
            raise ToolError(f"Region capture failed: {e}")


def _active_window_bbox():
    """Return (left, top, right, bottom) of the foreground window, or None."""
    try:
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        rect = win32gui.GetWindowRect(hwnd)  # (l, t, r, b)
        return rect
    except Exception:
        return None


def _active_window_title() -> str:
    try:
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd) if hwnd else ""
    except Exception:
        return ""


def _image_to_b64(img, fmt="PNG", quality=70) -> str:
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
    else:
        img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _image_size_kb(img) -> int:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return len(buf.getvalue()) // 1024


def _run_ocr(img) -> str:
    try:
        import pytesseract
    except ImportError:
        raise ToolError(
            "OCR unavailable: the 'pytesseract' package is not installed."
        )
    # Ensure the Tesseract binary is discoverable.
    exe = os.environ.get("TESSERACT_PATH") or _find_tesseract_exe()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe
    try:
        return pytesseract.image_to_string(img)
    except Exception as e:  # noqa: BLE001
        raise ToolError(
            "OCR failed (is the Tesseract engine installed?). Detail: " + str(e)
        )


def _find_tesseract_exe() -> Optional[str]:
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _trim_ocr(text: str, max_chars: int = 1500) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[:max_chars] + "…"
    return out


@register("takeScreenshot")
def take_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
    img = _capture()
    include_image = bool(args.get("include_image", False))
    result: Dict[str, Any] = {
        "result": f"Captured screen ({img.width}x{img.height}).",
        "width": img.width,
        "height": img.height,
    }
    if include_image:
        # Downscale + JPEG to keep payload small for the WS bridge.
        max_dim = int(args.get("max_dim", 1280))
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img_small = img.resize(
                (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
            )
        else:
            img_small = img
        result["image_base64"] = _image_to_b64(img_small, fmt="JPEG", quality=60)
        result["image_mime"] = "image/jpeg"
    return result


@register("saveScreenshot")
def save_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
    img = _capture()
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = args.get("name")
    fname = f"{name}-{stamp}.png" if name else f"screenshot-{stamp}.png"
    out_path = SCREENSHOTS_DIR / fname
    img.save(out_path, format="PNG")
    return {"result": f"Saved screenshot to {out_path}.", "path": str(out_path)}


@register("analyzeScreenshot")
def analyze_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
    img = _capture()
    try:
        text = _run_ocr(img)
    except ToolError as e:
        return {"result": f"Screenshot captured, but OCR unavailable: {e.message}"}
    return {
        "result": "Screenshot analyzed via OCR.",
        "text": _trim_ocr(text, int(args.get("max_chars", 1500))),
    }


@register("readScreen")
def read_screen(args: Dict[str, Any]) -> Dict[str, Any]:
    """OCR the active window and report its title + visible text."""
    title = _active_window_title()
    bbox = _active_window_bbox()
    if bbox:
        try:
            img = _capture_region(bbox)
        except ToolError:
            img = _capture()
    else:
        img = _capture()
    try:
        text = _run_ocr(img)
    except ToolError as e:
        return {
            "result": f"Active window: {title or 'unknown'}. OCR unavailable: {e.message}",
            "active_window": title,
        }
    return {
        "result": f"Active window '{title or 'unknown'}' contains readable text.",
        "active_window": title,
        "text": visible,
    }


@register("analyzeScreenWithAI")
def analyze_screen_with_ai(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Take a live screenshot and analyze it with Gemini Multimodal Vision.
    Can answer questions about what is on screen, read error dialogues, inspect code,
    find buttons to click, or describe open applications.
    Args:
        prompt (str, optional): Specific question or instruction for analyzing the screen.
            Default: "Describe what is currently visible on the screen, identify any open applications, and locate key UI elements or errors."
    """
    args = args or {}
    user_prompt = args.get("prompt", "Describe what is on screen, identify active apps, and locate key buttons or errors.")

    try:
        img = _capture()
    except ToolError as e:
        return {"result": f"Could not capture screen: {e.message}"}

    # Compress to JPEG buffer
    try:
        from io import BytesIO
        buf = BytesIO()
        # Resize if very large for faster upload
        w, h = img.size
        if w > 1920:
            scale = 1920 / w
            img = img.resize((int(w * scale), int(h * scale)))
        img.convert("RGB").save(buf, format="JPEG", quality=75)
        img_bytes = buf.getvalue()
    except Exception as e:
        return {"result": f"Failed to prepare screen image buffer: {e}"}

    # Attempt Gemini Vision analysis
    try:
        from config import config
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                user_prompt,
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            ],
        )
        return {
            "result": f"Screen Vision Analysis:\n{response.text}",
            "analysis": response.text,
            "dimensions": f"{img.size[0]}x{img.size[1]}",
        }
    except Exception as e:
        # Fallback to OCR if vision fails
        try:
            ocr_text = _run_ocr(img)
            return {
                "result": f"Vision API unavailable ({e}). Extracted OCR text:\n{_trim_ocr(ocr_text, 1200)}",
                "ocr_fallback": True,
            }
        except Exception:
            return {"result": f"Screen captured but vision analysis encountered an error: {e}"}


__all__ = [
    "take_screenshot",
    "save_screenshot",
    "analyze_screenshot",
    "read_screen",
    "analyze_screen_with_ai",
]

