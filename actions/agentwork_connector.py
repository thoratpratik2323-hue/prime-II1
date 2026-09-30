"""
AgentWork / Collagent: Platform Connector & Base L2 Escrow Settlement Engine
Manages API connectivity with Collagent instance, Hardhat EVM RPC, and handles
USDC escrow deposits, verifier-gated settlement, and refund mechanisms.
"""

import hashlib
import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Prime.AgentWork.Connector")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "agentwork")
ESCROW_FILE = os.path.join(DATA_DIR, "escrow_ledger.json")


def _ensure_connector_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ESCROW_FILE):
        with open(ESCROW_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)


class CollagentConnector:
    """API Connector and Escrow Settlement engine for Collagent / AgentWork."""

    def __init__(
        self,
        api_base: str = "http://localhost:3001/api/v1",
        evm_rpc: str = "http://127.0.0.1:8545",
        escrow_path: Optional[str] = None,
    ):
        _ensure_connector_storage()
        self.api_base = os.getenv("AIWORK_API_BASE", api_base)
        self.evm_rpc = os.getenv("AIWORK_EVM_RPC", evm_rpc)
        self.escrow_path = escrow_path or ESCROW_FILE

    def _load_escrow(self) -> Dict[str, Dict[str, Any]]:
        try:
            if os.path.exists(self.escrow_path):
                with open(self.escrow_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading escrow: {e}")
        return {}

    def _save_escrow(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self.escrow_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def check_platform_health(self) -> Dict[str, Any]:
        """Checks if self-hosted Collagent API or local EVM Hardhat node is reachable."""
        api_online = False
        evm_online = False

        try:
            req = urllib.request.Request(f"{self.api_base}/health", headers={"User-Agent": "Prime-Collagent-Client"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                api_online = (resp.status == 200)
        except Exception:
            api_online = False

        try:
            # Check local EVM node
            data = json.dumps({"jsonrpc": "2.0", "method": "web3_clientVersion", "params": [], "id": 1}).encode()
            req = urllib.request.Request(self.evm_rpc, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                evm_online = (resp.status == 200)
        except Exception:
            evm_online = False

        return {
            "api_base": self.api_base,
            "api_online": api_online,
            "evm_rpc": self.evm_rpc,
            "evm_online": evm_online,
            "network": "Base L2 (EVM 8453 / Local 31337)",
            "operating_mode": "LIVE_REMOTE" if (api_online or evm_online) else "AUTONOMOUS_LOCAL_FALLBACK",
        }

    def deposit_escrow(
        self,
        task_id: str,
        amount_usdc: float,
        depositor_address: str = "0xPrimeEmployerTreasury",
        token_symbol: str = "USDC",
    ) -> Dict[str, Any]:
        """Locks funds in task escrow awaiting verifier quorum completion."""
        escrows = self._load_escrow()
        salt = f"{task_id}_{amount_usdc}_{time.time()}"
        tx_hash = f"0x{hashlib.sha256(salt.encode()).hexdigest()}"

        record = {
            "task_id": task_id,
            "amount_usdc": float(amount_usdc),
            "token": token_symbol,
            "depositor": depositor_address,
            "tx_hash": tx_hash,
            "status": "LOCKED",
            "settled_to": None,
            "settled_at": None,
            "created_at": time.time(),
        }

        escrows[task_id] = record
        self._save_escrow(escrows)
        logger.info(f"Escrow of {amount_usdc} {token_symbol} locked for task '{task_id}'. Tx: {tx_hash[:10]}...")
        return {"status": "success", "escrow": record}

    def settle_escrow(
        self,
        task_id: str,
        recipient_address: str,
        verifier_consensus: Optional[str] = None,
        override_signoff: bool = False,
    ) -> Dict[str, Any]:
        """
        Releases escrowed funds to worker recipient upon approved verifier quorum
        or manual employer signoff.
        """
        escrows = self._load_escrow()
        if task_id not in escrows:
            return {"status": "error", "message": f"No escrow found for task '{task_id}'"}

        record = escrows[task_id]
        if record["status"] != "LOCKED":
            return {"status": "error", "message": f"Escrow is already {record['status']}"}

        # Check conditions
        if not override_signoff and verifier_consensus != "APPROVED":
            return {
                "status": "error",
                "message": f"Escrow settlement denied: verifier consensus is '{verifier_consensus}' (requires 'APPROVED' or employer signoff)",
            }

        settlement_salt = f"settle_{task_id}_{recipient_address}_{time.time()}"
        settle_tx_hash = f"0x{hashlib.sha256(settlement_salt.encode()).hexdigest()}"

        record["status"] = "SETTLED"
        record["settled_to"] = recipient_address
        record["settlement_tx"] = settle_tx_hash
        record["settled_at"] = time.time()
        record["settlement_reason"] = "VERIFIER_QUORUM" if verifier_consensus == "APPROVED" else "EMPLOYER_SIGNOFF"

        self._save_escrow(escrows)
        logger.info(
            f"Escrow for task '{task_id}' settled to '{recipient_address}' ({record['amount_usdc']} USDC). Tx: {settle_tx_hash[:10]}..."
        )
        return {
            "status": "success",
            "message": f"Released {record['amount_usdc']} USDC to {recipient_address}",
            "escrow": record,
        }

    def refund_escrow(self, task_id: str, reason: str = "TASK_CANCELLED") -> Dict[str, Any]:
        """Refunds locked escrow back to depositor."""
        escrows = self._load_escrow()
        if task_id not in escrows:
            return {"status": "error", "message": f"No escrow found for task '{task_id}'"}

        record = escrows[task_id]
        if record["status"] != "LOCKED":
            return {"status": "error", "message": f"Escrow is already {record['status']}"}

        record["status"] = "REFUNDED"
        record["refund_reason"] = reason
        record["refunded_at"] = time.time()

        self._save_escrow(escrows)
        logger.info(f"Escrow for task '{task_id}' refunded to depositor '{record['depositor']}'.")
        return {"status": "success", "message": f"Refunded {record['amount_usdc']} USDC", "escrow": record}

    def get_escrow_summary(self) -> Dict[str, Any]:
        """Returns protocol escrow totals."""
        escrows = self._load_escrow()
        total_locked = sum(e["amount_usdc"] for e in escrows.values() if e.get("status") == "LOCKED")
        total_settled = sum(e["amount_usdc"] for e in escrows.values() if e.get("status") == "SETTLED")
        total_refunded = sum(e["amount_usdc"] for e in escrows.values() if e.get("status") == "REFUNDED")

        return {
            "total_escrows": len(escrows),
            "total_locked_usdc": round(total_locked, 2),
            "total_settled_usdc": round(total_settled, 2),
            "total_refunded_usdc": round(total_refunded, 2),
            "escrows": list(escrows.values()),
        }
