"""
tests/test_gtm_suite.py
Comprehensive unit test suite for OpenGTM B2B Lead Intelligence & Outbound Suite:
1. Waterfall Lead Enrichment Engine (Local cache -> Meta Intel -> Web Scrape -> API)
2. Buying Signals & Intent Scanner (Careers/hiring, funding milestones, intent scoring)
3. Hyper-Personalized Outbound Drafter (WhatsApp, Cold Email, LinkedIn + WhatsApp Manager staging)
4. OpenGTM Self-Hosted Server API Connector
5. Tool Specifications & Dispatcher Integration
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.gtm_waterfall import GTMLeadWaterfall, enrich_company_lead
from actions.gtm_signals import GTMBuyingSignalsScanner, scan_account_signals
from actions.gtm_outreach import GTMOutreachDrafter, draft_gtm_outreach, queue_whatsapp_gtm_pitch
from actions.opengtm_connector import OpenGTMConnector, connect_opengtm
import tool_definitions

class TestGTMWaterfall(unittest.TestCase):
    """Test Suite for Cascading Waterfall Lead Enrichment."""

    def setUp(self):
        self.test_cache_path = Path(__file__).resolve().parent / "tmp_gtm_cache.json"
        self.waterfall = GTMLeadWaterfall(cache_path=self.test_cache_path)

    def tearDown(self):
        if self.test_cache_path.exists():
            try:
                self.test_cache_path.unlink()
            except Exception:
                pass

    def test_clean_domain(self):
        self.assertEqual(self.waterfall.clean_domain("https://www.stripe.com/docs"), "stripe.com")
        self.assertEqual(self.waterfall.clean_domain("http://linear.app/features?ref=product"), "linear.app")
        self.assertEqual(self.waterfall.clean_domain("sub.domain.co.in/"), "sub.domain.co.in")
        self.assertEqual(self.waterfall.clean_domain("  apple.com  "), "apple.com")

    def test_stage1_cache_hit_and_miss(self):
        # Miss
        self.assertIsNone(self.waterfall._stage1_cache("unknown-lead.com"))
        
        # Insert and test hit
        self.waterfall.cache["testcorp.com"] = {
            "domain": "testcorp.com",
            "company_name": "TestCorp",
            "confidence_score": 85
        }
        hit = self.waterfall._stage1_cache("testcorp.com")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["company_name"], "TestCorp")
        self.assertIn("Local Cache", hit["waterfall_stage_resolved"])

    @patch("urllib.request.urlopen")
    def test_stage2_meta_intel_extraction(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.info.return_value = {"server": "cloudflare", "x-vercel-id": "iad1::123"}
        html_payload = """
        <html>
            <head>
                <title>Acme Corp | Modern Cloud Orchestration</title>
                <meta name="description" content="Acme builds AI-driven workflows for forward-thinking enterprises." />
            </head>
            <body>
                <a href="https://linkedin.com/company/acme-corp">LinkedIn</a>
                <a href="https://github.com/acme">GitHub</a>
                <p>Contact us at hello@acmecorp.io or sales@acmecorp.io</p>
                <script src="https://js.stripe.com/v3/"></script>
                <script src="https://js.hs-scripts.com/12345.js"></script>
            </body>
        </html>
        """
        mock_response.read.return_value = html_payload.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        intel = self.waterfall._stage2_meta_intel("acmecorp.io")
        self.assertEqual(intel["company_name"], "Acme Corp")
        self.assertIn("Acme builds AI-driven workflows", intel["description"])
        self.assertIn("Cloudflare", intel["tech_stack"])
        self.assertIn("Vercel", intel["tech_stack"])
        self.assertIn("Stripe", intel["tech_stack"])
        self.assertIn("HubSpot", intel["tech_stack"])
        self.assertIn("hello@acmecorp.io", intel["raw_emails"])
        self.assertIn("linkedin", intel["social_links"])

    @patch("actions.web_search.search_duckduckgo")
    def test_stage3_web_search_founders(self, mock_ddg):
        mock_ddg.return_value = [
            {"title": "Acme Corp History", "snippet": "Acme Corp was founded by Alice Walker and Bob Smith in 2021."},
            {"title": "Leadership at Acme", "snippet": "CEO Alice Walker announced their newest release today."}
        ]

        res = self.waterfall._stage3_web_search("Acme Corp", "acmecorp.io")
        self.assertIn("Alice Walker", res["founders"])
        self.assertIn("Bob Smith", res["founders"])

    @patch.object(GTMLeadWaterfall, "_stage2_meta_intel")
    @patch.object(GTMLeadWaterfall, "_stage3_web_search")
    def test_full_waterfall_enrichment_flow(self, mock_s3, mock_s2):
        mock_s2.return_value = {
            "domain": "innovate.ai",
            "company_name": "Innovate AI",
            "title": "Innovate AI Platforms",
            "description": "Enterprise agent orchestration platform.",
            "tech_stack": ["React", "TailwindCSS", "Next.js"],
            "social_links": {"twitter": "https://x.com/innovate"},
            "raw_emails": ["team@innovate.ai"],
            "http_status": 200
        }
        mock_s3.return_value = {
            "founders": ["David Miller"],
            "search_summary": "Founded by David Miller in San Francisco."
        }

        result = self.waterfall.enrich_lead("innovate.ai")
        self.assertTrue(result["ok"])
        lead = result["lead"]
        self.assertEqual(lead["company_name"], "Innovate AI")
        self.assertEqual(lead["founders"], ["David Miller"])
        self.assertGreaterEqual(lead["confidence_score"], 80)
        self.assertIn("innovate.ai", self.waterfall.cache)


class TestGTMBuyingSignals(unittest.TestCase):
    """Test Suite for Account Intent & Buying Signals Detection."""

    def setUp(self):
        self.scanner = GTMBuyingSignalsScanner()

    @patch("urllib.request.urlopen")
    def test_check_careers_page_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"""
        <html>
            <body>
                <h1>We are hiring!</h1>
                <p>Open positions: Senior Software Engineer, Full Stack, Product Manager</p>
                <button>Apply Now</button>
            </body>
        </html>
        """
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.scanner._check_careers_page("growthtech.co")
        self.assertTrue(res["has_careers_page"])
        self.assertTrue(res["is_actively_hiring"])
        self.assertIn("Software Engineer", res["detected_roles"])
        self.assertIn("Full Stack", res["detected_roles"])

    @patch("actions.web_search.search_duckduckgo")
    def test_search_funding_news(self, mock_ddg):
        mock_ddg.return_value = [
            {"title": "ScaleUp Raises $15 million Series A", "snippet": "ScaleUp has secured $15 million Series A funding for AI tooling."},
            {"title": "ScaleUp expands to Europe", "snippet": "ScaleUp expands to new markets with record customer demand."}
        ]

        res = self.scanner._search_funding_news("ScaleUp", "scaleup.io")
        self.assertTrue(res["has_recent_growth"])
        self.assertTrue(len(res["funding_mentions"]) > 0)
        self.assertTrue(any("$15 million" in m for m in res["funding_mentions"]))

    def test_compute_intent_score_and_tier(self):
        # High intent
        hiring_high = {"is_actively_hiring": True, "has_careers_page": True}
        funding_high = {"funding_mentions": ["$10M Series A"], "has_recent_growth": True}
        tech_high = ["React", "HubSpot", "Cloudflare", "Stripe"]

        res_high = self.scanner.compute_intent_score(hiring_high, funding_high, tech_high)
        self.assertGreaterEqual(res_high["intent_score"], 80)
        self.assertEqual(res_high["urgency_tier"], "HIGH")

        # Low intent
        hiring_low = {"is_actively_hiring": False, "has_careers_page": False}
        funding_low = {"funding_mentions": [], "has_recent_growth": False}
        tech_low = []

        res_low = self.scanner.compute_intent_score(hiring_low, funding_low, tech_low)
        self.assertLess(res_low["intent_score"], 50)
        self.assertEqual(res_low["urgency_tier"], "LOW")

    def test_generate_conversation_hooks(self):
        hooks = self.scanner.generate_conversation_hooks(
            company_name="ApexAI",
            hiring_data={"detected_roles": ["DevOps", "AI Engineer"], "is_actively_hiring": True},
            funding_data={"funding_mentions": ["$20 million Series B"], "milestones": []},
            tech_stack=["Shopify"]
        )
        self.assertTrue(len(hooks) >= 2)
        self.assertTrue(any("DevOps" in h for h in hooks))
        self.assertTrue(any("$20 million" in h for h in hooks))


class TestGTMOutreach(unittest.TestCase):
    """Test Suite for Hyper-Personalized Outbound Drafter & WhatsApp Queuer."""

    def setUp(self):
        self.test_log_path = Path(__file__).resolve().parent / "tmp_gtm_outreach_log.json"
        self.drafter = GTMOutreachDrafter(log_path=self.test_log_path)

    def tearDown(self):
        if self.test_log_path.exists():
            try:
                self.test_log_path.unlink()
            except Exception:
                pass

    @patch("actions.gtm_waterfall.waterfall_engine.enrich_lead")
    @patch("actions.gtm_signals.signals_scanner.scan_signals")
    def test_draft_outreach_whatsapp_and_email(self, mock_signals, mock_lead):
        mock_lead.return_value = {
            "ok": True,
            "lead": {
                "company_name": "FintechHub",
                "founders": ["Sarah Connor"],
                "tech_stack": ["React", "PostgreSQL"],
                "emails": ["sarah@fintechhub.com"]
            }
        }
        mock_signals.return_value = {
            "conversation_hooks": ["Saw FintechHub recently secured $10 million Series A."],
            "intent_score": 85,
            "urgency_tier": "HIGH"
        }

        # 1. WhatsApp draft
        wa_res = self.drafter.draft_outreach("fintechhub.com", channel="whatsapp", target_contact_name="Sarah Connor")
        self.assertTrue(wa_res["ok"])
        draft = wa_res["draft"]
        self.assertEqual(draft["channel"], "whatsapp")
        self.assertIn("Hey Sarah!", draft["message"])
        self.assertIn("Series A", draft["message"])

        # 2. Cold email draft
        email_res = self.drafter.draft_outreach("fintechhub.com", channel="email", target_contact_name="Sarah Connor")
        self.assertTrue(email_res["ok"])
        edraft = email_res["draft"]
        self.assertEqual(edraft["channel"], "email")
        self.assertIn("Quick question regarding FintechHub", edraft["subject"])
        self.assertIn("Hi Sarah,", edraft["body"])

    @patch("actions.gtm_outreach.GTMOutreachDrafter.draft_outreach")
    @patch("whatsapp_manager.send_whatsapp")
    def test_queue_whatsapp_pitch_staging_and_send(self, mock_send_wa, mock_draft):
        mock_draft.return_value = {
            "ok": True,
            "draft": {
                "message": "Hey John, saw you're expanding your team!",
                "hook_used": "Team expansion",
                "intent_score": 80,
                "urgency_tier": "HIGH",
                "company": "Nexus"
            }
        }

        # Staging mode (send_now=False)
        staged = self.drafter.queue_whatsapp_pitch("John Doe", "nexus.io", send_now=False)
        self.assertTrue(staged["ok"])
        self.assertEqual(staged["status"], "staged_draft")
        mock_send_wa.assert_not_called()

        # Immediate send mode (send_now=True)
        mock_send_wa.return_value = {"ok": True, "message": "Dispatched via WhatsApp Desktop"}
        sent = self.drafter.queue_whatsapp_pitch("+1234567890", "nexus.io", send_now=True)
        self.assertTrue(sent["ok"])
        self.assertEqual(sent["status"], "sent")
        mock_send_wa.assert_called_once()


class TestOpenGTMConnector(unittest.TestCase):
    """Test Suite for Self-Hosted OpenGTM API Connector."""

    def setUp(self):
        self.connector = OpenGTMConnector(base_url="http://127.0.0.1:3000", api_key="test_opengtm_key")

    @patch("urllib.request.urlopen")
    def test_health_check_online(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "healthy", "service": "opengtm"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.connector.check_health()
        self.assertTrue(res["ok"])
        self.assertTrue(res["online"])
        self.assertEqual(res["http_status"], 200)

    @patch("urllib.request.urlopen")
    def test_health_check_offline(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        res = self.connector.check_health()
        self.assertFalse(res["ok"])
        self.assertFalse(res["online"])
        self.assertIn("not reachable", res["error"])

    @patch("urllib.request.urlopen")
    def test_list_workbooks(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps([{"id": "wb_01", "name": "SaaS Founders Q4"}]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.connector.list_workbooks()
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["workbooks"]), 1)
        self.assertEqual(res["workbooks"][0]["id"], "wb_01")


class TestToolDefinitionsIntegration(unittest.TestCase):
    """Test Suite verifying tool catalog definitions and execution dispatch."""

    def test_specs_registered(self):
        names = [s["name"] for s in tool_definitions.TOOL_SPECS]
        self.assertIn("enrichLead", names)
        self.assertIn("scanBuyingSignals", names)
        self.assertIn("draftGTMOutreach", names)
        self.assertIn("queueGTMWhatsAppOutreach", names)
        self.assertIn("connectOpenGTM", names)

    @patch("actions.gtm_waterfall.enrich_company_lead")
    def test_execute_enrich_lead(self, mock_enrich):
        mock_enrich.return_value = {"ok": True, "lead": {"company_name": "TestCorp"}}
        res = tool_definitions.execute_tool("enrichLead", {"domain": "testcorp.com"})
        self.assertTrue(res["ok"])
        mock_enrich.assert_called_with("testcorp.com", force_refresh=False)

    @patch("actions.gtm_signals.scan_account_signals")
    def test_execute_scan_signals(self, mock_scan):
        mock_scan.return_value = {"ok": True, "intent_score": 90}
        res = tool_definitions.execute_tool("scanBuyingSignals", {"domain": "testcorp.com"})
        self.assertTrue(res["ok"])
        mock_scan.assert_called_with("testcorp.com")

    @patch("actions.gtm_outreach.draft_gtm_outreach")
    def test_execute_draft_outreach(self, mock_draft):
        mock_draft.return_value = {"ok": True, "draft": {"message": "Hello"}}
        res = tool_definitions.execute_tool("draftGTMOutreach", {"domain": "testcorp.com", "channel": "whatsapp"})
        self.assertTrue(res["ok"])
        mock_draft.assert_called()

    @patch("actions.gtm_outreach.queue_whatsapp_gtm_pitch")
    def test_execute_queue_whatsapp(self, mock_queue):
        mock_queue.return_value = {"ok": True, "status": "staged_draft"}
        res = tool_definitions.execute_tool("queueGTMWhatsAppOutreach", {"recipient": "Alice", "domain": "testcorp.com"})
        self.assertTrue(res["ok"])
        mock_queue.assert_called_with("Alice", "testcorp.com", send_now=False, custom_note="")

    @patch("actions.opengtm_connector.connect_opengtm")
    def test_execute_connect_opengtm(self, mock_conn):
        mock_conn.return_value = {"ok": True, "online": True}
        res = tool_definitions.execute_tool("connectOpenGTM", {"action": "health"})
        self.assertTrue(res["ok"])
        mock_conn.assert_called_with(action="health", domain="")


if __name__ == "__main__":
    unittest.main()
