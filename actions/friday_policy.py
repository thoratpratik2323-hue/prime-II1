"""
actions/friday_policy.py
Approval Boundary & Safety Policy Gatekeeper for Prime AI (Inspired by debpalash/friday).

Enforces exact risk policies between model output and physical execution:
- Tier 1: SAFE (read-only, search, status inspection) -> Auto-approved
- Tier 2: SENSITIVE (local file edits, safe tests, media playback) -> Approved with Execution Receipt
- Tier 3: HIGH_RISK / DESTRUCTIVE (file deletions, hard shell resets, format, process kills) -> Explicit Approval Required
"""

import json
import logging
import re
import secrets
import time
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("prime.friday.policy")


class FridayPolicyGatekeeper:
    """Evaluates requested tool actions against safety boundaries."""

    DESTRUCTIVE_COMMAND_PATTERNS = [
        re.compile(r"\brm\s+-(?:r|f|rf|fr)\b", re.IGNORECASE),
        re.compile(r"\brmdir\s+/[sS]\b", re.IGNORECASE),
        re.compile(r"\bdel\s+/[fFqQsS]\b", re.IGNORECASE),
        re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),
        re.compile(r"\bdrop\s+database\b", re.IGNORECASE),
        re.compile(r"\bshutdown\s+/[sSrR]\b", re.IGNORECASE),
        re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
        re.compile(r"\bgit\s+clean\s+-fdx?\b", re.IGNORECASE),
    ]

    HIGH_RISK_TOOLS: Set[str] = {
        "deleteFile",
        "dropDatabase",
        "forceKillProcess",
        "systemShutdown",
        "systemReboot"
    }

    def __init__(self):
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def evaluate_action(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate if a requested action can execute immediately or requires user approval.
        Returns safety assessment and approval token if gated.
        """
        args = params or {}
        name = tool_name.strip()

        # 1. Check explicit high risk tools
        if name in self.HIGH_RISK_TOOLS:
            return self._create_approval_request(name, args, "Tool is designated as HIGH_RISK / DESTRUCTIVE.")

        # 2. Check terminal commands for destructive shell syntax
        if name in ("runTerminalCommand", "terminal_command", "cmd"):
            cmd = str(args.get("command") or args.get("cmd") or "").strip()
            for pattern in self.DESTRUCTIVE_COMMAND_PATTERNS:
                if pattern.search(cmd):
                    return self._create_approval_request(
                        name, args, 
                        f"Command contains potentially destructive operation: '{cmd[:60]}'"
                    )

        # 3. Check file deletion patterns in generic tools
        if "delete" in name.lower() or "remove" in name.lower():
            return self._create_approval_request(name, args, "Operation removes persistent resources.")

        # Approved
        return {
            "ok": True,
            "status": "APPROVED",
            "risk_tier": "SAFE" if "read" in name.lower() or "get" in name.lower() or "search" in name.lower() else "SENSITIVE",
            "approval_required": False
        }

    def _create_approval_request(self, tool_name: str, params: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Generate a one-time approval card with security token."""
        token = f"appr_{secrets.token_hex(6)}"
        now = time.time()

        approval_record = {
            "token": token,
            "tool_name": tool_name,
            "params": params,
            "reason": reason,
            "created_at": now,
            "expires_at": now + 120  # 2 minute TTL
        }

        self.pending_approvals[token] = approval_record
        logger.warning(f"[Friday Policy] Gated HIGH_RISK action '{tool_name}': {reason}. Token: {token}")

        return {
            "ok": True,
            "status": "APPROVAL_REQUIRED",
            "risk_tier": "HIGH_RISK",
            "approval_required": True,
            "approval_token": token,
            "reason": reason,
            "card_ui": {
                "title": f"Action Approval Required: {tool_name}",
                "reason": reason,
                "token": token,
                "confirm_prompt": f"Say 'Approve {token}' or click Confirm to execute."
            }
        }

    def verify_approval(self, approval_token: str) -> Dict[str, Any]:
        """Validate if the provided approval token is valid and unexpired."""
        token = approval_token.strip()
        if token in self.pending_approvals:
            record = self.pending_approvals.pop(token)
            if time.time() <= record["expires_at"]:
                return {
                    "ok": True,
                    "approved": True,
                    "tool_name": record["tool_name"],
                    "params": record["params"]
                }
            return {"ok": False, "approved": False, "error": "Approval token has expired."}

        return {"ok": False, "approved": False, "error": "Invalid or already consumed approval token."}


# Global singleton
policy_gatekeeper = FridayPolicyGatekeeper()


def check_action_policy(tool_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return policy_gatekeeper.evaluate_action(tool_name, params=params)


def verify_action_approval(approval_token: str) -> Dict[str, Any]:
    return policy_gatekeeper.verify_approval(approval_token)
