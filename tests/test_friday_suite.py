"""
tests/test_friday_suite.py
Comprehensive unit test suite for Friday Assistant Architecture Suite in Prime AI:
1. Execution Receipts & Atomic Undo/Rollback Engine
2. Explicit User Preference & Memory Ledger
3. Approval Boundary & Safety Policy Gatekeeper
4. Durable Multi-Step Task Planner
5. Tool Catalog Registration & Dispatch Integration
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.friday_receipts import FridayReceiptEngine, record_action_receipt, undo_last_action, list_execution_receipts
from actions.friday_memory import FridayMemoryLedger, remember_user_preference, recall_user_preferences, forget_user_preference
from actions.friday_policy import FridayPolicyGatekeeper, check_action_policy, verify_action_approval
from actions.friday_tasks import FridayTaskManager, create_durable_task_plan, update_task_plan_step, get_active_task_plan
import tool_definitions


class TestFridayReceipts(unittest.TestCase):
    """Test Suite for Execution Receipts & Atomic Undo/Rollback."""

    def setUp(self):
        self.test_dir = Path(__file__).resolve().parent / "tmp_friday_receipts"
        self.engine = FridayReceiptEngine(storage_dir=self.test_dir)
        self.sample_file = self.test_dir / "target_file.txt"

    def tearDown(self):
        if self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_capture_and_rollback_modification(self):
        # 1. Create file with original content
        self.sample_file.write_text("Original pristine content.", encoding="utf-8")
        pre = self.engine.capture_pre_state(str(self.sample_file))
        self.assertTrue(pre["exists"])
        self.assertEqual(pre["content"], "Original pristine content.")

        # 2. Modify file and record receipt
        self.sample_file.write_text("Corrupted or unintended change.", encoding="utf-8")
        rcpt = self.engine.record_receipt("patch_file", str(self.sample_file), pre)
        self.assertIn("rcpt_", rcpt["receipt_id"])

        # 3. Undo / Rollback
        undo_res = self.engine.rollback_receipt(rcpt["receipt_id"])
        self.assertTrue(undo_res["ok"])
        self.assertEqual(self.sample_file.read_text(encoding="utf-8"), "Original pristine content.")

    def test_capture_and_rollback_creation(self):
        new_file = self.test_dir / "created_file.txt"
        pre = self.engine.capture_pre_state(str(new_file))
        self.assertFalse(pre["exists"])

        # Create file
        new_file.write_text("New file created.", encoding="utf-8")
        rcpt = self.engine.record_receipt("create_file", str(new_file), pre)

        # Undo should remove the created file
        undo_res = self.engine.undo_last_action()
        self.assertTrue(undo_res["ok"])
        self.assertFalse(new_file.exists())


class TestFridayMemory(unittest.TestCase):
    """Test Suite for Explicit Preference & Memory Ledger."""

    def setUp(self):
        self.test_mem = Path(__file__).resolve().parent / "tmp_friday_mem.json"
        self.ledger = FridayMemoryLedger(storage_path=self.test_mem)

    def tearDown(self):
        if self.test_mem.exists():
            try:
                self.test_mem.unlink()
            except Exception:
                pass

    def test_remember_recall_forget(self):
        # 1. Remember
        rem = self.ledger.remember("editor", "VS Code with Vim Keybindings", category="preferences")
        self.assertTrue(rem["ok"])
        self.assertIn("editor", self.ledger.memories)

        # 2. Recall
        rec = self.ledger.recall(query="vim")
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["count"], 1)
        self.assertEqual(rec["memories"][0]["value"], "VS Code with Vim Keybindings")

        # 3. Prompt context
        prompt_ctx = self.ledger.get_system_prompt_context()
        self.assertIn("VS Code", prompt_ctx)

        # 4. Forget
        f_res = self.ledger.forget("editor")
        self.assertTrue(f_res["ok"])
        self.assertNotIn("editor", self.ledger.memories)


class TestFridayPolicy(unittest.TestCase):
    """Test Suite for Approval Boundary & Safety Policy Gatekeeper."""

    def setUp(self):
        self.gatekeeper = FridayPolicyGatekeeper()

    def test_safe_and_sensitive_actions(self):
        # Safe read action
        safe_eval = self.gatekeeper.evaluate_action("readFile", {"path": "test.txt"})
        self.assertEqual(safe_eval["status"], "APPROVED")
        self.assertFalse(safe_eval["approval_required"])

        # Sensitive write action
        sens_eval = self.gatekeeper.evaluate_action("patchCodeFile", {"path": "test.txt"})
        self.assertEqual(sens_eval["status"], "APPROVED")
        self.assertFalse(sens_eval["approval_required"])

    def test_destructive_command_gating_and_approval(self):
        # Destructive command
        dest_eval = self.gatekeeper.evaluate_action("runTerminalCommand", {"command": "rm -rf /some/directory"})
        self.assertEqual(dest_eval["status"], "APPROVAL_REQUIRED")
        self.assertTrue(dest_eval["approval_required"])
        self.assertEqual(dest_eval["risk_tier"], "HIGH_RISK")
        token = dest_eval["approval_token"]
        self.assertIn("appr_", token)

        # Verify approval with token
        verified = self.gatekeeper.verify_approval(token)
        self.assertTrue(verified["ok"])
        self.assertTrue(verified["approved"])


class TestFridayTasks(unittest.TestCase):
    """Test Suite for Durable Multi-Step Task Planner."""

    def setUp(self):
        self.test_tasks = Path(__file__).resolve().parent / "tmp_friday_tasks.json"
        self.manager = FridayTaskManager(storage_path=self.test_tasks)

    def tearDown(self):
        if self.test_tasks.exists():
            try:
                self.test_tasks.unlink()
            except Exception:
                pass

    def test_plan_lifecycle_and_restart_survival(self):
        # 1. Create multi-step plan
        steps = ["Research API specs", "Implement module", "Run test suite"]
        res = self.manager.create_plan("Build Authentication Service", steps)
        self.assertTrue(res["ok"])
        plan_id = res["plan_id"]

        # 2. Complete Step 0
        u1 = self.manager.update_step_status(plan_id, 0, "completed", evidence="Found OAuth2 docs")
        self.assertTrue(u1["ok"])
        self.assertEqual(u1["current_step"], 1)

        # 3. Simulate process restart by reloading from disk
        reloaded_manager = FridayTaskManager(storage_path=self.test_tasks)
        active = reloaded_manager.get_active_plan()
        self.assertTrue(active["ok"])
        self.assertTrue(active["has_active_plan"])
        self.assertEqual(active["plan"]["current_step_index"], 1)
        self.assertEqual(active["plan"]["steps"][0]["status"], "completed")


class TestToolDefinitionsFridayIntegration(unittest.TestCase):
    """Test Suite for Friday Tool Registration & Dispatcher Integration."""

    def test_specs_registered(self):
        names = [s["name"] for s in tool_definitions.TOOL_SPECS]
        self.assertIn("undoLastAction", names)
        self.assertIn("listExecutionReceipts", names)
        self.assertIn("rememberUserPreference", names)
        self.assertIn("recallPreferences", names)
        self.assertIn("forgetUserPreference", names)
        self.assertIn("checkActionPolicy", names)
        self.assertIn("createDurableTaskPlan", names)
        self.assertIn("updateTaskPlanStep", names)
        self.assertIn("getActiveTaskPlan", names)

    @patch("actions.friday_receipts.undo_last_action")
    def test_execute_undo(self, mock_undo):
        mock_undo.return_value = {"ok": True, "message": "Undone"}
        res = tool_definitions.execute_tool("undoLastAction", {})
        self.assertTrue(res["ok"])
        mock_undo.assert_called_once()

    @patch("actions.friday_memory.remember_user_preference")
    def test_execute_remember(self, mock_rem):
        mock_rem.return_value = {"ok": True, "message": "Remembered"}
        res = tool_definitions.execute_tool("rememberUserPreference", {"key": "theme", "value": "Tokyo Night"})
        self.assertTrue(res["ok"])
        mock_rem.assert_called_with("theme", "Tokyo Night", category="preferences")

    @patch("actions.friday_policy.check_action_policy")
    def test_execute_check_policy(self, mock_policy):
        mock_policy.return_value = {"ok": True, "status": "APPROVED"}
        res = tool_definitions.execute_tool("checkActionPolicy", {"tool_name": "createFile"})
        self.assertTrue(res["ok"])
        mock_policy.assert_called_with("createFile", params={})

    @patch("actions.friday_tasks.create_durable_task_plan")
    def test_execute_create_plan(self, mock_plan):
        mock_plan.return_value = {"ok": True, "plan_id": "p1"}
        res = tool_definitions.execute_tool("createDurableTaskPlan", {"goal": "Upgrade UI", "steps": ["Step 1", "Step 2"]})
        self.assertTrue(res["ok"])
        mock_plan.assert_called_with("Upgrade UI", ["Step 1", "Step 2"])


if __name__ == "__main__":
    unittest.main()
