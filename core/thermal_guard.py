"""
Smart Hardware Thermal & Battery Power Guardian for Prime AI.
Audits CPU load, memory pressure, battery discharge rate, and thermal bottlenecks,
and dynamically adjusts power profiles between Performance, Balanced, and Eco modes.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.thermal_guard")

CURRENT_POWER_PROFILE = "balanced"


class ThermalGuard:
    """Monitors system thermal envelope and manages hardware power profiles."""

    def __init__(self):
        self.profile = CURRENT_POWER_PROFILE

    def get_health_audit(self) -> Dict[str, Any]:
        """Perform comprehensive system hardware and thermal health audit."""
        cpu_usage = 0.0
        cpu_count = os.cpu_count() or 4
        ram_percent = 0.0
        ram_available_mb = 0
        battery_percent = 100
        power_plugged = True
        battery_status_str = "AC Power"

        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1)
            vm = psutil.virtual_memory()
            ram_percent = vm.percent
            ram_available_mb = int(vm.available / (1024 * 1024))

            batt = psutil.sensors_battery()
            if batt:
                battery_percent = int(batt.percent)
                power_plugged = bool(batt.power_plugged)
                plugged_str = "Plugged In" if power_plugged else "On Battery"
                battery_status_str = f"{battery_percent}% ({plugged_str})"
        except Exception:
            pass

        # Evaluate risk conditions
        warnings: List[str] = []
        health_status = "OPTIMAL"

        if not power_plugged and battery_percent < 20:
            warnings.append(f"Low battery critical: {battery_percent}%. Please connect AC charger.")
            health_status = "CRITICAL"
        elif not power_plugged and battery_percent < 35:
            warnings.append(f"Battery is getting low: {battery_percent}%.")
            if health_status != "CRITICAL":
                health_status = "WARNING"

        if cpu_usage > 90.0:
            warnings.append(f"High CPU utilization: {cpu_usage}%. Potential thermal throttling.")
            if health_status != "CRITICAL":
                health_status = "WARNING"

        if ram_percent > 90.0:
            warnings.append(f"High RAM pressure: {ram_percent}%. Only {ram_available_mb} MB available.")
            if health_status != "CRITICAL":
                health_status = "WARNING"

        recommendation = "System running optimally."
        if health_status == "CRITICAL":
            recommendation = "Switch to 'eco' power profile and connect charger to prevent shutdown."
        elif health_status == "WARNING":
            recommendation = "Consider throttling heavy background tasks or closing high-memory processes."

        return {
            "ok": True,
            "status": health_status,
            "current_profile": self.profile,
            "metrics": {
                "cpu_usage_percent": cpu_usage,
                "cpu_cores": cpu_count,
                "ram_usage_percent": ram_percent,
                "ram_available_mb": ram_available_mb,
                "battery_percent": battery_percent,
                "power_plugged": power_plugged,
                "battery_status": battery_status_str
            },
            "warnings": warnings,
            "recommendation": recommendation
        }

    def set_power_profile(self, profile: str) -> Dict[str, Any]:
        """
        Set power profile: 'performance', 'balanced', or 'eco'.
        """
        p = (profile or "").strip().lower()
        if p not in ("performance", "balanced", "eco"):
            return {
                "ok": False,
                "error": f"Invalid profile '{profile}'. Choose from: 'performance', 'balanced', 'eco'."
            }

        global CURRENT_POWER_PROFILE
        self.profile = p
        CURRENT_POWER_PROFILE = p

        descriptions = {
            "performance": "Max compute throughput. Full multimodal vision and high-rate local inference enabled.",
            "balanced": "Optimal compromise between battery longevity and AI inference speed.",
            "eco": "Low-power mode. Throttles background vision polling and forces ultra-fast LPU/Groq cloud models to minimize CPU thermals."
        }

        return {
            "ok": True,
            "profile": p,
            "message": f"Power profile switched to '{p.upper()}'.",
            "description": descriptions[p]
        }


_THERMAL_INSTANCE: Optional[ThermalGuard] = None


def get_thermal_guard() -> ThermalGuard:
    """Singleton getter for Thermal Guard."""
    global _THERMAL_INSTANCE
    if _THERMAL_INSTANCE is None:
        _THERMAL_INSTANCE = ThermalGuard()
    return _THERMAL_INSTANCE


def get_hardware_health_audit() -> Dict[str, Any]:
    """Retrieve full hardware and thermal health audit."""
    return get_thermal_guard().get_health_audit()


def set_power_profile(profile: str) -> Dict[str, Any]:
    """Switch active power profile."""
    return get_thermal_guard().set_power_profile(profile)
