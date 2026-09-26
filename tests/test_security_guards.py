"""
Test Suite: Security Guards & Safe AST Evaluators
Validates that eval/exec vulnerabilities are eradicated and safety guardrails hold.
"""

import sys
import os
import unittest
import math

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pathlib import Path
from actions.safe_code_executor import SafeCodeExecutor
from actions.workflow_engine import WorkflowEngine
from actions.autonomous_autopilot import _execute_safe_gui_statement
from desktop_agent.tools_shell import execute_powershell, manage_process
from desktop_agent.tools_files import _ensure_safe, ToolError


class TestSecurityGuards(unittest.TestCase):
    """Verifies that all security boundaries are strictly enforced."""

    def setUp(self):
        self.executor = SafeCodeExecutor()

    def test_safe_math_expression_evaluator(self):
        """calculate_expression should correctly evaluate math expressions without eval()."""
        # Basic math
        res = self.executor.calculate_expression("2 + 2 * 3")
        self.assertTrue(res["success"])
        self.assertEqual(res["result"], 8)

        res = self.executor.calculate_expression("(10 - 2) / 4")
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["result"], 2.0)

        res = self.executor.calculate_expression("2 ** 4")
        self.assertTrue(res["success"])
        self.assertEqual(res["result"], 16)

        res = self.executor.calculate_expression("10 % 3")
        self.assertTrue(res["success"])
        self.assertEqual(res["result"], 1)

        # Advanced math functions and constants
        res = self.executor.calculate_expression("sqrt(16)")
        self.assertTrue(res["success"])
        self.assertEqual(res["result"], 4.0)

        res = self.executor.calculate_expression("sin(pi / 2)")
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["result"], 1.0)

        res = self.executor.calculate_expression("log(e)")
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["result"], 1.0)

    def test_math_evaluator_blocks_code_execution_and_exploits(self):
        """calculate_expression must reject any malicious code execution or sandbox escapes."""
        # Function imports / OS commands
        res = self.executor.calculate_expression("__import__('os').system('whoami')")
        self.assertFalse(res["success"])

        res = self.executor.calculate_expression("open('test.txt', 'w')")
        self.assertFalse(res["success"])

        # Classic attribute-chain sandbox escapes
        res = self.executor.calculate_expression("().__class__.__bases__[0].__subclasses__()")
        self.assertFalse(res["success"])

        res = self.executor.calculate_expression("().__class__.__mro__[1].__subclasses__()")
        self.assertFalse(res["success"])

        # Dangerous builtins
        res = self.executor.calculate_expression("eval('1+1')")
        self.assertFalse(res["success"])

        res = self.executor.calculate_expression("exec('x = 1')")
        self.assertFalse(res["success"])

    def test_workflow_engine_safe_condition_evaluation(self):
        """WorkflowEngine._evaluate_condition should evaluate safe conditions without eval()."""
        engine = WorkflowEngine()
        context = {
            "retry_count": 3,
            "status": "success",
            "is_ready": True,
            "is_error": False,
        }

        # Valid expressions
        self.assertTrue(engine._evaluate_condition("retry_count < 5", context))
        self.assertFalse(engine._evaluate_condition("retry_count > 5", context))
        self.assertTrue(engine._evaluate_condition("status == 'success'", context))
        self.assertFalse(engine._evaluate_condition("status == 'failed'", context))
        self.assertTrue(engine._evaluate_condition("is_ready and not is_error", context))

        # Rejection of unsafe expressions / function calls
        self.assertFalse(engine._evaluate_condition("__import__('os').system('dir')", context))
        self.assertFalse(engine._evaluate_condition("().__class__.__bases__[0]", context))

    def test_autopilot_blocks_arbitrary_gui_statements(self):
        """_execute_safe_gui_statement must reject non-whitelisted functions and arbitrary code."""
        import pyautogui
        import time

        # Unsafe function calls
        self.assertFalse(_execute_safe_gui_statement("os.system('dir')", pyautogui, time))
        self.assertFalse(_execute_safe_gui_statement("__import__('subprocess').call(['calc'])", pyautogui, time))
        self.assertFalse(_execute_safe_gui_statement("eval('1+1')", pyautogui, time))
        self.assertFalse(_execute_safe_gui_statement("open('pwned.txt', 'w').write('bad')", pyautogui, time))

        # Safe sleep call with literal argument
        self.assertTrue(_execute_safe_gui_statement("time.sleep(0.001)", pyautogui, time))

    def test_powershell_dangerous_command_guardrails(self):
        """execute_powershell must block dangerous system commands."""
        # Test destructive commands
        with self.assertRaises(ToolError) as ctx1:
            execute_powershell({"command": "format C: /fs:ntfs"})
        self.assertIn("Safety Guardrails", str(ctx1.exception))

        with self.assertRaises(ToolError) as ctx2:
            execute_powershell({"command": "Remove-Item -Recurse -Force C:\\Windows\\System32"})
        self.assertIn("Safety Guardrails", str(ctx2.exception))

        with self.assertRaises(ToolError) as ctx3:
            execute_powershell({"command": "Set-MpPreference -DisableRealtimeMonitoring $true"})
        self.assertIn("Safety Guardrails", str(ctx3.exception))

    def test_process_manager_blocks_killing_system_processes(self):
        """manage_process must reject terminating critical Windows processes."""
        for sys_proc in ["csrss.exe", "lsass.exe", "services.exe", "smss.exe", "winlogon.exe"]:
            with self.assertRaises(ToolError) as ctx:
                manage_process({"action": "kill", "name": sys_proc})
            self.assertIn("Cannot terminate protected Windows system process", str(ctx.exception))

    def test_file_tools_forbidden_system_roots(self):
        """_ensure_safe must refuse write/delete targeting core Windows system directories."""
        # Windows system folder
        with self.assertRaises(ToolError) as ctx1:
            _ensure_safe(Path(r"C:\Windows\System32\drivers\etc\hosts"), allow_anywhere=True, for_write_or_delete=True)
        self.assertIn("strictly forbidden", str(ctx1.exception))

        # Program Files
        with self.assertRaises(ToolError) as ctx2:
            _ensure_safe(Path(r"C:\Program Files\Common Files"), allow_anywhere=True, for_write_or_delete=True)
        self.assertIn("strictly forbidden", str(ctx2.exception))

        # Drive root
        with self.assertRaises(ToolError) as ctx3:
            _ensure_safe(Path(r"C:\\"), allow_anywhere=True, for_write_or_delete=True)
        self.assertIn("strictly forbidden", str(ctx3.exception))


if __name__ == "__main__":
    unittest.main()
