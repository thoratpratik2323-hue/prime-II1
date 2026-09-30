"""
AgentWork / Collagent: Problem Charter & Workstream DAG Decomposer
Implements ProblemSpec v1 charters, algorithmic DAG workstream decomposition,
and content-digested artifact evidence ledger with SHA-256 provenance tracking.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Prime.AgentWork.Charter")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "agentwork")
CHARTERS_FILE = os.path.join(DATA_DIR, "problem_charters.json")
ARTIFACTS_FILE = os.path.join(DATA_DIR, "artifact_ledger.json")


def _ensure_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CHARTERS_FILE):
        with open(CHARTERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
    if not os.path.exists(ARTIFACTS_FILE):
        with open(ARTIFACTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


class ProblemCharterManager:
    """Manages ProblemSpec v1 charters and workstream DAGs."""

    def __init__(self, charters_path: Optional[str] = None, artifacts_path: Optional[str] = None):
        _ensure_storage()
        self.charters_path = charters_path or CHARTERS_FILE
        self.artifacts_path = artifacts_path or ARTIFACTS_FILE

    def _load_charters(self) -> Dict[str, Dict[str, Any]]:
        try:
            if os.path.exists(self.charters_path):
                with open(self.charters_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading charters: {e}")
        return {}

    def _save_charters(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self.charters_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def create_problem_charter(
        self,
        title: str,
        charter: str,
        acceptance_criteria: List[str],
        bounty_usdc: float = 0.0,
        scope: str = "GLOBAL",
        risk_level: str = "LOW",
        license_type: str = "MIT",
        creator_agent: str = "Prime-Coordinator",
    ) -> Dict[str, Any]:
        """Creates and stores a ProblemSpec v1 charter."""
        charters = self._load_charters()
        salt = f"{title}_{time.time()}_{bounty_usdc}"
        problem_id = f"prob_{hashlib.sha256(salt.encode('utf-8')).hexdigest()[:12]}"

        record = {
            "problem_id": problem_id,
            "version": "ProblemSpec-v1",
            "title": title,
            "charter": charter,
            "scope": scope.upper(),
            "risk_level": risk_level.upper(),
            "license": license_type,
            "acceptance_criteria": acceptance_criteria,
            "bounty_usdc": float(bounty_usdc),
            "creator_agent": creator_agent,
            "status": "OPEN",
            "workstreams": {},
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        charters[problem_id] = record
        self._save_charters(charters)
        logger.info(f"Created ProblemSpec v1 charter '{problem_id}': {title}")
        return {"status": "success", "problem": record}

    def decompose_into_workstream_dag(
        self,
        problem_id: str,
        workstreams: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Decomposes a problem into a DAG of workstreams.
        Each workstream item: {
            "key": "frontend",
            "title": "Build responsive React UI",
            "bounty_share_pct": 30.0,
            "dependencies": ["api_spec"]
        }
        Validates DAG for cycles.
        """
        charters = self._load_charters()
        if problem_id not in charters:
            return {"status": "error", "message": f"Problem charter '{problem_id}' not found"}

        charter = charters[problem_id]

        # Validate DAG dependencies and cycles
        keys = {ws.get("key") for ws in workstreams if ws.get("key")}
        if len(keys) != len(workstreams):
            return {"status": "error", "message": "Duplicate or missing workstream keys"}

        for ws in workstreams:
            deps = ws.get("dependencies", [])
            for d in deps:
                if d not in keys:
                    return {"status": "error", "message": f"Dependency '{d}' in workstream '{ws.get('key')}' does not exist"}

        # Cycle detection via topological sort
        in_degree = {k: 0 for k in keys}
        adj: Dict[str, List[str]] = {k: [] for k in keys}

        for ws in workstreams:
            k = ws["key"]
            for d in ws.get("dependencies", []):
                adj[d].append(k)
                in_degree[k] += 1

        queue = [k for k, deg in in_degree.items() if deg == 0]
        visited_count = 0
        execution_order = []

        while queue:
            node = queue.pop(0)
            execution_order.append(node)
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(keys):
            return {"status": "error", "message": "Cyclic dependency detected in workstream graph"}

        # Store workstreams
        formatted_workstreams: Dict[str, Any] = {}
        for ws in workstreams:
            k = ws["key"]
            bounty_pct = float(ws.get("bounty_share_pct", 0.0))
            allocated_usdc = round((bounty_pct / 100.0) * charter.get("bounty_usdc", 0.0), 2)
            formatted_workstreams[k] = {
                "key": k,
                "title": ws.get("title", k),
                "dependencies": ws.get("dependencies", []),
                "bounty_share_pct": bounty_pct,
                "allocated_usdc": allocated_usdc,
                "status": "READY" if not ws.get("dependencies") else "PENDING",
                "assigned_worker": None,
                "completed_at": None,
            }

        charter["workstreams"] = formatted_workstreams
        charter["execution_order"] = execution_order
        charter["updated_at"] = time.time()
        self._save_charters(charters)

        return {
            "status": "success",
            "problem_id": problem_id,
            "workstreams_count": len(formatted_workstreams),
            "execution_order": execution_order,
            "workstreams": formatted_workstreams,
        }

    def register_artifact(
        self,
        problem_id: str,
        workstream_key: str,
        title: str,
        artifact_content_or_uri: str,
        artifact_type: str = "CODE",
        license_type: str = "MIT",
        creator_agent: str = "Worker-Agent",
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Registers a content-digested artifact with SHA-256 cryptographic provenance."""
        _ensure_storage()
        charters = self._load_charters()
        if problem_id not in charters:
            return {"status": "error", "message": f"Problem charter '{problem_id}' not found"}

        charter = charters[problem_id]
        if workstream_key not in charter.get("workstreams", {}):
            return {"status": "error", "message": f"Workstream '{workstream_key}' not in problem '{problem_id}'"}

        # Calculate content digest
        digest = hashlib.sha256(artifact_content_or_uri.encode("utf-8")).hexdigest()
        artifact_id = f"art_{digest[:12]}"

        artifact_entry = {
            "artifact_id": artifact_id,
            "problem_id": problem_id,
            "workstream_key": workstream_key,
            "title": title,
            "artifact_digest": digest,
            "artifact_type": artifact_type.upper(),
            "license": license_type,
            "creator_agent": creator_agent,
            "evidence": evidence or {},
            "registered_at": time.time(),
        }

        # Save to artifacts ledger
        try:
            records = []
            if os.path.exists(self.artifacts_path):
                with open(self.artifacts_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
            records.append(artifact_entry)
            with open(self.artifacts_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to record artifact: {e}")

        # Mark workstream in review
        charter["workstreams"][workstream_key]["status"] = "IN_REVIEW"
        charter["workstreams"][workstream_key]["artifact_id"] = artifact_id
        charter["updated_at"] = time.time()
        self._save_charters(charters)

        return {"status": "success", "artifact": artifact_entry}

    def list_charters(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        charters = self._load_charters()
        results = list(charters.values())
        if status:
            results = [c for c in results if c.get("status") == status.upper()]
        return results

    def get_charter(self, problem_id: str) -> Optional[Dict[str, Any]]:
        charters = self._load_charters()
        return charters.get(problem_id)
