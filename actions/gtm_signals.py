"""
actions/gtm_signals.py
OpenGTM Buying Signals & Account Intent Engine for Prime AI.

Scans accounts for 4 intent dimensions:
1. Hiring & Expansion Signals (Careers, open positions, team growth)
2. Funding & Milestone Signals (Seed/Series A/B, investment, press releases)
3. Tech Stack & Modernization Signals (CMS, CRM, analytics, cloud platforms)
4. Outbound Conversation Hooks & Icebreakers based on detected triggers
"""

import re
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from actions.gtm_waterfall import waterfall_engine

logger = logging.getLogger("prime.gtm.signals")

class GTMBuyingSignalsScanner:
    """Detects buying intent and generates actionable conversation hooks."""

    def __init__(self):
        pass

    def _check_careers_page(self, domain: str) -> Dict[str, Any]:
        """Check common careers and jobs endpoints for hiring activity."""
        paths = ["/careers", "/jobs", "/about/careers", "/join-us", "/open-roles"]
        hiring_intel = {
            "has_careers_page": False,
            "careers_url": None,
            "detected_roles": [],
            "is_actively_hiring": False
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        for p in paths:
            url = f"https://{domain}{p}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=4) as response:
                    if response.status == 200:
                        hiring_intel["has_careers_page"] = True
                        hiring_intel["careers_url"] = url
                        html = response.read(150000).decode("utf-8", errors="ignore")
                        
                        # Look for common role keywords
                        roles = []
                        for role_kw in ["Software Engineer", "Frontend", "Backend", "Full Stack", "Product Manager", 
                                        "Account Executive", "Sales Manager", "Marketing", "DevOps", "AI Engineer", "Data Scientist"]:
                            if re.search(rf"\b{role_kw}\b", html, re.IGNORECASE):
                                roles.append(role_kw)

                        if roles or any(kw in html.lower() for kw in ["open positions", "we are hiring", "current openings", "apply now"]):
                            hiring_intel["is_actively_hiring"] = True
                            hiring_intel["detected_roles"] = list(dict.fromkeys(roles))
                        break
            except Exception:
                continue

        return hiring_intel

    def _search_funding_news(self, company_name: str, domain: str) -> Dict[str, Any]:
        """Search news and press for recent funding, acquisitions, or product milestones."""
        signals = {
            "funding_mentions": [],
            "milestones": [],
            "has_recent_growth": False
        }
        try:
            from actions.web_search import search_duckduckgo
            query = f'"{company_name}" (funding OR "raised" OR "Series" OR "acquired" OR "launched" OR "expansion")'
            results = search_duckduckgo(query)
            if results:
                for r in results[:4]:
                    snippet = r.get("snippet", "")
                    title = r.get("title", "")
                    text = f"{title} {snippet}"
                    
                    # Detect funding keywords
                    funding_match = re.search(r'(\$\d+(?:\.\d+)?\s*(?:million|M|billion|B)?\s*(?:seed|series\s*[a-d]|funding|investment))', text, re.IGNORECASE)
                    if funding_match:
                        signals["funding_mentions"].append(funding_match.group(1))
                        signals["has_recent_growth"] = True

                    # Detect launch / expansion keywords
                    if any(w in text.lower() for w in ["launches", "expands to", "partners with", "unveils", "records growth"]):
                        clean_snip = snippet[:140].strip()
                        if clean_snip:
                            signals["milestones"].append(clean_snip)
                            signals["has_recent_growth"] = True

        except Exception as e:
            logger.debug(f"[Signals] Funding news search error: {e}")

        signals["funding_mentions"] = list(dict.fromkeys(signals["funding_mentions"]))
        signals["milestones"] = list(dict.fromkeys(signals["milestones"]))[:3]
        return signals

    def compute_intent_score(self, hiring_data: Dict[str, Any], funding_data: Dict[str, Any], tech_stack: List[str]) -> Dict[str, Any]:
        """Calculate weighted account intent score (0-100) and urgency classification."""
        score = 20 # Base baseline score

        if hiring_data.get("is_actively_hiring"):
            score += 35
        elif hiring_data.get("has_careers_page"):
            score += 15

        if funding_data.get("funding_mentions"):
            score += 30
        elif funding_data.get("has_recent_growth"):
            score += 15

        if len(tech_stack) >= 4:
            score += 15
        elif len(tech_stack) >= 2:
            score += 10

        score = min(score, 100)

        if score >= 75:
            tier = "HIGH"
            action = "Immediate outreach recommended. Strong intent triggers present."
        elif score >= 50:
            tier = "MEDIUM"
            action = "Targeted nurture outreach with value drop."
        else:
            tier = "LOW"
            action = "Low urgency account. Monitor for new trigger events."

        return {
            "intent_score": score,
            "urgency_tier": tier,
            "recommended_action": action
        }

    def generate_conversation_hooks(self, company_name: str, hiring_data: Dict[str, Any], 
                                     funding_data: Dict[str, Any], tech_stack: List[str]) -> List[str]:
        """Synthesize concrete, non-generic icebreakers for outreach messages."""
        hooks = []

        # Hook 1: Hiring trigger
        if hiring_data.get("detected_roles"):
            roles_str = ", ".join(hiring_data["detected_roles"][:2])
            hooks.append(f"Noticed {company_name} is actively expanding your team and hiring for {roles_str}.")
        elif hiring_data.get("is_actively_hiring"):
            hooks.append(f"Saw that {company_name} is scaling headcount across key departments on your careers portal.")

        # Hook 2: Funding or growth milestone
        if funding_data.get("funding_mentions"):
            hooks.append(f"Big congratulations on the recent {funding_data['funding_mentions'][0]} announcement!")
        elif funding_data.get("milestones"):
            hooks.append(f"Saw the recent announcement: '{funding_data['milestones'][0]}'.")

        # Hook 3: Tech stack / modernization
        if "Shopify" in tech_stack or "WordPress" in tech_stack:
            hooks.append(f"Noticed your digital storefront is built on {tech_stack[0]}—curious how you're optimizing checkout conversion.")
        elif "React" in tech_stack or "Next.js" in tech_stack:
            hooks.append(f"Love the clean, performant experience on {company_name}'s web platform.")

        if not hooks:
            hooks.append(f"Following {company_name}'s momentum in the market and wanted to reach out directly.")

        return hooks

    def scan_signals(self, domain_or_name: str) -> Dict[str, Any]:
        """
        Analyze all buying intent signals for the specified domain.
        Combines waterfall tech stack, careers page scan, and funding news.
        """
        domain = waterfall_engine.clean_domain(domain_or_name)
        if not domain:
            return {"ok": False, "error": "Invalid domain"}

        # Get base lead enrichment (from cache if already resolved)
        lead_result = waterfall_engine.enrich_lead(domain)
        lead_data = lead_result.get("lead", {})
        company_name = lead_data.get("company_name", domain.split(".")[0].capitalize())
        tech_stack = lead_data.get("tech_stack", [])

        # Check careers & hiring
        hiring_intel = self._check_careers_page(domain)

        # Search funding and milestones
        funding_intel = self._search_funding_news(company_name, domain)

        # Compute intent score
        intent = self.compute_intent_score(hiring_intel, funding_intel, tech_stack)

        # Generate conversation hooks
        hooks = self.generate_conversation_hooks(company_name, hiring_intel, funding_intel, tech_stack)

        return {
            "ok": True,
            "domain": domain,
            "company_name": company_name,
            "intent_score": intent["intent_score"],
            "urgency_tier": intent["urgency_tier"],
            "recommended_action": intent["recommended_action"],
            "hiring_signals": hiring_intel,
            "growth_signals": funding_intel,
            "tech_stack": tech_stack,
            "conversation_hooks": hooks,
        }

# Global singleton
signals_scanner = GTMBuyingSignalsScanner()

def scan_account_signals(domain_or_name: str) -> Dict[str, Any]:
    """Helper entry point for Prime tool dispatch."""
    return signals_scanner.scan_signals(domain_or_name)
