"""
AgentWork / Collagent: Autonomous Worker Agent & Labor Marketplace Bidding Engine
Scans open bounties/tasks, scores capability matching against Prime's 279 specialized agents,
submits identity-bound bids with stakes and time estimates, and packages verifiable deliveries.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Prime.AgentWork.Worker")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "agentwork")
BIDS_FILE = os.path.join(DATA_DIR, "agent_bids.json")
DELIVERIES_FILE = os.path.join(DATA_DIR, "work_deliveries.json")


def _ensure_worker_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(BIDS_FILE):
        with open(BIDS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
    if not os.path.exists(DELIVERIES_FILE):
        with open(DELIVERIES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)


class AgentWorkerEngine:
    """Autonomous labor agent that scans, bids on, and delivers decentralized AI tasks."""

    def __init__(self, bids_path: Optional[str] = None, deliveries_path: Optional[str] = None):
        _ensure_worker_storage()
        self.bids_path = bids_path or BIDS_FILE
        self.deliveries_path = deliveries_path or DELIVERIES_FILE

    def _load_bids(self) -> Dict[str, Dict[str, Any]]:
        try:
            if os.path.exists(self.bids_path):
                with open(self.bids_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading bids: {e}")
        return {}

    def _save_bids(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self.bids_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_deliveries(self) -> Dict[str, Dict[str, Any]]:
        try:
            if os.path.exists(self.deliveries_path):
                with open(self.deliveries_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading deliveries: {e}")
        return {}

    def _save_deliveries(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self.deliveries_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def evaluate_task_feasibility(self, required_skills: List[str], max_budget_usdc: float) -> Dict[str, Any]:
        """
        Calculates match score (0-100) based on Prime's known core specializations:
        e.g., python, backend, fullstack, smart_contracts, ai, security, testing, data.
        """
        core_skills = {
            "python": 0.98,
            "backend": 0.95,
            "api": 0.95,
            "solidity": 0.88,
            "smart_contracts": 0.88,
            "evm": 0.90,
            "testing": 0.95,
            "security": 0.92,
            "ai": 0.96,
            "rag": 0.95,
            "devops": 0.85,
            "git": 0.98,
            "database": 0.92,
        }

        matched = []
        score_accum = 0.0

        if not required_skills:
            match_score = 85.0
        else:
            for skill in required_skills:
                norm = skill.strip().lower()
                weight = core_skills.get(norm, 0.75)
                score_accum += weight
                matched.append({"skill": skill, "competency": weight})
            match_score = round(min(100.0, (score_accum / len(required_skills)) * 100), 1)

        recommended_stake = round(max(5.0, max_budget_usdc * 0.1), 2)
        recommended_bid = round(max_budget_usdc * 0.9, 2)

        return {
            "match_score": match_score,
            "is_feasible": match_score >= 60.0,
            "matched_skills": matched,
            "recommended_bid_usdc": recommended_bid,
            "recommended_stake_usdc": recommended_stake,
        }

    def place_labor_bid(
        self,
        task_id: str,
        bid_amount_usdc: float,
        stake_amount_usdc: float,
        estimated_hours: float,
        proposal_pitch: str,
        worker_agent_id: str = "Prime-Labor-Node-01",
    ) -> Dict[str, Any]:
        """Submits an identity-bound bid with crypto stake commitment."""
        bids = self._load_bids()
        salt = f"{task_id}_{worker_agent_id}_{time.time()}"
        bid_id = f"bid_{hashlib.sha256(salt.encode('utf-8')).hexdigest()[:12]}"

        bid_record = {
            "bid_id": bid_id,
            "task_id": task_id,
            "worker_agent_id": worker_agent_id,
            "bid_amount_usdc": float(bid_amount_usdc),
            "stake_amount_usdc": float(stake_amount_usdc),
            "estimated_hours": float(estimated_hours),
            "proposal_pitch": proposal_pitch,
            "status": "SUBMITTED",
            "created_at": time.time(),
        }

        bids[bid_id] = bid_record
        self._save_bids(bids)
        logger.info(f"Submitted bid '{bid_id}' for task '{task_id}' (Amount: {bid_amount_usdc} USDC)")
        return {"status": "success", "bid": bid_record}

    def package_delivery(
        self,
        task_id: str,
        bid_id: str,
        git_commit_sha: str,
        delivery_summary: str,
        artifact_uris: List[str],
        worker_agent_id: str = "Prime-Labor-Node-01",
    ) -> Dict[str, Any]:
        """Packages completed task into a verifiable delivery bundle ready for sandbox verifiers."""
        deliveries = self._load_deliveries()
        salt = f"{task_id}_{git_commit_sha}_{time.time()}"
        delivery_id = f"del_{hashlib.sha256(salt.encode('utf-8')).hexdigest()[:12]}"

        delivery_record = {
            "delivery_id": delivery_id,
            "task_id": task_id,
            "bid_id": bid_id,
            "worker_agent_id": worker_agent_id,
            "git_commit_sha": git_commit_sha,
            "delivery_summary": delivery_summary,
            "artifact_uris": artifact_uris,
            "status": "SUBMITTED_FOR_VERIFICATION",
            "delivered_at": time.time(),
        }

        deliveries[delivery_id] = delivery_record
        self._save_deliveries(deliveries)

        # Update bid status to DELIVERED
        bids = self._load_bids()
        if bid_id in bids:
            bids[bid_id]["status"] = "DELIVERED"
            self._save_bids(bids)

        logger.info(f"Packaged delivery '{delivery_id}' for task '{task_id}' commit {git_commit_sha[:8]}")
        return {"status": "success", "delivery": delivery_record}

    def list_my_bids(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        bids = self._load_bids()
        results = list(bids.values())
        if status:
            results = [b for b in results if b.get("status") == status.upper()]
        return results

    def get_delivery(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        deliveries = self._load_deliveries()
        return deliveries.get(delivery_id)
