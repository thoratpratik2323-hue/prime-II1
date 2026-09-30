"""
actions/os1_fragments.py
Generative Ephemeral UI Fragments Engine for Prime AI (Inspired by debpalash/OS1).

Generates purpose-built, lightweight micro-widgets that appear when needed and fade when done:
- disk_cleaner: Storage breakdown, caches, temp files, and cleaning actions
- git_card: Modified files, git status, one-tap commit suggestion
- media_controller: Minimal floating "chill" audio player widget
- system_status: CPU, RAM, battery, thermal load summary
- lead_intel_card: Enriched company and intent signals overview
"""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("prime.os1.fragments")
FRAGMENTS_FILE = Path(__file__).resolve().parent.parent / "data" / "os1_active_fragments.json"


class OS1FragmentsEngine:
    """Manages active, ephemeral UI fragments on Prime's screen."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or FRAGMENTS_FILE
        self.active_fragments: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load active fragments: {e}")
        return {}

    def _save(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.active_fragments, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to persist fragments: {e}")

    def generate_fragment(self, fragment_type: str, custom_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate and stage an ephemeral UI fragment."""
        frag_id = f"frag_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now().isoformat()
        ftype = fragment_type.lower().strip()

        if ftype == "disk_cleaner":
            content = self._build_disk_fragment()
        elif ftype in ("git", "git_card", "git_diff"):
            content = self._build_git_fragment()
        elif ftype in ("media", "media_controller", "music"):
            content = self._build_media_fragment(custom_data)
        elif ftype in ("system", "system_status", "hardware"):
            content = self._build_system_fragment()
        elif ftype in ("lead", "lead_intel", "lead_card"):
            content = self._build_lead_fragment(custom_data)
        else:
            content = {
                "title": (custom_data or {}).get("title", "Custom Fragment"),
                "body": (custom_data or {}).get("body", "Ephemeral UI Fragment"),
                "actions": (custom_data or {}).get("actions", ["Dismiss"])
            }

        fragment = {
            "id": frag_id,
            "type": ftype,
            "created_at": now_iso,
            "ttl_seconds": 300,  # 5 minutes ephemeral life
            "state": "active",
            "content": content
        }

        self.active_fragments[frag_id] = fragment
        self._save()
        logger.info(f"[OS1 Fragments] Generated ephemeral fragment {frag_id} of type '{ftype}'")
        return {
            "ok": True,
            "fragment_id": frag_id,
            "type": ftype,
            "fragment": fragment
        }

    def dismiss_fragment(self, fragment_id: str) -> Dict[str, Any]:
        """Dismiss and remove an ephemeral fragment."""
        if fragment_id in self.active_fragments:
            removed = self.active_fragments.pop(fragment_id)
            self._save()
            return {"ok": True, "message": f"Fragment '{fragment_id}' dismissed.", "type": removed.get("type")}
        elif fragment_id.lower() == "all":
            count = len(self.active_fragments)
            self.active_fragments.clear()
            self._save()
            return {"ok": True, "message": f"Dismissed all {count} active fragments."}
        return {"ok": False, "error": f"Fragment '{fragment_id}' not found."}

    def list_active_fragments(self) -> Dict[str, Any]:
        """List all currently rendered ephemeral fragments."""
        return {
            "ok": True,
            "count": len(self.active_fragments),
            "fragments": list(self.active_fragments.values())
        }

    def _build_disk_fragment(self) -> Dict[str, Any]:
        """Constructs disk usage and cleaning options."""
        drives = []
        try:
            import psutil
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    drives.append({
                        "mount": part.mountpoint,
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                        "percent": usage.percent
                    })
                except Exception:
                    pass
        except Exception:
            pass

        temp_dir = os.environ.get("TEMP", "")
        temp_size_mb = 0
        if temp_dir and os.path.exists(temp_dir):
            try:
                temp_size_mb = round(sum(os.path.getsize(os.path.join(temp_dir, f)) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))) / (1024**2), 1)
            except Exception:
                temp_size_mb = 120.0

        return {
            "title": "OS 1 Disk & Storage Breakdown",
            "drives": drives,
            "temp_cache_mb": temp_size_mb,
            "suggested_actions": ["Clean Windows Temp Files", "Purge Package Caches", "Review Large Files"]
        }

    def _build_git_fragment(self) -> Dict[str, Any]:
        """Constructs Git repository status card."""
        cwd = Path.cwd()
        branch = "main"
        modified_files = []
        try:
            import subprocess
            branch_out = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=cwd, timeout=3)
            if branch_out.returncode == 0:
                branch = branch_out.stdout.strip()
            status_out = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, cwd=cwd, timeout=3)
            if status_out.returncode == 0:
                modified_files = [line.strip() for line in status_out.stdout.splitlines() if line.strip()][:8]
        except Exception as e:
            logger.debug(f"Git check error: {e}")

        return {
            "title": f"Git Repository: {cwd.name} ({branch})",
            "branch": branch,
            "changed_files_count": len(modified_files),
            "sample_changes": modified_files,
            "suggested_actions": ["Review Diff", "Safe Commit", "Run Tests"]
        }

    def _build_media_fragment(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Minimal chill music controller fragment."""
        track = (data or {}).get("track", "Lofi Beats for Deep Focus")
        artist = (data or {}).get("artist", "OS 1 Companion FM")
        return {
            "title": "Now Playing",
            "track": track,
            "artist": artist,
            "playback_state": "playing",
            "controls": ["Previous", "Play/Pause", "Next", "Volume Down", "Volume Up"]
        }

    def _build_system_fragment(self) -> Dict[str, Any]:
        """Constructs real-time hardware thermals and load."""
        cpu_percent = 0.0
        ram_percent = 0.0
        ram_used_gb = 0.0
        ram_total_gb = 0.0
        battery_percent = None
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            ram_percent = mem.percent
            ram_used_gb = round(mem.used / (1024**3), 1)
            ram_total_gb = round(mem.total / (1024**3), 1)
            batt = psutil.sensors_battery()
            if batt:
                battery_percent = batt.percent
        except Exception:
            pass

        return {
            "title": "System Telemetry & Health",
            "cpu_load_percent": cpu_percent,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "ram_percent": ram_percent,
            "battery_percent": battery_percent,
            "status": "Healthy" if cpu_percent < 80 else "Heavy Load"
        }

    def _build_lead_fragment(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Constructs lead intelligence card."""
        info = data or {}
        return {
            "title": f"Lead Intelligence: {info.get('company_name', 'Account')}",
            "domain": info.get("domain", ""),
            "intent_score": info.get("intent_score", 70),
            "urgency_tier": info.get("urgency_tier", "MEDIUM"),
            "tech_stack": info.get("tech_stack", []),
            "hooks": info.get("conversation_hooks", []),
            "suggested_actions": ["Draft WhatsApp Pitch", "Send Cold Email", "View Full Waterfall"]
        }


# Global singleton
fragments_engine = OS1FragmentsEngine()


def generate_fragment(fragment_type: str, custom_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return fragments_engine.generate_fragment(fragment_type, custom_data=custom_data)


def dismiss_fragment(fragment_id: str) -> Dict[str, Any]:
    return fragments_engine.dismiss_fragment(fragment_id)


def list_active_fragments() -> Dict[str, Any]:
    return fragments_engine.list_active_fragments()
