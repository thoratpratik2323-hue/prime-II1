"""
actions/friday_tasks.py
Durable Multi-Step Task & Plan Tracker for Prime AI (Inspired by debpalash/friday).

Enables multi-step planning where progress, step statuses, and verification receipts
survive process restarts, preventing repeated work and lost context.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("prime.friday.tasks")
TASKS_FILE = Path(__file__).resolve().parent.parent / "data" / "friday_durable_tasks.json"


class FridayTaskManager:
    """Manages durable, restart-safe plans and task execution steps."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or TASKS_FILE
        self.plans: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load durable tasks: {e}")
        return {}

    def _save(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.plans, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save durable tasks: {e}")

    def create_plan(self, goal: str, steps: List[str]) -> Dict[str, Any]:
        """Create a new durable multi-step plan."""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now().isoformat()

        structured_steps = []
        for i, s in enumerate(steps):
            structured_steps.append({
                "step_index": i,
                "description": s,
                "status": "pending",
                "evidence": None
            })

        plan = {
            "plan_id": plan_id,
            "goal": goal,
            "created_at": now_iso,
            "updated_at": now_iso,
            "status": "in_progress",
            "current_step_index": 0,
            "steps": structured_steps
        }

        self.plans[plan_id] = plan
        self._save()
        logger.info(f"[Friday Tasks] Created durable plan {plan_id}: '{goal}' ({len(steps)} steps)")
        return {
            "ok": True,
            "plan_id": plan_id,
            "plan": plan
        }

    def update_step_status(self, plan_id: str, step_index: int, status: str, evidence: Optional[str] = None) -> Dict[str, Any]:
        """Update progress on a specific step."""
        if plan_id not in self.plans:
            return {"ok": False, "error": f"Plan '{plan_id}' not found."}

        plan = self.plans[plan_id]
        if step_index < 0 or step_index >= len(plan["steps"]):
            return {"ok": False, "error": f"Invalid step index {step_index}."}

        plan["steps"][step_index]["status"] = status
        if evidence:
            plan["steps"][step_index]["evidence"] = evidence
        plan["updated_at"] = datetime.now().isoformat()

        # Check if all completed
        if all(s["status"] == "completed" for s in plan["steps"]):
            plan["status"] = "completed"
        elif any(s["status"] == "failed" for s in plan["steps"]):
            plan["status"] = "failed"
        else:
            plan["status"] = "in_progress"
            # Advance current step
            for idx, s in enumerate(plan["steps"]):
                if s["status"] != "completed":
                    plan["current_step_index"] = idx
                    break

        self._save()
        logger.info(f"[Friday Tasks] Plan {plan_id} step {step_index} updated to {status}")
        return {
            "ok": True,
            "plan_id": plan_id,
            "plan_status": plan["status"],
            "current_step": plan["current_step_index"]
        }

    def get_active_plan(self) -> Dict[str, Any]:
        """Fetch the most recent in-progress plan surviving restarts."""
        for p in reversed(list(self.plans.values())):
            if p["status"] == "in_progress":
                return {
                    "ok": True,
                    "has_active_plan": True,
                    "plan": p
                }

        return {"ok": True, "has_active_plan": False, "plan": None}

    def list_plans(self, limit: int = 10) -> Dict[str, Any]:
        """List recent plans."""
        return {
            "ok": True,
            "count": len(self.plans),
            "plans": list(reversed(list(self.plans.values())))[:limit]
        }


# Global singleton
task_manager = FridayTaskManager()


def create_durable_task_plan(goal: str, steps: List[str]) -> Dict[str, Any]:
    return task_manager.create_plan(goal, steps)


def update_task_plan_step(plan_id: str, step_index: int, status: str, evidence: Optional[str] = None) -> Dict[str, Any]:
    return task_manager.update_step_status(plan_id, step_index, status, evidence=evidence)


def get_active_task_plan() -> Dict[str, Any]:
    return task_manager.get_active_plan()
