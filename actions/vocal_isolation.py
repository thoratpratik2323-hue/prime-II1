"""
actions/vocal_isolation.py
Advanced Vocal Isolation & Noise Suppression Pre-Processing for Prime AI.
Filters out background ambient noise (fan hum, AC, TV spill, street noise)
from microphone audio streams or reference voice cloning samples using
spectral gating, butterworth bandpass filtering, and dynamic thresholding.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

log = logging.getLogger("prime.vocal_isolation")

_VOCAL_ISOLATION_ENABLED = True
_ISOLATION_SENSITIVITY = 0.75  # 0.0 (subtle) to 1.0 (aggressive)


def get_vocal_isolation_state() -> Dict[str, Any]:
    """Return the current active vocal isolation configuration."""
    return {
        "ok": True,
        "enabled": _VOCAL_ISOLATION_ENABLED,
        "sensitivity": _ISOLATION_SENSITIVITY,
    }


def set_vocal_isolation_state(enabled: bool, sensitivity: float = 0.75) -> Dict[str, Any]:
    """Toggle or tune vocal isolation and noise suppression."""
    global _VOCAL_ISOLATION_ENABLED, _ISOLATION_SENSITIVITY
    _VOCAL_ISOLATION_ENABLED = bool(enabled)
    _ISOLATION_SENSITIVITY = max(0.1, min(1.0, float(sensitivity)))
    log.info(
        "Vocal Isolation %s (sensitivity=%.2f)",
        "ENABLED" if _VOCAL_ISOLATION_ENABLED else "DISABLED",
        _ISOLATION_SENSITIVITY,
    )
    return {
        "ok": True,
        "enabled": _VOCAL_ISOLATION_ENABLED,
        "sensitivity": _ISOLATION_SENSITIVITY,
        "message": f"Vocal Isolation {'ENABLED' if _VOCAL_ISOLATION_ENABLED else 'DISABLED'} (sensitivity={_ISOLATION_SENSITIVITY:.2f}).",
    }


def apply_vocal_isolation(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    sensitivity: Optional[float] = None,
) -> np.ndarray:
    """
    Applies high-pass (85Hz), low-pass (7600Hz), and spectral noise gating
    to isolate human vocal frequencies and suppress ambient background hiss/hum.
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    if not _VOCAL_ISOLATION_ENABLED and sensitivity is None:
        return audio_data

    sens = _ISOLATION_SENSITIVITY if sensitivity is None else max(0.1, min(1.0, float(sensitivity)))

    try:
        import scipy.signal as signal

        orig_dtype = audio_data.dtype
        # Convert to float [-1.0, 1.0]
        if orig_dtype == np.int16:
            data = audio_data.astype(np.float32) / 32768.0
        elif orig_dtype == np.int32:
            data = audio_data.astype(np.float32) / 2147483648.0
        else:
            data = audio_data.astype(np.float32)

        nyquist = 0.5 * max(8000, sample_rate)

        # 1. Bandpass Filter: 85 Hz (eliminate sub-bass rumbling / fan) to 7500 Hz (speech band)
        low_cut = max(20.0, min(85.0, nyquist - 100.0))
        high_cut = max(low_cut + 100.0, min(7500.0, nyquist - 50.0))
        b_bp, a_bp = signal.butter(2, [low_cut / nyquist, high_cut / nyquist], btype="bandpass")
        filtered = signal.lfilter(b_bp, a_bp, data, axis=0)

        # 2. Dynamic Noise Gate
        # Estimate noise floor using 15th percentile energy of windowed frames
        frame_len = max(64, int(sample_rate * 0.02))  # 20ms frames
        num_frames = len(filtered) // frame_len
        if num_frames > 2:
            frames = filtered[: num_frames * frame_len].reshape(num_frames, frame_len)
            frame_energy = np.mean(frames**2, axis=1)
            noise_floor_energy = np.percentile(frame_energy, 15)
            # Threshold scales with sensitivity
            threshold = noise_floor_energy * (1.5 + sens * 2.5)

            # Apply soft gain mask
            gain = np.ones(num_frames, dtype=np.float32)
            mask_below = frame_energy < threshold
            attenuation = 1.0 - (sens * 0.85)  # 0.15 to 0.9 gain reduction
            gain[mask_below] = attenuation

            # Smooth gain curve (exponential moving average)
            smoothed_gain = np.empty_like(gain)
            smoothed_gain[0] = gain[0]
            alpha = 0.3
            for i in range(1, num_frames):
                smoothed_gain[i] = alpha * gain[i] + (1 - alpha) * smoothed_gain[i - 1]

            # Upsample gain to full signal length
            full_gain = np.repeat(smoothed_gain, frame_len)
            filtered[: len(full_gain)] *= full_gain

        # 3. Peak Normalization and Conversion back to original dtype
        max_val = np.max(np.abs(filtered))
        if max_val > 1.0:
            filtered = filtered / max_val

        if orig_dtype == np.int16:
            return np.clip(filtered * 32767.0, -32768.0, 32767.0).astype(np.int16)
        elif orig_dtype == np.int32:
            return np.clip(filtered * 2147483647.0, -2147483648.0, 2147483647.0).astype(np.int32)
        return filtered.astype(orig_dtype)

    except Exception as e:
        log.warning("Vocal isolation failed (%s), returning original audio", e)
        return audio_data


def clean_audio_file(input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Cleans a WAV audio file by removing background noise, fan hum, and non-vocal frequencies.
    Ideal for preparing reference voice samples before voice cloning.
    """
    p = Path(input_path)
    if not p.exists():
        return {"ok": False, "error": f"Audio file not found: {input_path}"}

    try:
        import wave

        with wave.open(str(p), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_frames = wf.readframes(n_frames)

        if sampwidth == 2:
            dtype = np.int16
        elif sampwidth == 4:
            dtype = np.int32
        else:
            dtype = np.int16

        arr = np.frombuffer(raw_frames, dtype=dtype)
        if n_channels == 2:
            arr = arr.reshape(-1, 2)

        cleaned_arr = apply_vocal_isolation(arr, sample_rate=framerate)

        out_path = Path(output_path) if output_path else p.with_name(f"{p.stem}_cleaned{p.suffix}")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(out_path), "wb") as out_wf:
            out_wf.setnchannels(n_channels)
            out_wf.setsampwidth(sampwidth)
            out_wf.setframerate(framerate)
            out_wf.writeframes(cleaned_arr.tobytes())

        return {
            "ok": True,
            "original_path": str(p),
            "cleaned_path": str(out_path),
            "sample_rate": framerate,
            "channels": n_channels,
            "message": f"Successfully cleaned audio with vocal isolation: {out_path.name}",
        }
    except Exception as e:
        log.error("Failed to clean audio file: %s", e)
        return {"ok": False, "error": f"Failed to clean audio file: {e}"}
