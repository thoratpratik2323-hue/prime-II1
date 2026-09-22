"""
claw_developer.py — Autonomous Software Engineering Engine for Prime AI.
Inherited and adapted from Claw Code (ultraworkers/claw-code).

Provides:
- Universal Terminal Execution & Process Supervision
- Precision Code Patching (Surgical Search-and-Replace)
- Autonomous Git Copilot (Status, Diff, AI Commit, Push)
- Automated Unit Test Runner & Verification
- Self-Healing Debugger & Code Repair using Gemini
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import config

log = logging.getLogger("prime.developer")


def run_terminal_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """Execute any shell or CLI command with real-time output capture."""
    target_cwd = Path(cwd).resolve() if cwd else Path.cwd()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(target_cwd),
            timeout=timeout
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "cwd": str(target_cwd)
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": -1,
            "error": f"Command timed out after {timeout} seconds.",
            "cwd": str(target_cwd)
        }
    except Exception as e:
        return {
            "ok": False,
            "returncode": -1,
            "error": str(e),
            "cwd": str(target_cwd)
        }


def patch_file(
    file_path: str,
    search_content: str,
    replace_content: str
) -> Dict[str, Any]:
    """Surgical search-and-replace patching of source code files."""
    path = Path(file_path).resolve()
    if not path.exists():
        return {"ok": False, "error": f"File '{file_path}' does not exist."}

    try:
        content = path.read_text(encoding="utf-8", errors="replace")

        # Normalize line endings for reliable matching
        norm_content = content.replace("\r\n", "\n")
        norm_search = search_content.replace("\r\n", "\n")
        norm_replace = replace_content.replace("\r\n", "\n")

        if norm_search not in norm_content:
            return {
                "ok": False,
                "error": "Target search block was not found in the file. Ensure exact whitespace and line match."
            }

        count = norm_content.count(norm_search)
        if count > 1:
            return {
                "ok": False,
                "error": f"Target search block matched {count} occurrences. Please provide a more specific context chunk."
            }

        # Apply replacement
        patched = norm_content.replace(norm_search, norm_replace, 1)

        # Preserve original line endings
        if "\r\n" in content:
            patched = patched.replace("\n", "\r\n")

        path.write_text(patched, encoding="utf-8")

        return {
            "ok": True,
            "message": f"Successfully patched '{path.name}'.",
            "file": str(path)
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to patch file: {e}"}


def git_automate(
    action: str = "status",
    message: Optional[str] = None,
    cwd: Optional[str] = None
) -> Dict[str, Any]:
    """Autonomous Git operations: status, diff, commit, push, branch."""
    target_cwd = Path(cwd).resolve() if cwd else Path.cwd()
    action = action.lower().strip()

    if action == "status":
        res = run_terminal_command("git status -s", cwd=str(target_cwd))
        return {
            "ok": res["ok"],
            "status": res["stdout"] if res["stdout"] else "Working tree clean.",
            "cwd": str(target_cwd)
        }

    elif action == "diff":
        res = run_terminal_command("git diff", cwd=str(target_cwd))
        return {
            "ok": res["ok"],
            "diff": res["stdout"][:4000] if res["stdout"] else "No unstaged changes.",
            "cwd": str(target_cwd)
        }

    elif action in ("commit", "commit_and_push", "push"):
        # 1. Stage changes
        stage_res = run_terminal_command("git add -A", cwd=str(target_cwd))
        if not stage_res["ok"]:
            return {"ok": False, "error": f"Git add failed: {stage_res.get('stderr')}"}

        # 2. Get staged diff
        diff_res = run_terminal_command("git diff --staged", cwd=str(target_cwd))
        diff_text = diff_res.get("stdout", "")

        if not diff_text and action != "push":
            return {"ok": True, "message": "Nothing to commit, working tree clean."}

        commit_msg = message
        if not commit_msg and diff_text:
            # Generate AI commit message using Gemini
            try:
                from google import genai
                client = genai.Client(api_key=config.gemini_api_key)
                prompt = (
                    "Write a single concise Git conventional commit message (e.g. feat: ..., fix: ..., refactor: ...) "
                    f"for this diff. Output only the commit title:\n{diff_text[:3000]}"
                )
                ai_resp = client.models.generate_content(
                    model=config.get_default_model(config.get_active_provider()),
                    contents=prompt
                )
                commit_msg = ai_resp.text.strip().replace('"', '').replace('`', '')
            except Exception:
                commit_msg = "chore: update codebase"

        if not commit_msg:
            commit_msg = "chore: updates via Prime Developer Engine"

        # Sanitize commit message to prevent shell command injection
        safe_msg = commit_msg.replace('"', "'").replace('\n', ' ').replace('\r', '').strip()
        if not safe_msg:
            safe_msg = "chore: updates via Prime Developer Engine"

        # Commit
        if action in ("commit", "commit_and_push"):
            c_res = run_terminal_command(f'git commit -m "{safe_msg}"', cwd=str(target_cwd))
            if not c_res["ok"]:
                return {"ok": False, "error": f"Git commit failed: {c_res.get('stderr')}"}

        # Push
        if action in ("push", "commit_and_push"):
            p_res = run_terminal_command("git push", cwd=str(target_cwd), timeout=90)
            return {
                "ok": p_res["ok"],
                "committed": True,
                "commit_message": commit_msg,
                "pushed": p_res["ok"],
                "details": p_res.get("stdout") or p_res.get("stderr")
            }

        return {
            "ok": True,
            "committed": True,
            "commit_message": commit_msg,
            "details": "Changes committed locally."
        }

    else:
        return {"ok": False, "error": f"Unsupported git action '{action}'."}


def run_unit_tests(
    framework: str = "pytest",
    path: Optional[str] = None,
    cwd: Optional[str] = None
) -> Dict[str, Any]:
    """Run automated unit tests and parse results."""
    target_cwd = Path(cwd).resolve() if cwd else Path.cwd()
    framework = framework.lower().strip()

    if framework == "pytest":
        cmd = f"pytest {path}" if path else "pytest"
    elif framework in ("unittest", "python"):
        cmd = f"python -m unittest {path}" if path else "python -m unittest discover"
    elif framework == "cargo":
        cmd = f"cargo test {path}" if path else "cargo test"
    elif framework == "npm":
        cmd = f"npm test -- {path}" if path else "npm test"
    else:
        cmd = f"{framework} {path if path else ''}"

    res = run_terminal_command(cmd, cwd=str(target_cwd), timeout=120)
    output = res.get("stdout") or res.get("stderr") or ""

    # Parse common metrics
    passed = "passed" in output.lower() or "ok" in output.lower()
    return {
        "ok": res["ok"] or passed,
        "framework": framework,
        "command": cmd,
        "output": output[:3000],
        "exit_code": res.get("returncode")
    }


def debug_file(
    file_path: str,
    error_trace: Optional[str] = None,
    instructions: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze a file using Gemini 3.6 Flash and generate an autonomous fix."""
    path = Path(file_path).resolve()
    if not path.exists():
        return {"ok": False, "error": f"File '{file_path}' not found."}

    try:
        code_content = path.read_text(encoding="utf-8", errors="replace")

        prompt = (
            f"You are the Prime Autonomous Software Engineering Engine (Claw Code).\n"
            f"File: {path.name}\n"
            f"Path: {str(path)}\n\n"
            f"--- CODE CONTENT ---\n{code_content[:10000]}\n--- END CODE ---\n\n"
        )
        if error_trace:
            prompt += f"--- ERROR TRACEBACK ---\n{error_trace}\n--- END TRACE ---\n\n"
        if instructions:
            prompt += f"--- INSTRUCTIONS ---\n{instructions}\n\n"

        prompt += (
            "Analyze the bug or requirement. Provide a clear diagnosis, and provide the exact search block "
            "and replacement block so it can be patched.\n"
            "Respond in JSON format with keys: 'diagnosis', 'search_block', 'replace_block', 'explanation'."
        )

        from google import genai
        client = genai.Client(api_key=config.gemini_api_key)
        response = client.models.generate_content(
            model=config.default_model,
            contents=prompt,
        )

        return {
            "ok": True,
            "analysis": response.text,
            "file": str(path)
        }
    except Exception as e:
        return {"ok": False, "error": f"Debugging failed: {e}"}
