"""
Unit and integration tests for Collagent / AgentWork Decentralized AI Agent Labor Protocol.
"""

import os
import shutil
import tempfile
import unittest

from actions.agentwork_charter import ProblemCharterManager
from actions.agentwork_worker import AgentWorkerEngine
from actions.agentwork_verifier import SandboxVerifierEngine
from actions.agentwork_connector import CollagentConnector
from tool_definitions import TOOL_SPECS, execute_tool


class TestAgentWorkCharter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.charters_file = os.path.join(self.test_dir, "test_charters.json")
        self.artifacts_file = os.path.join(self.test_dir, "test_artifacts.json")
        self.mgr = ProblemCharterManager(self.charters_file, self.artifacts_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_charter_and_dag_decomposition(self):
        # 1. Create problem charter
        res = self.mgr.create_problem_charter(
            title="Decentralized Storage Adapter",
            charter="Build IPFS and Arweave storage adapter microservice",
            acceptance_criteria=["99% test coverage", "Latency < 200ms"],
            bounty_usdc=500.0,
            scope="GLOBAL",
            risk_level="LOW",
        )
        self.assertEqual(res["status"], "success")
        prob_id = res["problem"]["problem_id"]
        self.assertEqual(res["problem"]["bounty_usdc"], 500.0)

        # 2. Decompose into DAG
        workstreams = [
            {"key": "api_spec", "title": "Define OpenAPI contract", "bounty_share_pct": 20.0, "dependencies": []},
            {"key": "ipfs_node", "title": "Implement IPFS client", "bounty_share_pct": 40.0, "dependencies": ["api_spec"]},
            {"key": "e2e_tests", "title": "Write automated E2E tests", "bounty_share_pct": 40.0, "dependencies": ["ipfs_node"]},
        ]
        dag_res = self.mgr.decompose_into_workstream_dag(prob_id, workstreams)
        self.assertEqual(dag_res["status"], "success")
        self.assertEqual(dag_res["workstreams_count"], 3)
        self.assertEqual(dag_res["execution_order"], ["api_spec", "ipfs_node", "e2e_tests"])
        self.assertEqual(dag_res["workstreams"]["ipfs_node"]["allocated_usdc"], 200.0)

        # 3. Test cycle detection
        cyclic_ws = [
            {"key": "a", "title": "A", "bounty_share_pct": 50.0, "dependencies": ["b"]},
            {"key": "b", "title": "B", "bounty_share_pct": 50.0, "dependencies": ["a"]},
        ]
        cycle_res = self.mgr.decompose_into_workstream_dag(prob_id, cyclic_ws)
        self.assertEqual(cycle_res["status"], "error")
        self.assertIn("Cyclic", cycle_res["message"])

        # 4. Register artifact with SHA-256 provenance
        art_res = self.mgr.register_artifact(
            prob_id,
            "api_spec",
            "OpenAPI v3 Spec",
            "openapi: 3.0.0\ninfo:\n  title: Storage Adapter",
            artifact_type="CODE",
        )
        self.assertEqual(art_res["status"], "success")
        self.assertTrue(art_res["artifact"]["artifact_id"].startswith("art_"))
        self.assertEqual(len(art_res["artifact"]["artifact_digest"]), 64)


class TestAgentWorkWorker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.bids_file = os.path.join(self.test_dir, "test_bids.json")
        self.deliveries_file = os.path.join(self.test_dir, "test_deliveries.json")
        self.worker = AgentWorkerEngine(self.bids_file, self.deliveries_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_feasibility_scoring_and_bidding(self):
        # 1. Feasibility scoring
        eval_res = self.worker.evaluate_task_feasibility(["python", "backend", "testing"], 200.0)
        self.assertTrue(eval_res["is_feasible"])
        self.assertGreaterEqual(eval_res["match_score"], 80.0)
        self.assertEqual(eval_res["recommended_bid_usdc"], 180.0)

        # 2. Place labor bid
        bid_res = self.worker.place_labor_bid(
            task_id="task_123",
            bid_amount_usdc=180.0,
            stake_amount_usdc=18.0,
            estimated_hours=6.0,
            proposal_pitch="Prime Python Specialist Agent executing clean implementation.",
        )
        self.assertEqual(bid_res["status"], "success")
        bid_id = bid_res["bid"]["bid_id"]

        # 3. Package delivery
        del_res = self.worker.package_delivery(
            task_id="task_123",
            bid_id=bid_id,
            git_commit_sha="a1b2c3d4e5f67890",
            delivery_summary="Delivered adapter code with 100% test pass rate.",
            artifact_uris=["https://git.local/commit/a1b2c3d4"],
        )
        self.assertEqual(del_res["status"], "success")
        del_id = del_res["delivery"]["delivery_id"]

        fetched = self.worker.get_delivery(del_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["git_commit_sha"], "a1b2c3d4e5f67890")


class TestAgentWorkVerifierAndQuorum(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.verifications_file = os.path.join(self.test_dir, "test_ver.json")
        self.quorum_file = os.path.join(self.test_dir, "test_quorum.json")
        self.verifier = SandboxVerifierEngine(self.verifications_file, self.quorum_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sandbox_verification_and_quorum_consensus(self):
        # 1. Sandbox verification passes
        v_res = self.verifier.run_sandbox_verification(
            task_id="task_abc",
            delivery_id="del_xyz",
            test_commands=["mock:pass", "echo all clear"],
        )
        self.assertEqual(v_res["status"], "success")
        job_id = v_res["verification"]["job_id"]
        self.assertEqual(v_res["verification"]["status"], "PASSED")

        # 2. Record vote 1 (single vote: pending more votes)
        vote1 = self.verifier.record_quorum_vote(
            task_id="task_abc",
            job_id=job_id,
            verifier_agent_id="Verifier-Node-01",
            vote="APPROVE",
        )
        self.assertEqual(vote1["status"], "success")
        self.assertFalse(vote1["consensus_reached"])
        self.assertEqual(vote1["consensus_status"], "PENDING_MORE_VOTES")

        # 3. Record vote 2 (reaching >= 2 votes and >= 66% approvals -> APPROVED)
        vote2 = self.verifier.record_quorum_vote(
            task_id="task_abc",
            job_id=job_id,
            verifier_agent_id="Verifier-Node-02",
            vote="APPROVE",
        )
        self.assertTrue(vote2["consensus_reached"])
        self.assertEqual(vote2["consensus_status"], "APPROVED")


class TestAgentWorkEscrowConnector(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.escrow_file = os.path.join(self.test_dir, "test_escrow.json")
        self.conn = CollagentConnector(escrow_path=self.escrow_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_escrow_lifecycle(self):
        # 1. Deposit escrow
        dep_res = self.conn.deposit_escrow("task_999", 250.0, depositor_address="0xEmployerWallet")
        self.assertEqual(dep_res["status"], "success")
        self.assertEqual(dep_res["escrow"]["status"], "LOCKED")

        # 2. Attempt settle without approval -> should fail
        fail_settle = self.conn.settle_escrow("task_999", "0xWorkerWallet", verifier_consensus="PENDING")
        self.assertEqual(fail_settle["status"], "error")
        self.assertIn("denied", fail_settle["message"].lower())

        # 3. Settle with verifier consensus APPROVED
        pass_settle = self.conn.settle_escrow("task_999", "0xWorkerWallet", verifier_consensus="APPROVED")
        self.assertEqual(pass_settle["status"], "success")
        self.assertEqual(pass_settle["escrow"]["status"], "SETTLED")

        # 4. Check summary
        summary = self.conn.get_escrow_summary()
        self.assertEqual(summary["total_escrows"], 1)
        self.assertEqual(summary["total_settled_usdc"], 250.0)


class TestToolDefinitionsAgentWorkIntegration(unittest.TestCase):
    def test_specs_registered(self):
        spec_names = {s["name"] for s in TOOL_SPECS}
        expected_tools = {
            "createProblemCharter",
            "decomposeProblemDAG",
            "registerWorkArtifact",
            "scanLaborMarketplace",
            "placeLaborBid",
            "verifyLaborDelivery",
            "settleTaskEscrow",
            "getCollagentStatus",
        }
        for tool_name in expected_tools:
            self.assertIn(tool_name, spec_names)

    def test_execute_create_charter_and_dag(self):
        res = execute_tool("createProblemCharter", {
            "title": "Quantum Resistance Engine",
            "charter": "Implement post-quantum cryptographic primitives",
            "acceptance_criteria": ["Kyber-512 support"],
            "bounty_usdc": 300.0,
        })
        self.assertEqual(res.get("status"), "success")
        prob_id = res.get("problem", {}).get("problem_id")
        self.assertIsNotNone(prob_id)

        # Decompose DAG via tool
        dag_res = execute_tool("decomposeProblemDAG", {
            "problem_id": prob_id,
            "workstreams": [
                {"key": "research", "title": "Algorithm Research", "bounty_share_pct": 50.0, "dependencies": []},
                {"key": "impl", "title": "Implementation", "bounty_share_pct": 50.0, "dependencies": ["research"]},
            ],
        })
        self.assertEqual(dag_res.get("status"), "success")
        self.assertEqual(dag_res.get("workstreams_count"), 2)

    def test_execute_scan_and_bid(self):
        scan_res = execute_tool("scanLaborMarketplace", {
            "required_skills": ["python", "smart_contracts"],
            "max_budget_usdc": 150.0,
        })
        self.assertTrue(scan_res.get("is_feasible"))

        bid_res = execute_tool("placeLaborBid", {
            "task_id": "test_task_tool",
            "bid_amount_usdc": 120.0,
            "stake_amount_usdc": 12.0,
            "proposal_pitch": "Prime Agent is uniquely suited for this task.",
        })
        self.assertEqual(bid_res.get("status"), "success")

    def test_execute_verify_and_status(self):
        ver_res = execute_tool("verifyLaborDelivery", {
            "task_id": "test_task_tool",
            "delivery_id": "del_tool_1",
            "test_commands": ["mock:pass"],
            "record_vote": "APPROVE",
        })
        self.assertEqual(ver_res.get("status"), "success")

        status_res = execute_tool("getCollagentStatus", {})
        self.assertEqual(status_res.get("status"), "success")
        self.assertIn("health", status_res)


if __name__ == "__main__":
    unittest.main()
