"""
Video Frame Extractor & Visual Analysis Engine for Prime AI.
Allows extracting high-resolution image frames from local MP4/MKV video files,
auto-discovering videos across user libraries, and exporting frames for inspection.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.video_processor")

VIDEOS_DIR = Path(os.path.expanduser("~")) / "Videos"
DEFAULT_OUTPUT_DIR = Path(os.path.expanduser("~")) / "Pictures" / "ExtractedFrames"


def find_video_file(query_or_path: str) -> Optional[Path]:
    """Find video file from absolute path or loose search query in user directories."""
    p = Path(query_or_path)
    if p.exists() and p.is_file():
        return p

    clean = query_or_path.lower().strip()
    search_dirs = [
        VIDEOS_DIR,
        Path(os.path.expanduser("~")) / "Downloads",
        Path("C:/My Projects/Personal Projects"),
    ]

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for ext in ("*.mp4", "*.mkv", "*.avi", "*.mov"):
            for f in s_dir.rglob(ext):
                if clean in f.name.lower() or clean in f.stem.lower():
                    return f

    return None


def extract_video_frames(
    video_path: str,
    output_dir: Optional[str] = None,
    interval_seconds: float = 2.0,
    max_frames: int = 30
) -> Dict[str, Any]:
    """
    Extract key image frames from a video file at regular time intervals using OpenCV.
    """
    target = find_video_file(video_path)
    if not target:
        return {"ok": False, "error": f"Could not locate video file matching '{video_path}'."}

    try:
        import cv2
    except ImportError:
        return {"ok": False, "error": "OpenCV (cv2) is not installed."}

    cap = cv2.VideoCapture(str(target))
    if not cap.isOpened():
        return {"ok": False, "error": f"Failed to open video file: {target}"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0

    frame_interval = max(1, int(fps * interval_seconds))

    out_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR / target.stem
    out_path.mkdir(parents=True, exist_ok=True)

    extracted_files: List[str] = []
    frame_idx = 0
    saved_count = 0

    while cap.isOpened() and saved_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp_sec = round(frame_idx / fps, 2)
            fname = f"frame_{saved_count + 1:03d}_{timestamp_sec}s.jpg"
            fpath = out_path / fname
            cv2.imwrite(str(fpath), frame)
            extracted_files.append(str(fpath))
            saved_count += 1

        frame_idx += 1

    cap.release()

    return {
        "ok": True,
        "video_file": str(target),
        "duration_seconds": round(duration_sec, 2),
        "fps": round(fps, 2),
        "total_frames_in_video": total_frames,
        "frames_extracted": saved_count,
        "output_directory": str(out_path),
        "extracted_images": extracted_files
    }


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get metadata for a video file (resolution, duration, fps)."""
    target = find_video_file(video_path)
    if not target:
        return {"ok": False, "error": f"Video '{video_path}' not found."}

    try:
        import cv2
        cap = cv2.VideoCapture(str(target))
        if not cap.isOpened():
            return {"ok": False, "error": f"Failed to open {target}"}

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()

        return {
            "ok": True,
            "filename": target.name,
            "path": str(target),
            "size_mb": round(target.stat().st_size / (1024 * 1024), 2),
            "duration_seconds": round(duration, 2),
            "resolution": f"{width}x{height}",
            "fps": round(fps, 2),
            "total_frames": total_frames
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to inspect video: {e}"}
