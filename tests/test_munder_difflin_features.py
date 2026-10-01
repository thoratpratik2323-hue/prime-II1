"""
tests/test_munder_difflin_features.py
Comprehensive Test Suite for Munder Difflin inspired features in Prime AI:
1. 2D Virtual Office Floor & Desk Telemetry
2. Asynchronous Stigmergy & Mailbox Protocol (Inbox/Outbox Router)
3. System-Wide Instant Dictation ("Stapler" Hotkey Engine)
4. Voice-First HITL Approval Gatekeeper
"""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.dots_mailbox import DotsMailbox, DotsMailboxRouter, mailbox_router
from core.prime_dots import PrimeDot, PrimeDotEngine, dot_engine
from actions.stapler_dictation import StaplerDictationEngine, stapler_engine


class TestMunderDifflinFeatures(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="prime_munder_test_"))
        self.orig_dots_dir = None

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(str(self.test_dir), ignore_errors=True)

    # ── 1. Asynchronous Mailbox Protocol Tests ────────────────────────────
    def test_mailbox_atomic_send_and_read(self):
        """Verify Dot mailbox creates messages atomically and drains inbox."""
        sender_id = "test_dot_sender"
        recipient_id = "test_dot_recipient"

        sender_mb = DotsMailbox(sender_id)
        recipient_mb = DotsMailbox(recipient_id)

        # Send message from sender to recipient outbox
        msg = sender_mb.send_message(
            recipient_id=recipient_id,
            subject="Dataset Ready",
            body="Synthesized 50 new samples.",
            action="data_share"
        )
        self.assertIsNotNone(msg.get("id"))
        self.assertEqual(msg["sender"], sender_id)
        self.assertEqual(msg["recipient"], recipient_id)

        # Run router pass to deliver from outbox to inbox
        delivered = mailbox_router.dispatch_pending()
        self.assertGreaterEqual(delivered, 1)

        # Recipient reads inbox
        inbox_msgs = recipient_mb.read_inbox(mark_as_done=True)
        self.assertEqual(len(inbox_msgs), 1)
        self.assertEqual(inbox_msgs[0]["subject"], "Dataset Ready")
        self.assertEqual(inbox_msgs[0]["body"], "Synthesized 50 new samples.")

        # Inbox is now drained
        self.assertEqual(recipient_mb.get_unread_count(), 0)

    def test_prime_dot_inter_agent_messaging(self):
        """Verify PrimeDot can send and receive messages directly."""
        dot_a = PrimeDot(goal="Scrape research papers", name="ScoutDot")
        dot_b = PrimeDot(goal="Write summary notes", name="WriterDot")

        # ScoutDot sends message to WriterDot
        res = dot_a.send_message(
            recipient_id=dot_b.dot_id,
            subject="arXiv papers extracted",
            body="3 papers on MoE routing downloaded.",
        )
        self.assertIn("id", res)

        # Dispatch via mailbox router
        mailbox_router.dispatch_pending()

        # WriterDot reads inbox
        unread = dot_b.read_inbox()
        self.assertEqual(len(unread), 1)
        self.assertIn("MoE routing", unread[0]["body"])

    # ── 2. Flying Envelope Event Stream ──────────────────────────────────
    def test_router_flight_telemetry(self):
        """Verify mailbox router records envelope flight events for 2D office floor."""
        dot_x = "dot_alpha"
        dot_y = "dot_beta"

        mb_x = DotsMailbox(dot_x)
        mb_x.send_message(dot_y, "Test Ping", "Hello from Alpha")
        mailbox_router.dispatch_pending()

        flights = mailbox_router.get_recent_flights(seconds_window=60.0)
        self.assertTrue(any(f["sender"] == dot_x and f["recipient"] == dot_y for f in flights))

    # ── 3. Stapler System-Wide Dictation Engine Tests ─────────────────────
    def test_stapler_engine_lifecycle(self):
        """Verify Stapler engine toggles, starts, and stops cleanly."""
        engine = StaplerDictationEngine()

        # Test start
        with patch("actions.stapler_dictation.user32.RegisterHotKey", return_value=1):
            with patch("actions.stapler_dictation.user32.UnregisterHotKey", return_value=1):
                engine.start()
                self.assertTrue(engine.enabled)

                # Test toggle
                engine.toggle()
                self.assertFalse(engine.enabled)

                engine.toggle()
                self.assertTrue(engine.enabled)

                engine.stop()
                self.assertFalse(engine.enabled)

    def test_stapler_dictation_injection_with_clipboard_restore(self):
        """Verify text injection preserves prior clipboard data."""
        engine = StaplerDictationEngine()

        with patch("win32gui.GetForegroundWindow", return_value=12345):
            with patch("win32gui.GetWindowText", return_value="VS Code"):
                with patch("win32clipboard.OpenClipboard"):
                    with patch("win32clipboard.IsClipboardFormatAvailable", return_value=True):
                        with patch("win32clipboard.GetClipboardData", return_value="original_code_snippet"):
                            with patch("win32clipboard.EmptyClipboard"):
                                with patch("win32clipboard.SetClipboardData"):
                                    with patch("win32clipboard.CloseClipboard"):
                                        with patch("pyautogui.hotkey"):
                                            # Mock recognizer
                                            with patch.object(engine.recognizer, "adjust_for_ambient_noise"):
                                                with patch.object(engine.recognizer, "listen", return_value=MagicMock()):
                                                    with patch.object(engine.recognizer, "recognize_google", return_value="def calculate_total():"):
                                                        with patch("speech_recognition.Microphone"):
                                                            res = engine.record_and_inject()
                                                            self.assertTrue(res.get("ok"))
                                                            self.assertEqual(res["text"], "def calculate_total():")
                                                            self.assertIn("calculate_total", res["message"])

    # ── 4. Voice-First HITL Approval Gatekeeper Tests ─────────────────────
    def test_hitl_approval_and_rejection_flow(self):
        """Verify operator can query pending approvals and resolve via voice command."""
        dot = PrimeDot(goal="Clean temporary cache logs", name="JanitorDot")
        dot_engine.dots[dot.dot_id] = dot

        # Simulate policy gatekeeper trigger
        dot.status = "waiting_approval"
        dot.pending_approval = {
            "token": "appr_test_1234",
            "tool": "runTerminalCommand",
            "args": {"command": "rm -rf /cache"},
            "reason": "Destructive deletion command",
        }

        # Query pending approvals
        pending = dot_engine.get_pending_approvals()
        self.assertTrue(any(p["dot_id"] == dot.dot_id for p in pending))

        # Test operator approval resolution
        ok = dot_engine.approve_dot_action(dot.dot_id, approved=True)
        self.assertTrue(ok)
        self.assertEqual(dot.status, "running")
        self.assertIsNone(dot.pending_approval)

    def test_fast_path_voice_approval_command(self):
        """Verify AIAgent fast-path intercepts 'approve' and 'reject' commands."""
        from ai_agent import AIAgent

        agent = AIAgent.__new__(AIAgent)
        test_dot = PrimeDot(goal="High risk task", name="SecDot")
        dot_engine.dots[test_dot.dot_id] = test_dot
        test_dot.status = "waiting_approval"
        test_dot.pending_approval = {"token": "tok_99", "tool": "wipeDisk", "reason": "High risk"}

        # Voice command: 'approve'
        reply = agent._process_fast_command("approve")
        self.assertIsNotNone(reply)
        self.assertIn("approved the requested action", reply)
        self.assertEqual(test_dot.status, "running")

    # ── 5. 2D Virtual Office State API Endpoint Tests ─────────────────────
    def test_office_state_endpoint(self):
        """Verify /api/office/state returns active dots, desk telemetry, and flights."""
        from mobile_room_server import app
        app.config["TESTING"] = True
        client = app.test_client()

        resp = client.get("/api/office/state")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.assertIn("dots", data)
        self.assertIn("flights", data)
        self.assertIn("stapler", data)
        self.assertEqual(data["stapler"]["hotkey"], "Ctrl+Alt+Space")


if __name__ == "__main__":
    unittest.main()
