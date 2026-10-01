"""
tests/test_fast_failover.py - Validates instant Groq failover and fast-path navigation.
"""

import time
import unittest
from unittest.mock import MagicMock, patch
from ai_agent import AIAgent

class TestFastFailoverAndNavigation(unittest.TestCase):
    def setUp(self):
        self.agent = AIAgent()

    def test_bare_navigation_prompt(self):
        res = self.agent._process_fast_command("navigate to", None, None)
        self.assertIsNotNone(res)
        self.assertIn("Where would you like to navigate", res)

    @patch("ai_agent.execute_tool", return_value={"ok": True, "result": "Opened in Chrome"})
    def test_navigate_to_site_fast_path(self, mock_exec):
        res = self.agent._process_fast_command("navigate to youtube", None, None)
        self.assertIsNotNone(res)
        self.assertIn("Opening Youtube in Google Chrome", res)
        mock_exec.assert_called_once()

    @patch("ai_agent.execute_tool", return_value={"ok": True, "result": "Opened in Chrome"})
    def test_go_to_site_fast_path(self, mock_exec):
        res = self.agent._process_fast_command("go to github", None, None)
        self.assertIsNotNone(res)
        self.assertIn("Opening Github in Google Chrome", res)
        mock_exec.assert_called_once()

    def test_gemini_503_immediate_groq_backoff(self):
        self.agent._gemini_chat = MagicMock()
        self.agent._gemini_chat.send_message.side_effect = Exception("503 UNAVAILABLE. The service is currently unavailable.")

        res = self.agent._process_gemini("test prompt", None, None)
        self.assertEqual(res, "__GEMINI_EXHAUSTED__")
        self.assertGreater(self.agent._gemini_quota_exhausted_until, time.time() + 40.0)

    def test_gemini_timeout_immediate_groq_backoff(self):
        self.agent._gemini_chat = MagicMock()
        self.agent._gemini_chat.send_message.side_effect = Exception("Request timed out. DeadlineExceeded")

        res = self.agent._process_gemini("test prompt", None, None)
        self.assertEqual(res, "__GEMINI_EXHAUSTED__")
        self.assertGreater(self.agent._gemini_quota_exhausted_until, time.time() + 40.0)

if __name__ == "__main__":
    unittest.main()
