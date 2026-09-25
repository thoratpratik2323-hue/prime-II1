"""
prime_traces.py — Trace-Based Continual Learning & Reflection Engine.
Inherited from OpenJarvis trace feedback and execution evaluation loop.

Logs detailed step-by-step traces for every user command, evaluates execution quality,
and automatically extracts self-improving lessons into the continual harness.
"""

from __future__ import annotations

import os
import sys
import time
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from rich.console import Console
from rich.table import Table

console = Console()

BASE_DIR = Path(__file__).parent
MEMORY_DIR = BASE_DIR / "memory"
TRACES_FILE = MEMORY_DIR / "execution_traces.jsonl"


class TraceLogger:
    """Logs and analyzes agent execution traces."""

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def start_trace(self, user_input: str, source: str = "voice") -> Dict[str, Any]:
        """Initialize a new interaction trace."""
        return {
            "trace_id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "start_time": time.time(),
            "source": source,
            "user_input": user_input,
            "tools_called": [],
            "status": "in_progress",
            "error": None,
            "response": "",
            "duration_ms": 0.0,
        }

    def record_tool_call(self, trace: Dict[str, Any], tool_name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Append tool call details to active trace."""
        if not trace:
            return
        ok = result.get("ok", True) if isinstance(result, dict) else True
        trace["tools_called"].append({
            "tool": tool_name,
            "args": args,
            "success": ok,
            "result_preview": str(result)[:150]
        })

    def end_trace(self, trace: Dict[str, Any], response: str = "", error: Optional[str] = None) -> Dict[str, Any]:
        """Finalize and persist trace, detecting reflections."""
        if not trace:
            return {}

        trace["duration_ms"] = round((time.time() - trace["start_time"]) * 1000, 1)
        trace["response"] = response[:200]
        trace["error"] = error
        trace["status"] = "failed" if error else "success"

        # Check if any tool failed
        any_tool_failed = any(not tc["success"] for tc in trace.get("tools_called", []))
        if any_tool_failed:
            trace["status"] = "partial_failure"

        # Append to JSONL log
        try:
            with open(TRACES_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace, ensure_ascii=False) + "\n")
            self._maybe_compact_traces()
        except Exception:
            pass

        # Automatic reflection learning: if failure occurred, feed into continual harness
        if any_tool_failed or error:
            self._auto_reflect_on_failure(trace)

        return trace

    def _maybe_compact_traces(self) -> None:
        """Compact trace file if it exceeds 2MB, keeping last 1,000 entries."""
        try:
            if not TRACES_FILE.exists() or TRACES_FILE.stat().st_size < 2 * 1024 * 1024:
                return
            from collections import deque
            with open(TRACES_FILE, "r", encoding="utf-8", errors="ignore") as f:
                recent = deque(f, maxlen=1000)
            temp_file = TRACES_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                f.writelines(recent)
            temp_file.replace(TRACES_FILE)
        except Exception:
            pass

    def _auto_reflect_on_failure(self, trace: Dict[str, Any]) -> None:
        """Extract a lesson and save to continual harness."""
        try:
            from prime_goal_harness import continual_harness
            for tc in trace.get("tools_called", []):
                if not tc["success"]:
                    topic = f"Tool Failure: {tc['tool']}"
                    insight = f"Command '{trace['user_input']}' failed with args {tc['args']}. Ensure parameters and fallback routing are validated."
                    continual_harness.record_lesson(topic, insight, source="trace_reflection_loop")
        except Exception:
            pass

    def get_recent_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent execution traces using bounded streaming deque."""
        if not TRACES_FILE.exists():
            return []
        traces = []
        try:
            from collections import deque
            with open(TRACES_FILE, "r", encoding="utf-8", errors="ignore") as f:
                tail = deque(f, maxlen=limit)
                for line in tail:
                    line = line.strip()
                    if line:
                        traces.append(json.loads(line))
        except Exception:
            pass
        return list(reversed(traces))

    def render_traces_table(self, limit: int = 8) -> Table:
        """Render Rich table of recent traces."""
        traces = self.get_recent_traces(limit)
        table = Table(title=f"⚡ OPENJARVIS TRACE FEEDBACK LOOP ({len(traces)} Recent Traces)", border_style="bright_cyan")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Input", style="bold white", width=28)
        table.add_column("Tools Used", style="cyan", width=22)
        table.add_column("Latency", justify="right", style="magenta", width=10)
        table.add_column("Status", justify="center", width=12)

        for t in traces:
            tools_str = ", ".join(tc["tool"] for tc in t.get("tools_called", [])) or "direct_llm"
            lat_str = f"{t.get('duration_ms', 0):.0f}ms"
            status = t.get("status", "success")
            if status == "success":
                status_badge = "[green]✓ SUCCESS[/green]"
            elif status == "partial_failure":
                status_badge = "[yellow]⚠ PARTIAL[/yellow]"
            else:
                status_badge = "[red]✗ FAILED[/red]"

            table.add_row(
                t.get("trace_id", "-"),
                t.get("user_input", "")[:26],
                tools_str[:20],
                lat_str,
                status_badge
            )

        return table


trace_logger = TraceLogger()
