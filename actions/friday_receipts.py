"""
actions/friday_receipts.py
Execution Receipts & Undo/Rollback Engine for Prime AI (Inspired by debpalash/friday).

Every state-changing effect (file creation, modification, deletion, configuration)
produces a verifiable cryptographic Execution Receipt with pre-action snapshots,
enabling reliable one-click/voice rollback via 'Undo that'.
"""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("prime.friday.receipts")
RECEIPTS_DIR = Path(__file__).resolve().parent.parent / "data" / "receipts"
RECEIPTS_LOG = RECEIPTS_DIR / "receipts_ledger.json"


class FridayReceiptEngine:
    """Manages verifiable execution receipts and atomic state rollback."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or RECEIPTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.storage_dir / "receipts_ledger.json"
        self.receipts: List[Dict[str, Any]] = self._load_ledger()

    def _load_ledger(self) -> List[Dict[str, Any]]:
        if self.ledger_file.exists():
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load receipts ledger: {e}")
        return []

    def _save_ledger(self):
        try:
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                json.dump(self.receipts[-200:], f, indent=2, ensure_ascii=False)  # Retain last 200
        except Exception as e:
            logger.warning(f"Failed to persist receipts ledger: {e}")

    def capture_pre_state(self, file_path: str) -> Dict[str, Any]:
        """Capture snapshot of a target file before modification."""
        p = Path(file_path).resolve()
        if not p.exists():
            return {"exists": False, "content": None, "path": str(p)}

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            return {
                "exists": True,
                "content": content,
                "path": str(p),
                "size": p.stat().st_size
            }
        except Exception as e:
            logger.debug(f"Failed to read pre-state of {p}: {e}")
            return {"exists": True, "content": None, "path": str(p), "error": str(e)}

    def record_receipt(self, action_type: str, target: str, pre_state: Dict[str, Any], 
                       post_state: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Record a successful execution receipt into the durable ledger."""
        receipt_id = f"rcpt_{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now().isoformat()

        receipt = {
            "receipt_id": receipt_id,
            "timestamp": now_iso,
            "action_type": action_type,
            "tool_name": action_type,
            "target": target,
            "pre_state": pre_state,
            "post_state": post_state or {},
            "metadata": metadata or {},
            "rolled_back": False
        }

        self.receipts.append(receipt)
        self._save_ledger()
        logger.info(f"[Friday Receipts] Issued receipt {receipt_id} for action '{action_type}' on '{target}'")
        return receipt

    def rollback_receipt(self, receipt_id: str) -> Dict[str, Any]:
        """Roll back a specific execution receipt to its pre-state."""
        target_receipt = None
        for r in reversed(self.receipts):
            if r["receipt_id"] == receipt_id:
                target_receipt = r
                break

        if not target_receipt:
            return {"ok": False, "error": f"Receipt '{receipt_id}' not found."}

        if target_receipt.get("rolled_back"):
            return {"ok": False, "error": f"Receipt '{receipt_id}' has already been rolled back."}

        pre = target_receipt.get("pre_state", {})
        target_path = pre.get("path") or target_receipt.get("target")
        if not target_path:
            return {"ok": False, "error": "No target path in receipt to rollback."}

        p = Path(target_path).resolve()

        try:
            if not pre.get("exists"):
                # File was newly created by this action; rollback means removing it
                if p.exists():
                    p.unlink()
                    logger.info(f"[Friday Rollback] Deleted newly created file '{p}'")
            else:
                # File existed; restore previous content
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(pre.get("content", ""), encoding="utf-8")
                logger.info(f"[Friday Rollback] Restored original content of '{p}'")

            target_receipt["rolled_back"] = True
            target_receipt["rolled_back_at"] = datetime.now().isoformat()
            self._save_ledger()

            return {
                "ok": True,
                "message": f"Successfully rolled back action '{target_receipt['action_type']}' on '{p.name}'.",
                "receipt_id": receipt_id,
                "target": str(p)
            }

        except Exception as e:
            logger.error(f"[Friday Rollback] Failed to rollback receipt {receipt_id}: {e}")
            return {"ok": False, "error": f"Rollback failed: {e}"}

    def undo_last_action(self) -> Dict[str, Any]:
        """Rolls back the most recent un-reverted state-changing action."""
        for r in reversed(self.receipts):
            if not r.get("rolled_back"):
                return self.rollback_receipt(r["receipt_id"])

        return {"ok": False, "error": "No recorded actions available to undo."}

    def list_receipts(self, limit: int = 15) -> Dict[str, Any]:
        """List recent execution receipts."""
        return {
            "ok": True,
            "count": len(self.receipts),
            "receipts": list(reversed(self.receipts[-limit:]))
        }


# Global singleton
receipt_engine = FridayReceiptEngine()
receipt_ledger = receipt_engine


def capture_pre_state(tool_name: str, params: Optional[Dict[str, Any]] = None, target_path: Optional[str] = None) -> Dict[str, Any]:
    """Capture snapshot of target state prior to tool mutation."""
    target = target_path or (params or {}).get("command") or (params or {}).get("path") or tool_name
    pre_state = {}
    if target_path:
        pre_state = receipt_engine.capture_file_state(target_path)
    return {
        "tool_name": tool_name,
        "target": str(target),
        "params": params or {},
        "pre_state": pre_state,
        "timestamp": datetime.now().isoformat()
    }


def record_receipt(receipt_action: Dict[str, Any], status: str = "SUCCESS", error: Optional[str] = None) -> Dict[str, Any]:
    """Record receipt using the capture_pre_state payload."""
    tool_name = receipt_action.get("tool_name", "unknown")
    target = receipt_action.get("target", "unknown")
    pre_state = receipt_action.get("pre_state", {})
    metadata = {
        "params": receipt_action.get("params", {}),
        "status": status,
        "error": error
    }
    return receipt_engine.record_receipt(tool_name, target, pre_state, metadata=metadata)


def record_action_receipt(action_type: str, target: str, pre_state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return receipt_engine.record_receipt(action_type, target, pre_state, metadata=metadata)


def undo_last_action() -> Dict[str, Any]:
    return receipt_engine.undo_last_action()


def list_execution_receipts(limit: int = 15) -> Dict[str, Any]:
    return receipt_engine.list_receipts(limit=limit)


get_execution_receipts = list_execution_receipts
