"""
Autonomous Git Sentinel & Pre-Commit Quality Gate for Prime AI.
Performs automated pre-commit audits (detecting exposed secrets, syntax errors, and conflict markers),
generates smart conventional commit messages, and executes safe commits.
"""

from __future__ import annotations

import ast
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.git_sentinel")

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_PATTERNS = [
    re.compile(r"(?:api[_-]?key|secret|token|password|auth_token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", re.IGNORECASE),
    re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}"),
    re.compile(r"gsk_[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{30,}"),
    re.compile(r"csk-[A-Za-z0-9_\-]{20,}"),
]


class GitSentinel:
    """Guards repositories against broken code, leaks, and unvetted commits."""

    def __init__(self, repo_dir: Optional[Path] = None):
        self.repo_dir = repo_dir or BASE_DIR

    def _run_git(self, args: List[str]) -> Tuple[int, str, str]:
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    def audit_pre_commit(self) -> Dict[str, Any]:
        """
        Audit working directory before committing:
        - Check for syntax errors in modified Python files.
        - Check for leaked API keys / secrets.
        - Check for unmerged conflict markers.
        """
        code, out, _ = self._run_git(["status", "--porcelain"])
        if code != 0:
            return {"ok": False, "passed": False, "error": "Not a git repository or git error."}

        if not out.strip():
            return {
                "ok": True,
                "passed": True,
                "clean": True,
                "message": "Working tree is clean. Nothing to commit.",
                "issues": [],
                "modified_files": []
            }

        issues: List[str] = []
        modified_files: List[str] = []

        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            status_code = line[:2].strip()
            file_name = line[2:].strip().strip('"')
            file_path = self.repo_dir / file_name

            modified_files.append(file_name)

            if not file_path.exists() or file_path.is_dir():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # 1. Merge conflict markers
            if any(m in content for m in ("<<<<<<< HEAD", "=======", ">>>>>>>")):
                issues.append(f"Merge conflict markers found in: {file_name}")

            # 2. Hardcoded Secrets Check (exclude test/dummy files)
            if not any(t in file_name.lower() for t in ("test", "example", "mock")):
                for pat in SECRET_PATTERNS:
                    if pat.search(content):
                        issues.append(f"Potential high-entropy secret/token detected in: {file_name}")
                        break

            # 3. Python Syntax Analysis
            if file_name.endswith(".py"):
                try:
                    ast.parse(content, filename=str(file_path))
                except SyntaxError as se:
                    issues.append(f"SyntaxError in {file_name} at line {se.lineno}: {se.msg}")

        passed = len(issues) == 0
        return {
            "ok": True,
            "passed": passed,
            "clean": False,
            "modified_files": modified_files,
            "issues": issues,
            "summary": "Pre-commit audit passed with zero issues." if passed else f"Audit found {len(issues)} critical issue(s)."
        }

    def generate_smart_commit_message(self, modified_files: Optional[List[str]] = None) -> str:
        """Analyze modified files and construct a clean conventional commit message."""
        if modified_files is None:
            _, out, _ = self._run_git(["status", "--porcelain"])
            modified_files = [l[2:].strip().strip('"') for l in out.splitlines() if l.strip()]

        if not modified_files:
            return "chore: update workspace assets"

        has_tests = any("test" in f.lower() for f in modified_files)
        has_docs = any(f.endswith(".md") or "doc" in f.lower() for f in modified_files)
        has_core = any("core" in f.lower() or f.endswith(".py") for f in modified_files)
        has_config = any("config" in f.lower() or f.endswith(".json") for f in modified_files)

        primary_files = [Path(f).name for f in modified_files[:3]]
        file_summary = ", ".join(primary_files)
        if len(modified_files) > 3:
            file_summary += f" and {len(modified_files) - 3} others"

        if has_core:
            return f"feat: optimize core functionality in {file_summary}"
        elif has_tests:
            return f"test: expand unit test coverage for {file_summary}"
        elif has_docs:
            return f"docs: update documentation and specifications in {file_summary}"
        elif has_config:
            return f"chore(config): update configuration settings in {file_summary}"
        else:
            return f"refactor: improve project structure in {file_summary}"

    def safe_commit(self, message: str = "") -> Dict[str, Any]:
        """
        Execute git pre-commit audit and commit only if all security and syntax gates pass.
        """
        audit = self.audit_pre_commit()
        if not audit.get("ok"):
            return audit

        if audit.get("clean"):
            return {"ok": False, "error": "Working tree is clean. Nothing to commit."}

        if not audit.get("passed"):
            return {
                "ok": False,
                "error": "Commit blocked by Pre-Commit Quality Gate.",
                "issues": audit.get("issues", [])
            }

        # Stage files
        self._run_git(["add", "-A"])

        commit_msg = message.strip() or self.generate_smart_commit_message(audit.get("modified_files"))
        code, out, err = self._run_git(["commit", "-m", commit_msg])

        if code == 0:
            return {
                "ok": True,
                "message": f"Successfully committed changes: '{commit_msg}'.",
                "commit_message": commit_msg,
                "output": out
            }
        else:
            return {"ok": False, "error": f"Git commit failed: {err or out}"}

    def generate_pr_summary(self, base_branch: str = "main") -> Dict[str, Any]:
        """Generate structured markdown PR summary with recent commits and changes."""
        code, branch_out, _ = self._run_git(["branch", "--show-current"])
        current_branch = branch_out.strip() or "main"

        code, log_out, _ = self._run_git(["log", f"{base_branch}..HEAD", "--oneline"])
        commits = log_out.splitlines() if log_out.strip() else []

        code, stat_out, _ = self._run_git(["diff", f"{base_branch}..HEAD", "--stat"])

        md_summary = f"""### 🚀 Pull Request: `{current_branch}` -> `{base_branch}`

#### 📝 Overview & Commits
{chr(10).join(f"- {c}" for c in commits) if commits else "- Working branch commits aligned with base."}

#### 📊 Changed Files
```
{stat_out or 'No file differences found.'}
```
"""
        return {
            "ok": True,
            "branch": current_branch,
            "base_branch": base_branch,
            "commit_count": len(commits),
            "summary_markdown": md_summary
        }


_GIT_SENTINEL_INSTANCE: Optional[GitSentinel] = None


def get_git_sentinel() -> GitSentinel:
    """Singleton getter for Git Sentinel."""
    global _GIT_SENTINEL_INSTANCE
    if _GIT_SENTINEL_INSTANCE is None:
        _GIT_SENTINEL_INSTANCE = GitSentinel()
    return _GIT_SENTINEL_INSTANCE


def git_pre_commit_audit() -> Dict[str, Any]:
    """Run security and syntax audit on working directory."""
    return get_git_sentinel().audit_pre_commit()


def git_safe_commit(message: str = "") -> Dict[str, Any]:
    """Audit and safely commit changes."""
    return get_git_sentinel().safe_commit(message)


def generate_pr_summary(base_branch: str = "main") -> Dict[str, Any]:
    """Generate markdown summary for pull request."""
    return get_git_sentinel().generate_pr_summary(base_branch)
