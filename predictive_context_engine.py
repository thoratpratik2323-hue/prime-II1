"""
predictive_context_engine.py — Deep Predictive Context & Anticipatory Memory Engine.
Anticipates user intent, pre-fetches codebase architecture and docs upon project switch,
manages deep-work focus triggers, and autonomously organizes thoughts into Obsidian.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("prime.predictive_context")

BASE_DIR = Path(__file__).resolve().parent
OBSIDIAN_VAULT = BASE_DIR / "Obsidian_Vault"


class PredictiveContextEngine:
    """
    Anticipatory engine that runs continuous background context inference:
    1. Active Codebase Pre-fetching: Infers tech stack, architecture, and git state.
    2. Deep Focus Music Trigger: Automatically enables focus soundscapes during intense dev sessions.
    3. Autonomous Obsidian Crystallization: Persists daily milestones and lessons into Obsidian notes.
    """

    def __init__(self, voice_engine: Any = None):
        self.voice = voice_engine
        self._enabled = os.getenv("PREDICTIVE_CONTEXT_ENABLED", "true").lower() in ("true", "1", "yes")
        self._auto_focus_music = os.getenv("AUTO_FOCUS_MUSIC", "false").lower() in ("true", "1", "yes")

        self._active_project_path: Optional[Path] = None
        self._active_project_name: str = ""
        self._cached_project_context: Dict[str, Any] = {}
        self._last_focus_check: float = time.time()
        self._coding_streak_start: Optional[float] = None
        self._focus_music_played: bool = False
        self._last_obsidian_sync: float = 0.0

        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._anticipation_loop,
            daemon=True,
            name="PrimePredictiveContextEngine"
        )
        self._thread.start()
        log.info("Deep Predictive Context Engine online.")

    def stop(self) -> None:
        self._stop_event.set()

    def _anticipation_loop(self) -> None:
        time.sleep(12)  # Wait for startup stabilization

        while not self._stop_event.is_set():
            if not self._enabled:
                time.sleep(5)
                continue

            try:
                self._inspect_active_codebase()
                self._check_focus_flow()
                self._maybe_crystallize_obsidian()
            except Exception as e:
                log.debug("Anticipation cycle exception: %s", e)

            self._stop_event.wait(15.0)

    def _inspect_active_codebase(self) -> None:
        """Inspect active window title to identify if operator switched projects/codebases."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return
            title = win32gui.GetWindowText(hwnd).strip()
        except Exception:
            return

        if not title:
            return

        # Typical VS Code title: "filename.py - ProjectName - Visual Studio Code"
        match = re.search(r"-\s*([A-Za-z0-9_\-\.\s]+)\s*-\s*Visual Studio Code", title, re.IGNORECASE)
        candidate_name = match.group(1).strip() if match else ""

        if not candidate_name and "prime" in title.lower():
            candidate_name = "Prime"

        if candidate_name and candidate_name != self._active_project_name:
            with self._lock:
                self._active_project_name = candidate_name
                log.info("Detected project switch to: '%s'. Pre-fetching codebase context...", candidate_name)
                self._prefetch_codebase_context(candidate_name)

    def _prefetch_codebase_context(self, project_name: str) -> None:
        """Scan project directory, infer stack, inspect git status, and query Obsidian notes."""
        context: Dict[str, Any] = {
            "project_name": project_name,
            "detected_at": datetime.now().isoformat(),
            "stack": [],
            "dependencies": [],
            "git_branch": "unknown",
            "recent_commits": [],
            "obsidian_related_notes": [],
        }

        # Resolve candidate directory
        target_dir = None
        common_roots = [
            BASE_DIR,
            BASE_DIR.parent,
            Path(r"c:\My Projects"),
            Path(r"c:\My Projects\Personal Projects"),
            Path.home() / "Projects",
        ]
        for root in common_roots:
            if (root / project_name).is_dir():
                target_dir = root / project_name
                break
            if root.name.lower() == project_name.lower():
                target_dir = root
                break

        if target_dir is None:
            target_dir = BASE_DIR

        self._active_project_path = target_dir

        # 1. Identify Tech Stack
        try:
            if (target_dir / "package.json").exists():
                context["stack"].append("Node.js/JavaScript/TypeScript")
                try:
                    pkg = json.loads((target_dir / "package.json").read_text(encoding="utf-8", errors="ignore"))
                    deps = list(pkg.get("dependencies", {}).keys())[:8]
                    context["dependencies"].extend(deps)
                except Exception:
                    pass

            if (target_dir / "requirements.txt").exists() or (target_dir / "pyproject.toml").exists():
                context["stack"].append("Python")

            if (target_dir / "Cargo.toml").exists():
                context["stack"].append("Rust")

            if (target_dir / "pubspec.yaml").exists():
                context["stack"].append("Flutter/Dart")
        except Exception:
            pass

        # 2. Git State
        try:
            res_b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(target_dir), capture_output=True, text=True, timeout=3)
            if res_b.returncode == 0:
                context["git_branch"] = res_b.stdout.strip()

            res_c = subprocess.run(["git", "log", "-n", "3", "--oneline"], cwd=str(target_dir), capture_output=True, text=True, timeout=3)
            if res_c.returncode == 0:
                context["recent_commits"] = [line.strip() for line in res_c.stdout.strip().splitlines() if line.strip()]
        except Exception:
            pass

        # 3. Pre-fetch relevant Obsidian notes
        try:
            from obsidian_rag import search_notes
            notes = search_notes(project_name)
            context["obsidian_related_notes"] = [n.get("title") for n in notes[:3] if n.get("title")]
        except Exception:
            pass

        self._cached_project_context = context

        # Feed into working memory of the unified brain
        try:
            from memory.brain import store_fact
            summary_fact = (
                f"Currently focused on project '{project_name}' (Stack: {', '.join(context['stack']) or 'General'}, "
                f"Branch: {context['git_branch']})."
            )
            store_fact("pratik", "active_project_context", summary_fact, confidence=0.95)
        except Exception:
            pass

    def _check_focus_flow(self) -> None:
        """Detect transition into deep coding flow and manage ambient focus cues."""
        now = time.time()
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).lower() if hwnd else ""
        except Exception:
            title = ""

        is_coding = any(k in title for k in ("visual studio code", "vscode", "pycharm", ".py", ".ts", ".js", ".rs", ".dart"))

        if is_coding:
            if self._coding_streak_start is None:
                self._coding_streak_start = now
            elif now - self._coding_streak_start > 300:  # 5 minutes continuous focus
                if not self._focus_music_played and self._auto_focus_music:
                    self._focus_music_played = True
                    log.info("Deep focus flow detected (>5 mins active coding). Offering focus ambience...")
                    if self.voice and getattr(self.voice, "tts_enabled", True):
                        self.voice.speak("Deep coding flow detected. Queuing ambient focus soundscape.")
                    try:
                        from tool_definitions import execute_tool
                        execute_tool("spotifyControl", {"command": "play lofi beats"})
                    except Exception:
                        pass
        else:
            # If away from coding for > 10 minutes, reset streak
            if self._coding_streak_start and (now - self._coding_streak_start > 600):
                self._coding_streak_start = None
                self._focus_music_played = False

    def _maybe_crystallize_obsidian(self) -> None:
        """Autonomously organize daily milestones into Obsidian notes."""
        now = time.time()
        if now - self._last_obsidian_sync < 1800:  # Every 30 minutes
            return
        self._last_obsidian_sync = now

        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_folder = OBSIDIAN_VAULT / "Daily_Notes"
        daily_folder.mkdir(parents=True, exist_ok=True)
        daily_file = daily_folder / f"{today_str}.md"

        try:
            # Collect recent trace count & facts
            from prime_traces import trace_logger
            traces = trace_logger.get_recent_traces(limit=5)
            commands = [t.get("user_input") for t in traces if t.get("user_input")]

            section = f"\n\n## 🧠 Prime Autonomous Sync ({datetime.now().strftime('%H:%M')})\n"
            if self._active_project_name:
                section += f"- **Active Project:** `{self._active_project_name}`\n"
            if commands:
                section += f"- **Recent Interactions:**\n"
                for cmd in commands[:3]:
                    section += f"  - `{cmd}`\n"

            # Append without overwriting user's existing markdown notes
            if daily_file.exists():
                existing = daily_file.read_text(encoding="utf-8", errors="ignore")
                if section.strip() not in existing:
                    daily_file.write_text(existing + section, encoding="utf-8")
            else:
                header = f"# 📝 Daily Journal — {today_str}\n\n*Created autonomously by Prime Cognitive Engine*\n"
                daily_file.write_text(header + section, encoding="utf-8")

            log.info("Autonomously crystallized session thoughts to Obsidian (%s)", daily_file.name)
        except Exception as e:
            log.debug("Obsidian crystallization error: %s", e)

    def get_predictive_system_context(self) -> str:
        """Return structured predictive context to inject into AI Agent system prompts."""
        with self._lock:
            if not self._cached_project_context:
                return ""
            ctx = self._cached_project_context
            lines = [
                f"[PREDICTIVE CODEBASE CONTEXT]",
                f"- Active Project: {ctx.get('project_name', 'None')}",
                f"- Tech Stack: {', '.join(ctx.get('stack', [])) or 'General'}",
                f"- Git Branch: {ctx.get('git_branch', 'N/A')}",
            ]
            if ctx.get("recent_commits"):
                lines.append(f"- Recent Commits: {'; '.join(ctx.get('recent_commits', [])[:2])}")
            if ctx.get("obsidian_related_notes"):
                lines.append(f"- Relevant Obsidian Knowledge: {', '.join(ctx.get('obsidian_related_notes', []))}")
            return "\n".join(lines)


# Singleton instance
from voice_engine import voice

predictive_engine = PredictiveContextEngine(voice_engine=voice)
