"""
tests/test_prime_dots.py
Comprehensive test suite for Prime Dots (24/7 Autonomous Background Agent Daemon Pods).
Validates:
1. PrimeDot lifecycle (instantiation, status transitions, serialization).
2. Canvas Markdown note generation in Obsidian_Vault/Dots/<dot_id>.md.
3. Policy approval gating and human-in-the-loop safety resolution.
4. PrimeDotEngine singleton orchestration (spawn, list, pause, resume, stop, telemetry).
5. Tool definition dispatch integration (spawnPrimeDot, listPrimeDots, controlPrimeDot, readDotCanvas).
"""

import os
import time
import unittest
from pathlib import Path

from core.prime_dots import PrimeDot, PrimeDotEngine, dot_engine
from tool_definitions import execute_tool, TOOL_SPECS


class TestPrimeDots(unittest.TestCase):
    """Test suite for Prime Dots Autonomous Agent Engine."""

    def setUp(self):
        self.engine = dot_engine

    def test_prime_dot_instantiation(self):
        """Verify dot initialization and defaults."""
        dot = PrimeDot(
            goal="Test automated lead intelligence gathering",
            name="TestLeadDot",
        )
        self.assertEqual(dot.status, "idle")
        self.assertEqual(dot.name, "TestLeadDot")
        self.assertEqual(dot.goal, "Test automated lead intelligence gathering")
        self.assertGreater(len(dot.allowed_tools), 5)
        self.assertTrue(dot.dot_id.startswith("dot_"))

        d = dot.to_dict()
        self.assertEqual(d["dot_id"], dot.dot_id)
        self.assertEqual(d["status"], "idle")
        self.assertEqual(d["goal"], dot.goal)

    def test_canvas_markdown_sync(self):
        """Verify Obsidian Second Brain canvas Markdown generation."""
        dot = PrimeDot(
            goal="Audit system resource metrics and security posture",
            name="TestAuditDot",
        )
        dot.status = "running"
        dot.iteration_count = 1
        dot.steps.append({
            "iteration": 1,
            "timestamp": "2026-10-01T12:00:00",
            "thought": "Checking CPU and memory telemetry.",
            "tool": "systemInfo",
            "args": {},
            "result": "CPU 12%, RAM 45%",
        })
        dot.findings.append("Resource usage is healthy.")
        dot._sync_canvas()

        self.assertTrue(dot.canvas_file.exists())
        content = dot.get_canvas_content()
        self.assertIn("Prime Dot Canvas: TestAuditDot", content)
        self.assertIn("Audit system resource metrics and security posture", content)

        self.assertIn("Resource usage is healthy", content)
        self.assertIn("systemInfo", content)

        # Cleanup
        try:
            dot.canvas_file.unlink(missing_ok=True)
        except Exception:
            pass

    def test_engine_spawn_and_lifecycle(self):
        """Verify spawning, listing, pausing, resuming, and stopping dots."""
        spawn_res = self.engine.spawn_dot(
            goal="Monitor local network health and latency",
            name="TestLifecycleDot",
            interval_seconds=0,
            auto_start=False,
        )
        self.assertTrue(spawn_res.get("ok"))
        dot_info = spawn_res["dot"]
        dot_id = dot_info["dot_id"]

        dot = self.engine.get_dot(dot_id)
        self.assertIsNotNone(dot)
        self.assertEqual(dot.name, "TestLifecycleDot")
        self.assertEqual(dot.status, "idle")

        # Test listing
        all_dots = self.engine.list_dots(active_only=False)
        self.assertTrue(any(d["dot_id"] == dot_id for d in all_dots))

        # Test pause and resume
        dot.status = "running"
        paused = self.engine.pause_dot(dot_id)
        self.assertTrue(paused)
        self.assertEqual(dot.status, "paused")

        resumed = self.engine.resume_dot(dot_id)
        self.assertTrue(resumed)
        self.assertEqual(dot.status, "running")

        # Test stop
        stopped = self.engine.stop_dot(dot_id)
        self.assertTrue(stopped)
        self.assertEqual(dot.status, "stopped")


        # Telemetry verification
        telemetry = self.engine.get_telemetry()
        self.assertIn("total_dots", telemetry)
        self.assertIn("running_dots", telemetry)
        self.assertIn("completed_dots", telemetry)

        # Cleanup canvas
        try:
            dot.canvas_file.unlink(missing_ok=True)
        except Exception:
            pass

    def test_policy_approval_workflow(self):
        """Verify human-in-the-loop approval workflow for gated tools."""
        dot = PrimeDot(
            goal="Execute system maintenance and purge logs",
            name="TestApprovalDot",
        )
        dot.status = "waiting_approval"
        dot.pending_approval = {
            "tool": "runTerminalCommand",
            "args": {"command": "rmdir /s /q temp"},
            "reason": "Terminal execution requires policy clearance",
            "requested_at": "2026-10-01T12:00:00",
        }
        self.engine.dots[dot.dot_id] = dot

        # Test rejection
        rej = self.engine.approve_dot_action(dot.dot_id, approved=False)
        self.assertTrue(rej)
        self.assertEqual(dot.status, "running")
        self.assertIsNone(dot.pending_approval)

        # Test approval
        dot.status = "waiting_approval"
        dot.pending_approval = {"tool": "runTerminalCommand", "args": {}}
        appr = self.engine.approve_dot_action(dot.dot_id, approved=True)
        self.assertTrue(appr)
        self.assertEqual(dot.status, "running")
        self.assertIsNone(dot.pending_approval)

        # Cleanup
        try:
            dot.canvas_file.unlink(missing_ok=True)
        except Exception:
            pass

    def test_tool_definitions_dispatch(self):
        """Verify all 4 Prime Dots tools execute cleanly via execute_tool()."""
        # 1. spawnPrimeDot
        res_spawn = execute_tool("spawnPrimeDot", {
            "goal": "Collect weekly research papers on local LLM quantization",
            "name": "ResearchPaperDot",
        })
        self.assertTrue(res_spawn.get("ok"))
        dot_id = res_spawn["dot"]["dot_id"]

        # 2. listPrimeDots
        res_list = execute_tool("listPrimeDots", {"active_only": False})
        self.assertTrue(res_list.get("ok"))
        self.assertGreaterEqual(res_list.get("count", 0), 1)

        # 3. controlPrimeDot (pause/resume/stop)
        res_ctrl_pause = execute_tool("controlPrimeDot", {
            "dot_id": dot_id,
            "action": "pause",
        })
        self.assertTrue(res_ctrl_pause.get("ok"))

        res_ctrl_stop = execute_tool("controlPrimeDot", {
            "dot_id": dot_id,
            "action": "stop",
        })
        self.assertTrue(res_ctrl_stop.get("ok"))

        # 4. readDotCanvas
        res_canvas = execute_tool("readDotCanvas", {"dot_id": dot_id})
        self.assertTrue(res_canvas.get("ok"))
        self.assertIn("goal", res_canvas)
        self.assertIn("canvas_content", res_canvas)


        # Cleanup
        dot = self.engine.get_dot(dot_id)
        if dot:
            try:
                dot.canvas_file.unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
