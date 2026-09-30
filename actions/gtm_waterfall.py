"""
actions/gtm_waterfall.py
OpenGTM Waterfall Lead Enrichment Engine for Prime AI.

Implements cascading, cost-optimized lead intelligence:
Stage 1: Local Cache Lookup (instant, $0)
Stage 2: Domain Meta Intel & Schema Analysis ($0)
Stage 3: Public Web / Search Scraping for Founders & Contacts ($0)
Stage 4: Extensible API Provider Adapters (Apollo/Hunter/Clearbit if keys configured)
"""

import os
import re
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("prime.gtm.waterfall")
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "gtm_cache.json"

class GTMLeadWaterfall:
    """Waterfall Lead Enrichment Engine inspired by OpenGTM."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or CACHE_FILE
        self.cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load GTM cache: {e}")
        return {}

    def _save_cache(self):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to write GTM cache: {e}")

    def clean_domain(self, domain_or_url: str) -> str:
        """Extract clean domain name without protocol or trailing paths."""
        domain = domain_or_url.strip().lower()
        if domain.startswith("http://") or domain.startswith("https://"):
            try:
                parsed = urllib.parse.urlparse(domain)
                domain = parsed.netloc or domain
            except Exception:
                pass
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.split("/")[0].split("?")[0].strip()
        return domain

    def _stage1_cache(self, domain: str) -> Optional[Dict[str, Any]]:
        """Stage 1: Check local cache for previously enriched lead."""
        if domain in self.cache:
            entry = self.cache[domain]
            logger.info(f"[Waterfall] Cache hit for {domain}")
            entry["waterfall_stage_resolved"] = "Stage 1 (Local Cache)"
            return entry
        return None

    def _stage2_meta_intel(self, domain: str) -> Dict[str, Any]:
        """Stage 2: Domain direct inspection (headers, title, meta tags, tech hints)."""
        intel = {
            "domain": domain,
            "company_name": domain.split(".")[0].capitalize(),
            "title": "",
            "description": "",
            "tech_stack": [],
            "social_links": {},
            "raw_emails": [],
            "http_status": None,
        }

        url = f"https://{domain}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                intel["http_status"] = response.status
                headers = dict(response.info())
                
                # Detect tech stack from response headers
                server_hdr = headers.get("server", "").lower()
                if "cloudflare" in server_hdr:
                    intel["tech_stack"].append("Cloudflare")
                if "vercel" in server_hdr or "x-vercel-id" in headers:
                    intel["tech_stack"].append("Vercel")
                if "netlify" in headers or "x-nf-request-id" in headers:
                    intel["tech_stack"].append("Netlify")
                if "next.js" in str(headers).lower():
                    intel["tech_stack"].append("Next.js")

                content_bytes = response.read(300000) # Read first 300KB
                html_text = content_bytes.decode("utf-8", errors="ignore")

                # Extract title
                title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
                if title_match:
                    clean_title = re.sub(r"\s+", " ", title_match.group(1)).strip()
                    intel["title"] = clean_title
                    if "|" in clean_title:
                        intel["company_name"] = clean_title.split("|")[0].strip()
                    elif "-" in clean_title:
                        intel["company_name"] = clean_title.split("-")[0].strip()

                # Extract meta description
                desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                if not desc_match:
                    desc_match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html_text, re.IGNORECASE)
                if desc_match:
                    intel["description"] = desc_match.group(1).strip()

                # Detect frameworks and marketing scripts in HTML
                low_html = html_text.lower()
                if "wp-content" in low_html:
                    intel["tech_stack"].append("WordPress")
                if "shopify" in low_html:
                    intel["tech_stack"].append("Shopify")
                if "webflow" in low_html:
                    intel["tech_stack"].append("Webflow")
                if "react" in low_html or "_next" in low_html:
                    intel["tech_stack"].append("React")
                if "tailwind" in low_html:
                    intel["tech_stack"].append("TailwindCSS")
                if "googletagmanager" in low_html or "google-analytics" in low_html:
                    intel["tech_stack"].append("Google Analytics")
                if "hubspot" in low_html or "hs-scripts" in low_html:
                    intel["tech_stack"].append("HubSpot")
                if "stripe.com" in low_html:
                    intel["tech_stack"].append("Stripe")
                if "intercom" in low_html:
                    intel["tech_stack"].append("Intercom")

                # Extract social profiles
                for platform in ["linkedin", "twitter", "x", "github", "facebook", "instagram", "youtube"]:
                    p_match = re.findall(rf'href=["\'](https?://(?:www\.)?{platform}\.com/[a-zA-Z0-9_\-\./]+)["\']', html_text, re.IGNORECASE)
                    if p_match:
                        intel["social_links"][platform] = p_match[0]

                # Extract potential emails
                emails = set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html_text))
                valid_emails = [e for e in emails if not e.endswith((".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"))]
                intel["raw_emails"] = valid_emails[:5]

        except Exception as e:
            logger.debug(f"[Waterfall] Meta inspection error for {domain}: {e}")

        intel["tech_stack"] = list(dict.fromkeys(intel["tech_stack"]))
        return intel

    def _stage3_web_search(self, company_name: str, domain: str) -> Dict[str, Any]:
        """Stage 3: Targeted search query to find leadership, founders, and headquarters."""
        query = f'"{company_name}" "{domain}" (founder OR CEO OR "headquarters" OR "about us")'
        search_res = {
            "founders": [],
            "leadership": [],
            "headquarters": "",
            "estimated_size": "Unknown",
            "search_summary": ""
        }
        try:
            from actions.web_search import search_duckduckgo
            results = search_duckduckgo(query)
            if results:
                snippets = []
                for r in results[:5]:
                    snippet = r.get("snippet", "") or r.get("title", "")
                    snippets.append(snippet)
                    
                    # Extract founder/CEO names heuristics
                    founder_matches = re.findall(r'(?:founded by|founder|co-founder|ceo)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)(?:\s+and\s+([A-Z][a-z]+ [A-Z][a-z]+))?', snippet, re.IGNORECASE)
                    for group in founder_matches:
                        for fm in group:
                            if fm and fm.lower() not in ["the company", "our team", "about us"] and fm not in search_res["founders"]:
                                search_res["founders"].append(fm)

                search_res["search_summary"] = " | ".join(snippets[:3])
        except Exception as e:
            logger.debug(f"[Waterfall] Stage 3 search error: {e}")
        return search_res

    def _stage4_api_adapters(self, domain: str, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4: Paid API waterfall (Hunter / Apollo / Clearbit if configured)."""
        hunter_key = os.getenv("HUNTER_API_KEY")
        apollo_key = os.getenv("APOLLO_API_KEY")

        api_intel = {}
        if hunter_key:
            try:
                # Query Hunter.io Domain Search
                req_url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={hunter_key}"
                req = urllib.request.Request(req_url, headers={"User-Agent": "PrimeGTM/1.0"})
                with urllib.request.urlopen(req, timeout=5) as res:
                    data = json.loads(res.read().decode())
                    if "data" in data and "emails" in data["data"]:
                        api_intel["hunter_emails"] = [e.get("value") for e in data["data"]["emails"][:5] if e.get("value")]
                        logger.info(f"[Waterfall] Hunter.io returned {len(api_intel['hunter_emails'])} emails")
            except Exception as e:
                logger.warning(f"[Waterfall] Hunter API query failed: {e}")

        return api_intel

    def enrich_lead(self, domain_or_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Execute the full OpenGTM cascading waterfall on a company or domain.
        Returns unified enriched lead record with confidence scoring.
        """
        domain = self.clean_domain(domain_or_name)
        if not domain:
            return {"error": "Invalid domain or company provided", "ok": False}

        # Stage 1: Local Cache
        if not force_refresh:
            cached = self._stage1_cache(domain)
            if cached:
                return {"ok": True, "source": "cache", "lead": cached}

        stages_run = []

        # Stage 2: Direct Meta & Domain Intel
        stages_run.append("Stage 2 (Meta Intel)")
        meta_data = self._stage2_meta_intel(domain)

        company_name = meta_data.get("company_name") or domain.split(".")[0].capitalize()

        # Stage 3: Web Search for Founders & Background
        stages_run.append("Stage 3 (Web Search)")
        search_data = self._stage3_web_search(company_name, domain)

        # Stage 4: API Adapters (if keys present)
        api_data = self._stage4_api_adapters(domain, meta_data)
        if api_data:
            stages_run.append("Stage 4 (API Adapters)")

        # Merge intel
        all_emails = list(dict.fromkeys(meta_data.get("raw_emails", []) + api_data.get("hunter_emails", [])))
        founders = list(dict.fromkeys(search_data.get("founders", [])))

        # Confidence Scoring
        confidence = 40
        if meta_data.get("description"):
            confidence += 20
        if meta_data.get("tech_stack"):
            confidence += 15
        if founders:
            confidence += 15
        if all_emails:
            confidence += 10
        confidence = min(confidence, 100)

        record = {
            "domain": domain,
            "company_name": company_name,
            "title": meta_data.get("title", ""),
            "description": meta_data.get("description", ""),
            "tech_stack": meta_data.get("tech_stack", []),
            "social_links": meta_data.get("social_links", {}),
            "emails": all_emails,
            "founders": founders,
            "search_summary": search_data.get("search_summary", ""),
            "confidence_score": confidence,
            "waterfall_stages": stages_run,
            "enriched_at": datetime.now().isoformat(),
        }

        # Cache result
        self.cache[domain] = record
        self._save_cache()

        logger.info(f"[Waterfall] Enriched {domain} with score {confidence}% via {', '.join(stages_run)}")
        return {
            "ok": True,
            "source": "live_waterfall",
            "lead": record
        }

# Global singleton
waterfall_engine = GTMLeadWaterfall()

def enrich_company_lead(domain_or_name: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Helper entry point for Prime tool dispatch."""
    return waterfall_engine.enrich_lead(domain_or_name, force_refresh=force_refresh)
