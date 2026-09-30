"""
actions/gtm_outreach.py
Hyper-Personalized GTM Outbound Drafter & WhatsApp / Email Activator for Prime AI.

Integrates with:
- actions/gtm_waterfall.py (Lead enrichment & tech stack)
- actions/gtm_signals.py (Hiring & funding buying signals)
- whatsapp_manager.py (Desktop & web WhatsApp dispatch)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from actions.gtm_waterfall import waterfall_engine
from actions.gtm_signals import signals_scanner
import whatsapp_manager

logger = logging.getLogger("prime.gtm.outreach")
OUTREACH_LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "gtm_outreach_log.json"

class GTMOutreachDrafter:
    """Drafts hyper-personalized messages based on waterfall intelligence and intent triggers."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or OUTREACH_LOG_FILE

    def _log_outreach(self, record: Dict[str, Any]):
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            existing = []
            if self.log_path.exists():
                try:
                    with open(self.log_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
            existing.append(record)
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(existing[-200:], f, indent=2, ensure_ascii=False) # Keep last 200
        except Exception as e:
            logger.warning(f"Failed to append to outreach log: {e}")

    def draft_outreach(self, domain_or_name: str, channel: str = "whatsapp", 
                       target_contact_name: str = "", value_proposition: str = "") -> Dict[str, Any]:
        """
        Draft hyper-personalized message for WhatsApp, Email, or LinkedIn.
        Pulls intelligence and intent hooks automatically.
        """
        domain = waterfall_engine.clean_domain(domain_or_name)
        lead_res = waterfall_engine.enrich_lead(domain)
        lead = lead_res.get("lead", {})
        company_name = lead.get("company_name", domain.split(".")[0].capitalize())

        # Scan intent signals
        signals = signals_scanner.scan_signals(domain)
        hooks = signals.get("conversation_hooks", [])
        hook_chosen = hooks[0] if hooks else f"Following {company_name}'s recent work in the industry."
        intent_score = signals.get("intent_score", 40)
        urgency_tier = signals.get("urgency_tier", "MEDIUM")

        contact_display = target_contact_name.strip()
        if not contact_display and lead.get("founders"):
            contact_display = lead["founders"][0]
        greeting_name = contact_display.split()[0] if contact_display else "there"

        # Default value proposition if none provided
        value_prop = value_proposition.strip() or "streamlining high-impact automation and agentic workflows to multiply your team's velocity"

        channel_clean = channel.lower().strip()

        if channel_clean == "whatsapp":
            message = (
                f"Hey {greeting_name}! 👋\n\n"
                f"{hook_chosen}\n\n"
                f"We've been helping fast-moving teams by {value_prop}.\n\n"
                f"Open to a brief 5-min chat or quick note exchange later this week?"
            )
            draft = {
                "channel": "whatsapp",
                "recipient": contact_display or "Contact",
                "message": message,
                "hook_used": hook_chosen,
                "intent_score": intent_score,
                "urgency_tier": urgency_tier,
                "company": company_name
            }

        elif channel_clean == "email":
            subject = f"Quick question regarding {company_name}'s growth"
            body = (
                f"Hi {greeting_name},\n\n"
                f"{hook_chosen}\n\n"
                f"I'm reaching out because we specialize in {value_prop}. Given your current trajectory, "
                f"I thought this could directly support your roadmap.\n\n"
                f"Would you be open to a 10-minute intro call this Thursday or Friday?\n\n"
                f"Best regards,\nPrime AI"
            )
            draft = {
                "channel": "email",
                "recipient": contact_display or lead.get("emails", [""])[0] if lead.get("emails") else "",
                "subject": subject,
                "body": body,
                "hook_used": hook_chosen,
                "intent_score": intent_score,
                "urgency_tier": urgency_tier,
                "company": company_name
            }

        else: # linkedin / inmail
            message = (
                f"Hi {greeting_name}, {hook_chosen} Impressive momentum at {company_name}. "
                f"We help teams like yours by {value_prop}. Would love to connect and share a quick insight!"
            )
            draft = {
                "channel": "linkedin",
                "recipient": contact_display or "LinkedIn Contact",
                "message": message,
                "hook_used": hook_chosen,
                "intent_score": intent_score,
                "urgency_tier": urgency_tier,
                "company": company_name
            }

        return {
            "ok": True,
            "draft": draft,
            "lead_summary": {
                "domain": domain,
                "company_name": company_name,
                "intent_score": intent_score,
                "tech_stack": lead.get("tech_stack", []),
                "emails": lead.get("emails", []),
            }
        }

    def queue_whatsapp_pitch(self, recipient: str, domain_or_name: str, 
                             send_now: bool = False, custom_note: str = "") -> Dict[str, Any]:
        """
        Drafts and activates a personalized WhatsApp message.
        If send_now=False: Stages the draft safely for user confirmation.
        If send_now=True: Immediately dispatches via whatsapp_manager.send_whatsapp.
        """
        domain = waterfall_engine.clean_domain(domain_or_name)
        draft_res = self.draft_outreach(domain, channel="whatsapp", target_contact_name=recipient, value_proposition=custom_note)
        if not draft_res.get("ok"):
            return draft_res

        draft_data = draft_res["draft"]
        msg_text = draft_data["message"]

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "channel": "whatsapp",
            "recipient": recipient,
            "domain": domain,
            "message": msg_text,
            "intent_score": draft_data["intent_score"],
            "sent_immediately": send_now
        }

        if send_now:
            logger.info(f"[GTM Outreach] Dispatching immediate WhatsApp message to '{recipient}'")
            dispatch_res = whatsapp_manager.send_whatsapp(recipient, msg_text)
            log_entry["dispatch_result"] = dispatch_res
            self._log_outreach(log_entry)
            return {
                "ok": True,
                "status": "sent",
                "recipient": recipient,
                "message": msg_text,
                "dispatch": dispatch_res
            }
        else:
            # Stage draft for confirmation
            logger.info(f"[GTM Outreach] Staged WhatsApp draft for '{recipient}'")
            self._log_outreach(log_entry)
            return {
                "ok": True,
                "status": "staged_draft",
                "recipient": recipient,
                "message": msg_text,
                "hook_used": draft_data["hook_used"],
                "intent_score": draft_data["intent_score"],
                "urgency_tier": draft_data["urgency_tier"],
                "note": "Draft staged successfully. You can approve and send immediately by setting send_now=True."
            }

# Global singleton
outreach_drafter = GTMOutreachDrafter()

def draft_gtm_outreach(domain_or_name: str, channel: str = "whatsapp", target_contact_name: str = "", value_proposition: str = "") -> Dict[str, Any]:
    return outreach_drafter.draft_outreach(domain_or_name, channel=channel, target_contact_name=target_contact_name, value_proposition=value_proposition)

def queue_whatsapp_gtm_pitch(recipient: str, domain_or_name: str, send_now: bool = False, custom_note: str = "") -> Dict[str, Any]:
    return outreach_drafter.queue_whatsapp_pitch(recipient, domain_or_name, send_now=send_now, custom_note=custom_note)
