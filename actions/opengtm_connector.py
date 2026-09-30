"""
actions/opengtm_connector.py
OpenGTM Self-Hosted Server API & MCP Connector for Prime AI.

Provides direct communication with a running OpenGTM instance:
1. Health & Server Status Check
2. Workbook & Workspace Synchronization
3. Remote Waterfall Execution Queue
4. Durable Job Status Polling
"""

import os
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional

logger = logging.getLogger("prime.opengtm.connector")

class OpenGTMConnector:
    """Client for local or remote OpenGTM server instances (FastAPI + PostgreSQL + Celery stack)."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OPENGTM_BASE_URL", "http://127.0.0.1:3000")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENGTM_API_KEY", "")

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PrimeAI-OpenGTM-Connector/1.0"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def check_health(self) -> Dict[str, Any]:
        """Check if OpenGTM server is reachable and operational."""
        endpoints = [f"{self.base_url}/api/health", f"{self.base_url}/health", f"{self.base_url}/"]
        
        for ep in endpoints:
            try:
                req = urllib.request.Request(ep, headers=self._headers(), method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    status = resp.status
                    if status in (200, 204):
                        body = ""
                        try:
                            body = resp.read().decode("utf-8")
                        except Exception:
                            pass
                        logger.info(f"[OpenGTM] Connected successfully to {self.base_url} (HTTP {status})")
                        return {
                            "ok": True,
                            "online": True,
                            "base_url": self.base_url,
                            "http_status": status,
                            "response": body[:200]
                        }
            except Exception as e:
                logger.debug(f"[OpenGTM] Endpoint {ep} failed: {e}")

        return {
            "ok": False,
            "online": False,
            "base_url": self.base_url,
            "error": "OpenGTM server is not reachable at the configured address. Start via `docker compose up`."
        }

    def list_workbooks(self) -> Dict[str, Any]:
        """Fetch list of workbooks and lead lists from the active OpenGTM workspace."""
        url = f"{self.base_url}/api/v1/workbooks"
        try:
            req = urllib.request.Request(url, headers=self._headers(), method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "workbooks": data}
        except Exception as e:
            return {
                "ok": False, 
                "error": f"Failed to list workbooks from OpenGTM: {e}",
                "hint": "Check if OPENGTM_API_KEY is configured in your environment."
            }

    def enqueue_remote_waterfall(self, domain: str, company_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enqueue a lead row into OpenGTM's durable backend execution queue."""
        url = f"{self.base_url}/api/v1/jobs/waterfall"
        payload = {
            "domain": domain,
            "company_name": company_name,
            "metadata": metadata or {}
        }
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=self._headers(), method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return {
                    "ok": True,
                    "job_id": result.get("job_id"),
                    "status": "enqueued",
                    "details": result
                }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to enqueue lead in OpenGTM queue: {e}",
                "fallback_available": "You can use Prime's local waterfall engine (actions/gtm_waterfall.py) directly without Docker."
            }

# Global singleton
opengtm_connector = OpenGTMConnector()

def connect_opengtm(action: str = "health", domain: str = "") -> Dict[str, Any]:
    """Helper entry point for Prime tool dispatch."""
    action_clean = action.lower().strip()
    if action_clean == "health" or not action_clean:
        return opengtm_connector.check_health()
    elif action_clean == "workbooks":
        return opengtm_connector.list_workbooks()
    elif action_clean == "enqueue":
        return opengtm_connector.enqueue_remote_waterfall(domain)
    else:
        return {"ok": False, "error": f"Unknown action: {action}. Supported: health, workbooks, enqueue"}
