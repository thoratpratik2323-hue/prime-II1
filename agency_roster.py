"""
agency_roster.py — Integration of 279+ Agency Agent Specialists for Prime AI.
Loads personas from C:\\Users\\thora\\.gemini\\config\\skills\\agency-*
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

SKILLS_DIR = Path(os.getenv("GEMINI_SKILLS_DIR") or (Path.home() / ".gemini" / "config" / "skills"))

_CACHE_AGENTS: Optional[Dict[str, Dict[str, Any]]] = None


def load_all_agency_agents(force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
    global _CACHE_AGENTS
    if _CACHE_AGENTS is not None and not force_reload:
        return _CACHE_AGENTS

    agents = {}
    if not SKILLS_DIR.exists():
        _CACHE_AGENTS = {}
        return {}

    for folder in SKILLS_DIR.glob("agency-*"):
        if not folder.is_dir():
            continue

        skill_file = folder / "SKILL.md"
        if not skill_file.exists():
            continue

        agent_id = folder.name.replace("agency-", "")
        display_name = agent_id.replace("-", " ").title()

        desc = ""
        try:
            content = skill_file.read_text(encoding="utf-8", errors="ignore")
            # Parse YAML frontmatter (including multiline block scalars)
            fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm_text = fm_match.group(1)
                desc_match = re.search(r"^description:\s*(?:[>|]-?\s*)?(.*(?:\n\s+.*)*)", fm_text, re.MULTILINE)
                if desc_match:
                    raw_desc = desc_match.group(1).strip()
                    desc = " ".join(line.strip() for line in raw_desc.splitlines()).strip("'\"")
            if not desc:
                # Fallback to first heading or paragraph
                lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#") and not l.startswith("---")]
                if lines:
                    desc = lines[0][:150]
        except Exception:
            desc = f"Specialist agent for {display_name}"

        # Determine category/division
        cat = "Engineering"
        if any(w in agent_id for w in ("security", "auditor", "penetration", "threat", "compliance")):
            cat = "Security"
        elif any(w in agent_id for w in ("frontend", "backend", "fullstack", "architect", "database", "devops", "sre", "api", "mobile", "rust", "godot", "unity", "unreal", "desktop")):
            cat = "Engineering"
        elif any(w in agent_id for w in ("ui", "ux", "designer", "brand", "visual")):
            cat = "Design"
        elif any(w in agent_id for w in ("marketing", "seo", "growth", "social", "twitter", "instagram", "tiktok", "bilibili", "xiaohongshu", "zhihu", "reddit", "content")):
            cat = "Marketing"
        elif any(w in agent_id for w in ("gis", "geo", "map", "cartography", "bim", "drone")):
            cat = "Geospatial & GIS"
        elif any(w in agent_id for w in ("test", "qa", "evidence", "benchmark")):
            cat = "Testing & QA"
        elif any(w in agent_id for w in ("sales", "deal", "outbound", "coach")):
            cat = "Sales"
        elif any(w in agent_id for w in ("product", "sprint", "prioritizer", "feedback")):
            cat = "Product"
        elif any(w in agent_id for w in ("finance", "pricing", "payable", "bookkeeper", "tax")):
            cat = "Finance"
        elif any(w in agent_id for w in ("game", "audio", "economy", "roblox")):
            cat = "Gaming"
        elif any(w in agent_id for w in ("spatial", "xr", "visionos", "3d")):
            cat = "Spatial Computing"
        else:
            cat = "Specialized"

        agents[agent_id] = {
            "id": agent_id,
            "display_name": display_name,
            "category": cat,
            "description": desc,
            "skill_path": skill_file,
        }

    _CACHE_AGENTS = agents
    return agents


def get_agent_by_name(name_or_id: str) -> Optional[Dict[str, Any]]:
    agents = load_all_agency_agents()
    clean = name_or_id.lower().strip()
    target_id = clean.replace(" ", "-").replace("agency-", "")
    
    # 1. Exact ID match
    if target_id in agents:
        return agents[target_id]

    # 2. Exact display name match
    for v in agents.values():
        if v["display_name"].lower() == clean:
            return v

    # 3. Word boundary match on ID or display name
    candidates = []
    pattern = rf"\b{re.escape(clean)}\b"
    for k, v in agents.items():
        if re.search(pattern, k) or re.search(pattern, v["display_name"].lower()):
            candidates.append(v)

    if candidates:
        candidates.sort(key=lambda x: len(x["id"]))
        return candidates[0]

    # 4. Partial substring fallback, sorted by shortest length
    sub_matches = []
    for k, v in agents.items():
        if target_id in k or clean in v["display_name"].lower():
            sub_matches.append(v)

    if sub_matches:
        sub_matches.sort(key=lambda x: len(x["id"]))
        return sub_matches[0]

    return None


def get_agent_instructions(agent_info: Dict[str, Any]) -> str:
    if not agent_info or not isinstance(agent_info, dict):
        return ""
    path = agent_info.get("skill_path")
    if not path or not Path(path).exists():
        return ""
    try:
        content = Path(path).read_text(encoding="utf-8", errors="ignore")
        # Strip frontmatter
        content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)
        return content.strip()
    except Exception:
        return ""


get_all_agents = load_all_agency_agents
