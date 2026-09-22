"""
prime_goal_harness.py — Persistent Goal Tracking & Continual Harness (Inspired by PrimeIntellect prime-agent).
Manages long-running autonomous objectives, progress checkpoints, and self-improving memory lessons.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

GOALS_FILE = Path(__file__).resolve().parent / "memory" / "active_goals.json"
LESSONS_FILE = Path(__file__).resolve().parent / "memory" / "continual_lessons.json"


def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Atomic write to prevent file corruption on unexpected crashes."""
    try:
        tmp_path = file_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(file_path)
    except Exception:
        # Fallback to direct write if replace fails
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _ensure_storage():
    GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not GOALS_FILE.exists():
        _atomic_write_json(GOALS_FILE, {"active_goal": None, "history": []})
    if not LESSONS_FILE.exists():
        _atomic_write_json(LESSONS_FILE, [])


class GoalTracker:
    def __init__(self):
        _ensure_storage()

    def get_active_goal(self) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
            return data.get("active_goal")
        except Exception:
            return None

    def set_goal(self, objective: str, subtasks: Optional[List[str]] = None) -> Dict[str, Any]:
        _ensure_storage()
        try:
            data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {"active_goal": None, "history": []}

        # If previous goal was active, archive it
        if data.get("active_goal"):
            data.setdefault("history", []).append(data["active_goal"])

        goal = {
            "objective": objective.strip(),
            "status": "IN_PROGRESS",
            "progress_percent": 0.0,
            "subtasks": [{"title": st, "done": False} for st in (subtasks or [])],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "notes": ["Goal initiated."]
        }
        data["active_goal"] = goal
        _atomic_write_json(GOALS_FILE, data)
        return goal

    def update_progress(self, progress_pct: float, note: str = "", status: str = "IN_PROGRESS") -> Optional[Dict[str, Any]]:
        _ensure_storage()
        try:
            data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None

        goal = data.get("active_goal")
        if not goal:
            return None

        goal["progress_percent"] = max(0.0, min(100.0, float(progress_pct)))
        goal["status"] = status
        goal["updated_at"] = datetime.now().isoformat()
        if note:
            goal.setdefault("notes", []).append(f"[{datetime.now().strftime('%H:%M:%S')}] {note}")

        if goal["progress_percent"] >= 100.0 or status == "COMPLETED":
            goal["status"] = "COMPLETED"
            data.setdefault("history", []).append(goal)
            data["active_goal"] = None

        _atomic_write_json(GOALS_FILE, data)
        return goal

    def add_subtask(self, title: str) -> Optional[Dict[str, Any]]:
        """Add a new subtask to the active goal."""
        _ensure_storage()
        try:
            data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
        goal = data.get("active_goal")
        if not goal:
            return None
        goal.setdefault("subtasks", []).append({"title": title.strip(), "done": False})
        goal["updated_at"] = datetime.now().isoformat()
        _atomic_write_json(GOALS_FILE, data)
        return goal

    def toggle_subtask(self, index: int, done: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """Toggle or set completion state of a subtask by 0-based index."""
        _ensure_storage()
        try:
            data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
        goal = data.get("active_goal")
        if not goal:
            return None
        subtasks = goal.get("subtasks", [])
        if 0 <= index < len(subtasks):
            if done is None:
                subtasks[index]["done"] = not subtasks[index].get("done", False)
            else:
                subtasks[index]["done"] = bool(done)
            goal["updated_at"] = datetime.now().isoformat()
            if subtasks:
                completed = sum(1 for s in subtasks if s.get("done"))
                goal["progress_percent"] = (completed / len(subtasks)) * 100.0
            _atomic_write_json(GOALS_FILE, data)
            return goal
        return None

    def complete_active_goal(self, summary: str = "Goal accomplished.") -> Optional[Dict[str, Any]]:
        return self.update_progress(100.0, note=summary, status="COMPLETED")

    def clear_active_goal(self) -> None:
        _ensure_storage()
        try:
            data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
            if data.get("active_goal"):
                data["active_goal"]["status"] = "CANCELLED"
                data.setdefault("history", []).append(data["active_goal"])
                data["active_goal"] = None
                _atomic_write_json(GOALS_FILE, data)
        except Exception:
            pass


class ContinualHarness:
    """Self-improving memory lessons harness (Inspired by PrimeIntellect /refine)."""
    def __init__(self):
        _ensure_storage()

    def record_lesson(self, topic: str, insight: str, source: str = "user_interaction", context: Optional[str] = None) -> Dict[str, Any]:
        _ensure_storage()
        try:
            lessons = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            lessons = []

        next_id = max([l.get("id", 0) for l in lessons], default=0) + 1
        lesson = {
            "id": next_id,
            "timestamp": datetime.now().isoformat(),
            "topic": topic.strip(),
            "insight": insight.strip(),
            "source": source
        }
        if context:
            lesson["context"] = str(context).strip()
        lessons.append(lesson)
        _atomic_write_json(LESSONS_FILE, lessons)
        return lesson

    def get_lessons(self, limit: int = 10) -> List[Dict[str, Any]]:
        _ensure_storage()
        try:
            lessons = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
            return lessons[-limit:] if limit > 0 else []
        except Exception:
            return []

    def get_lessons_context_prompt(self) -> str:
        """Formats stored lessons for injection into AI system prompt."""
        lessons = self.get_lessons(limit=8)
        if not lessons:
            return ""
        lines = ["\n[CONTINUAL HARNESS LESSONS & LEARNED PATTERNS]"]
        for l in lessons:
            topic = l.get("topic", "General")
            insight = l.get("insight", "")
            if insight:
                lines.append(f"- {topic}: {insight}")
        return "\n".join(lines)


goal_tracker = GoalTracker()
continual_harness = ContinualHarness()
