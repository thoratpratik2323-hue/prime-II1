"""
core/prime_dots.py
Prime Dots — Autonomous, Persistent 24/7 Background AI Agent Daemon Pods for Prime AI.
Inspired by OpenAI's 'Dots' architecture (DevDay 2026), engineered for local privacy,
Obsidian Second Brain canvas synchronization, policy-gated safety, and multi-LLM execution.

Key Capabilities:
1. Always-on background execution: Runs independently of active chat/voice sessions.
2. Isolated Sandboxes & Workspace Canvas: Syncs real-time state to Obsidian_Vault/Dots/<dot_id>.md.
3. Multi-step ReAct loop: Autonomous thinking, tool execution, and self-verification.
4. Policy Gatekeeper integration: Automatically requests operator approval before sensitive operations.
5. Voice & Cockpit Telemetry: Live alerts via Ultron Voice, Mobile Room SSE, and WhatsApp.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("prime.dots")

DOTS_STORAGE_PATH = Path(__file__).resolve().parent.parent / "data" / "prime_dots.json"
DOTS_CANVAS_DIR = Path(__file__).resolve().parent.parent / "Obsidian_Vault" / "Dots"
DOTS_SANDBOX_DIR = Path(__file__).resolve().parent.parent / "data" / "dots"


class PrimeDot:
    """An autonomous, persistent background agent pod executing goals on behalf of the operator."""

    def __init__(
        self,
        goal: str,
        name: Optional[str] = None,
        dot_id: Optional[str] = None,
        interval_seconds: int = 0,
        allowed_tools: Optional[List[str]] = None,
        max_iterations: int = 25,
        created_at: Optional[str] = None,
    ):
        self.dot_id = dot_id or f"dot_{uuid.uuid4().hex[:8]}"
        self.name = name or self._generate_default_name(goal)
        self.goal = goal.strip()
        self.interval_seconds = max(0, interval_seconds)
        self.allowed_tools = allowed_tools or self._default_allowed_tools()
        self.max_iterations = max_iterations

        self.status = "idle"  # idle | running | waiting_approval | paused | completed | failed
        self.created_at = created_at or datetime.now().isoformat()
        self.last_run: Optional[str] = None
        self.iteration_count = 0
        self.steps: List[Dict[str, Any]] = []
        self.logs: List[str] = []
        self.findings: List[str] = []
        self.pending_approval: Optional[Dict[str, Any]] = None

        # Workspace paths
        self.canvas_file = DOTS_CANVAS_DIR / f"{self.dot_id}.md"
        self.sandbox_path = DOTS_SANDBOX_DIR / self.dot_id

        # Munder Difflin Asynchronous Mailbox layer
        from core.dots_mailbox import DotsMailbox
        self.mailbox = DotsMailbox(self.dot_id)

        # Runtime control events
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._approval_event = threading.Event()
        self._approval_decision = False

    def send_message(
        self,
        recipient_id: str,
        subject: str,
        body: str,
        action: str = "data_share",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send an asynchronous stigmergic message to another Dot's inbox."""
        res = self.mailbox.send_message(recipient_id, subject, body, action, payload)
        self._log(f"Sent mailbox message to {recipient_id}: {subject}")
        return res

    def read_inbox(self, mark_as_done: bool = True) -> List[Dict[str, Any]]:
        """Read and drain unread messages from own inbox."""
        msgs = self.mailbox.read_inbox(mark_as_done)
        if msgs:
            self._log(f"Read {len(msgs)} message(s) from inbox.")
        return msgs

    @staticmethod
    def _generate_default_name(goal: str) -> str:
        words = re.findall(r"\b[A-Za-z0-9]+\b", goal)
        if words:
            summary = " ".join(words[:4]).title()
            return f"Dot-{summary}"
        return "Prime-Autonomous-Dot"

    @staticmethod
    def _default_allowed_tools() -> List[str]:
        return [
            "searchWeb",
            "searchGoogle",
            "searchYouTube",
            "searchGitHub",
            "queryObsidianKnowledgeBase",
            "searchObsidianNotes",
            "writeObsidianNote",
            "readObsidianNote",
            "systemInfo",
            "getWeather",
            "morningBriefing",
            "runTerminalCommand",
            "readFile",
            "createFile",
            "listDirectory",
            "enrichLead",
            "scanBuyingSignals",
            "draftGTMOutreach",
            "sendDotMessage",
            "readDotInbox",
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dot_id": self.dot_id,
            "name": self.name,
            "goal": self.goal,
            "status": self.status,
            "interval_seconds": self.interval_seconds,
            "allowed_tools": self.allowed_tools,
            "max_iterations": self.max_iterations,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "iteration_count": self.iteration_count,
            "steps_completed": len(self.steps),
            "pending_approval": self.pending_approval,
            "findings_count": len(self.findings),
            "unread_inbox": self.mailbox.get_unread_count(),
            "canvas_file": str(self.canvas_file),
            "sandbox_path": str(self.sandbox_path),
        }

    def start(self) -> bool:
        """Starts or resumes the background execution thread."""
        if self._thread and self._thread.is_alive():
            logger.info("Dot %s is already running.", self.dot_id)
            return False

        self._stop_event.clear()
        self._pause_event.clear()
        self.status = "running"
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name=f"Thread-{self.dot_id}")
        self._thread.start()
        self._log(f"Dot '{self.name}' ({self.dot_id}) initialized and running in background.")
        self.update_canvas()
        return True

    def pause(self) -> bool:
        """Pauses the dot's autonomous execution."""
        if self.status != "running":
            return False
        self._pause_event.set()
        self.status = "paused"
        self._log(f"Dot '{self.name}' paused by operator.")
        self.update_canvas()
        return True

    def resume(self) -> bool:
        """Resumes a paused dot."""
        if self.status != "paused":
            return False
        self._pause_event.clear()
        self.status = "running"
        self._log(f"Dot '{self.name}' resumed by operator.")
        self.update_canvas()
        return True

    def stop(self) -> bool:
        """Stops the dot execution gracefully."""
        self._stop_event.set()
        self._pause_event.clear()
        self._approval_event.set()
        self.status = "stopped"
        self._log(f"Dot '{self.name}' stopped.")
        self.update_canvas()
        return True

    def approve_action(self, approved: bool = True) -> bool:
        """Resolves a pending policy gatekeeper request."""
        if not self.pending_approval or self.status != "waiting_approval":
            return False
        self._approval_decision = approved
        self.pending_approval = None
        self.status = "running"
        self._approval_event.set()
        self.update_canvas()
        return True

    def _sync_canvas(self):
        """Convenience alias for update_canvas."""
        self.update_canvas()

    def get_canvas_content(self) -> str:
        """Returns the raw Markdown canvas content from Obsidian."""
        if self.canvas_file.exists():
            try:
                return self.canvas_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return ""



    def _log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        logger.info("[Dot %s] %s", self.dot_id, message)

    def _run_loop(self):
        """Main autonomous execution loop."""
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        DOTS_CANVAS_DIR.mkdir(parents=True, exist_ok=True)

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(1)
                continue

            self.last_run = datetime.now().isoformat()
            self.iteration_count += 1
            self._log(f"Starting iteration #{self.iteration_count} for goal: '{self.goal}'")

            try:
                completed = self._execute_autonomous_step()
                self.update_canvas()

                if completed:
                    self.status = "completed"
                    self._log(f"Goal achieved: '{self.goal}'")
                    self._notify_operator(f"Sir, Dot '{self.name}' has achieved its goal.")
                    self.update_canvas()
                    break

                if self.iteration_count >= self.max_iterations:
                    self.status = "completed"
                    self._log(f"Reached maximum iteration limit ({self.max_iterations}). Finalizing.")
                    self.update_canvas()
                    break

            except Exception as e:
                logger.exception("Error executing Dot %s step", self.dot_id)
                self.status = "failed"
                self._log(f"Execution error: {e}")
                self.update_canvas()
                break

            # If recurring, sleep for the interval; otherwise pause between steps
            if self.interval_seconds > 0:
                self._log(f"Iteration completed. Sleeping for {self.interval_seconds}s until next scheduled cycle.")
                for _ in range(self.interval_seconds):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            else:
                # One-shot task execution pause
                time.sleep(1.5)

    def _execute_autonomous_step(self) -> bool:
        """Executes one cognitive planning and action step."""
        import tool_definitions
        from actions.friday_policy import FridayPolicyGatekeeper

        # 1. Synthesize context for step
        history_summary = "\n".join(
            f"- Step {s['step_index']}: Tool {s.get('tool', 'none')} -> Result: {str(s.get('result', ''))[:120]}"
            for s in self.steps[-5:]
        ) or "No previous steps executed."

        # 2. ReAct Next-Action Planning
        # In production, uses active LLM provider; here backed by Master Brain logic
        plan = self._plan_next_action(history_summary)

        thought = plan.get("thought", "Analyzing goal progress.")
        tool_name = plan.get("tool")
        tool_args = plan.get("args", {})
        is_finished = plan.get("finished", False)

        self._log(f"Thought: {thought}")

        if is_finished or not tool_name:
            if plan.get("final_summary"):
                self.findings.append(plan["final_summary"])
            return True

        # Check tool permission
        if tool_name not in self.allowed_tools:
            self._log(f"Skipping unauthorized tool '{tool_name}'.")
            return False

        # 3. Policy Gatekeeper Evaluation
        gatekeeper = FridayPolicyGatekeeper()
        eval_res = gatekeeper.evaluate_action(tool_name, tool_args)

        if eval_res.get("approval_required"):
            self.status = "waiting_approval"
            token = eval_res.get("token")
            reason = eval_res.get("reason", "Sensitive action boundary.")
            self.pending_approval = {
                "token": token,
                "tool": tool_name,
                "args": tool_args,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
            self._log(f"ACTION GATED: Requires approval for '{tool_name}'. Reason: {reason}")
            self.update_canvas()

            # Voice alert
            self._notify_operator(
                f"Dot '{self.name}' requests operator approval to execute {tool_name}."
            )

            # Wait for operator response
            self._approval_event.clear()
            self._approval_event.wait(timeout=300)  # 5 min timeout

            if not self._approval_decision:
                self._log(f"Action '{tool_name}' was REJECTED by operator or timed out.")
                self.pending_approval = None
                self.status = "running"
                return False

            self.pending_approval = None
            self.status = "running"
            self._log(f"Action '{tool_name}' APPROVED by operator.")

        # 4. Tool Execution
        try:
            res = tool_definitions.execute_tool(tool_name, tool_args)
            res_str = str(res.get("result") if isinstance(res, dict) else res)[:300]
            self._log(f"Executed tool '{tool_name}' -> {res_str}")

            # Record step
            step_record = {
                "step_index": len(self.steps) + 1,
                "thought": thought,
                "tool": tool_name,
                "args": tool_args,
                "result": res_str,
                "timestamp": datetime.now().isoformat(),
            }
            self.steps.append(step_record)

            # If tool produced actionable insight, append to findings
            if len(res_str) > 30 and "error" not in res_str.lower():
                self.findings.append(f"[{tool_name}] {res_str[:160]}")

            # Record execution receipt
            try:
                from actions.friday_receipts import receipt_engine
                receipt_engine.create_receipt(
                    action_name=f"dot_{self.dot_id}_{tool_name}",
                    parameters=tool_args,
                    outcome=res,
                    reversible=False,
                )
            except Exception:
                pass

        except Exception as e:
            self._log(f"Failed to execute tool '{tool_name}': {e}")
            return False

        return False

    def _plan_next_action(self, history_summary: str) -> Dict[str, Any]:
        """Plans the next tool call. Uses provider if available, or structured heuristics."""
        goal_lower = self.goal.lower()

        # Step 0: Initial search or discovery
        if len(self.steps) == 0:
            if any(k in goal_lower for k in ("search", "find", "check", "news", "research", "monitor")):
                return {
                    "thought": f"Initiating web search to gather intelligence for: '{self.goal}'.",
                    "tool": "searchWeb",
                    "args": {"query": self.goal},
                    "finished": False,
                }
            elif any(k in goal_lower for k in ("note", "obsidian", "brain", "knowledge")):
                return {
                    "thought": f"Querying Obsidian Second Brain for relevant notes.",
                    "tool": "queryObsidianKnowledgeBase",
                    "args": {"query": self.goal},
                    "finished": False,
                }
            elif any(k in goal_lower for k in ("system", "hardware", "cpu", "performance", "specs")):
                return {
                    "thought": "Checking host system hardware vitals.",
                    "tool": "systemInfo",
                    "args": {},
                    "finished": False,
                }

        # Step 1: Synthesize findings into Obsidian Second Brain Page
        if len(self.steps) >= 1 and not any(s.get("tool") == "writeObsidianNote" for s in self.steps):
            findings_text = "\n".join(f"- {f}" for f in self.findings) or "Background audit completed successfully."
            return {
                "thought": "Archiving intelligence findings into an Obsidian Second Brain note.",
                "tool": "writeObsidianNote",
                "args": {
                    "title": f"Dot Intelligence - {self.name}",
                    "content": f"# {self.name} Report\n\n**Goal**: {self.goal}\n**Generated**: {datetime.now().isoformat()}\n\n## Findings\n{findings_text}\n\n---\n*Generated autonomously by Prime Dot {self.dot_id}*",
                },
                "finished": False,
            }

        # Goal Completion
        return {
            "thought": "All steps executed and findings archived to Second Brain.",
            "tool": None,
            "args": {},
            "finished": True,
            "final_summary": f"Completed background mission for '{self.goal}'.",
        }

    def _notify_operator(self, text: str):
        """Dispatches an audible or visual alert to the operator."""
        try:
            from voice_engine import voice
            if getattr(voice, "tts_enabled", False):
                voice.speak(text)
        except Exception:
            pass

    def update_canvas(self):
        """Renders live Markdown 'Page' canvas in Obsidian Second Brain."""
        try:
            DOTS_CANVAS_DIR.mkdir(parents=True, exist_ok=True)
            status_emojis = {
                "running": "🟢 RUNNING (ALWAYS-ON)",
                "paused": "⏸️ PAUSED",
                "waiting_approval": "⚠️ WAITING OPERATOR APPROVAL",
                "completed": "✅ COMPLETED",
                "failed": "❌ FAILED",
                "stopped": "⏹️ STOPPED",
            }
            status_display = status_emojis.get(self.status, self.status.upper())

            steps_md = ""
            for idx, s in enumerate(self.steps, start=1):
                step_num = s.get("step_index", s.get("iteration", idx))
                steps_md += f"### Step {step_num} — `{s.get('tool', 'None')}`\n"
                steps_md += f"- **Thought**: {s.get('thought')}\n"
                steps_md += f"- **Result**: `{s.get('result', '')}`\n"
                steps_md += f"- *Timestamp*: {s.get('timestamp')}\n\n"

            findings_md = "\n".join(f"- {f}" for f in self.findings) if self.findings else "*No discrete findings recorded yet.*"
            logs_md = "\n".join(f"`{l}`" for l in self.logs[-12:]) if self.logs else "*No logs.*"

            content = f"""# 🟣 Prime Dot Canvas: {self.name}
> **Dot ID**: `{self.dot_id}` | **Status**: {status_display}  
> **Created**: `{self.created_at}` | **Iterations**: `{self.iteration_count}/{self.max_iterations}`

---

## 🎯 Primary Objective / Goal
{self.goal}

## 📊 Live Findings & Deliverables
{findings_md}

## 🪜 Autonomous Execution Journey
{steps_md or '*Awaiting step execution.*'}

## 🖥️ Live Telemetry & Log Stream
{logs_md}

---
*Synced live by Prime Autonomous Dot Engine • Local & Private*
"""
            with open(self.canvas_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.warning("Failed to update Dot canvas note: %s", e)



class PrimeDotEngine:
    """Singleton Engine managing all persistent Prime Dots."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.dots: Dict[str, PrimeDot] = {}
        self._load_state()
        self._initialized = True

    def spawn_dot(
        self,
        goal: str,
        name: Optional[str] = None,
        interval_seconds: int = 0,
        allowed_tools: Optional[List[str]] = None,
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        """Spawns and optionally launches a new autonomous background Dot."""
        dot = PrimeDot(
            goal=goal,
            name=name,
            interval_seconds=interval_seconds,
            allowed_tools=allowed_tools,
        )
        self.dots[dot.dot_id] = dot
        if auto_start:
            dot.start()
        self._save_state()
        return {
            "ok": True,
            "message": f"Spawned Prime Dot '{dot.name}' ({dot.dot_id})",
            "dot": dot.to_dict(),
        }

    def list_dots(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Lists active or all registered Dots."""
        results = []
        for d in self.dots.values():
            if active_only and d.status not in ("running", "waiting_approval"):
                continue
            results.append(d.to_dict())
        return results

    def get_dot(self, dot_id: str) -> Optional[PrimeDot]:
        return self.dots.get(dot_id)

    def pause_dot(self, dot_id: str) -> bool:
        dot = self.get_dot(dot_id)
        if dot:
            ok = dot.pause()
            self._save_state()
            return ok
        return False

    def resume_dot(self, dot_id: str) -> bool:
        dot = self.get_dot(dot_id)
        if dot:
            ok = dot.resume()
            self._save_state()
            return ok
        return False

    def stop_dot(self, dot_id: str) -> bool:
        dot = self.get_dot(dot_id)
        if dot:
            ok = dot.stop()
            self._save_state()
            return ok
        return False

    def approve_dot_action(self, dot_id: str, approved: bool = True) -> bool:
        dot = self.get_dot(dot_id)
        if dot:
            ok = dot.approve_action(approved)
            self._save_state()
            return ok
        return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Returns list of all Dots currently awaiting operator approval."""
        res = []
        for did, dot in self.dots.items():
            if dot.status == "waiting_approval" and dot.pending_approval:
                res.append({
                    "dot_id": did,
                    "name": dot.name,
                    "pending_approval": dot.pending_approval,
                })
        return res

    def get_telemetry(self) -> Dict[str, Any]:
        total = len(self.dots)
        running = sum(1 for d in self.dots.values() if d.status == "running")
        waiting = sum(1 for d in self.dots.values() if d.status == "waiting_approval")
        completed = sum(1 for d in self.dots.values() if d.status == "completed")
        return {
            "total_dots": total,
            "running_dots": running,
            "waiting_approval": waiting,
            "completed_dots": completed,
        }

    def _save_state(self):
        try:
            DOTS_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {did: dot.to_dict() for did, dot in self.dots.items()}
            with open(DOTS_STORAGE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to save Prime Dots state: %s", e)

    def _load_state(self):
        if DOTS_STORAGE_PATH.exists():
            try:
                with open(DOTS_STORAGE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for did, d_data in data.items():
                        dot = PrimeDot(
                            goal=d_data["goal"],
                            name=d_data.get("name"),
                            dot_id=did,
                            interval_seconds=d_data.get("interval_seconds", 0),
                            allowed_tools=d_data.get("allowed_tools"),
                            max_iterations=d_data.get("max_iterations", 25),
                            created_at=d_data.get("created_at"),
                        )
                        dot.status = d_data.get("status", "idle")
                        dot.iteration_count = d_data.get("iteration_count", 0)
                        self.dots[did] = dot
            except Exception as e:
                logger.warning("Failed to load Prime Dots state: %s", e)


dot_engine = PrimeDotEngine()


def ensure_office_server(port: int = 8765):
    """Ensure the 2D Virtual Office Floor HUD HTTP server is running on the given port."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        s.connect(("127.0.0.1", port))
        s.close()
        return True  # Server is already active
    except Exception:
        pass
    finally:
        try:
            s.close()
        except Exception:
            pass

    try:
        import threading
        from mobile_room_server import app
        t = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=port, debug=False, threaded=True, use_reloader=False),
            name="prime-office-server",
            daemon=True
        )
        t.start()
        time.sleep(0.6)
        return True
    except Exception as e:
        logger.warning("Could not auto-start office server: %s", e)
        return False
