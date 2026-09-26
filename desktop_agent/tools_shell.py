"""
Universal System, PowerShell, and File Execution Tools for Prime AI.
Enables full arbitrary shell command execution, process management, drive monitoring,
and universal file/path launching.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .registry import ToolError, register


DANGEROUS_SHELL_PATTERNS = [
    r"set-mppreference\s+.*-disable",
    r"stop-service\s+.*(?:windefend|mpssvc|securityhealth)",
    r"\bformat\s+[a-zA-Z]:",
    r"format-(?:volume|disk)\b",
    r"(?:rd|rmdir)\s+.*(?:windows|system32)",
    r"remove-item\s+.*(?:windows|system32)",
    r"del(?:ete)?\s+.*(?:windows|system32)",
    r"(?:iex|invoke-expression)\s*\(?(?:new-object\s+net\.webclient|invoke-webrequest)",
    r"reg\s+save\s+hklm\\(?:sam|system|security)",
    r"vssadmin\s+delete\s+shadows",
]

CRITICAL_SYSTEM_PROCESSES = {
    "csrss.exe", "lsass.exe", "services.exe", "smss.exe", "svchost.exe",
    "winlogon.exe", "system", "idle", "registry", "fontdrvhost.exe"
}


def _validate_powershell_safety(cmd: str) -> None:
    import re
    cmd_lower = cmd.lower().strip()
    for pattern in DANGEROUS_SHELL_PATTERNS:
        if re.search(pattern, cmd_lower):
            raise ToolError(
                "PowerShell command blocked by Prime Safety Guardrails: Destructive system tampering detected."
            )


@register("executePowerShell")
def execute_powershell(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Execute any arbitrary PowerShell command or script on Windows with full capabilities.
    Allows installing packages (winget, pip, npm), checking services, configuring settings,
    running scripts, manipulating files, querying network, and automating system tasks.
    Args:
        command (str): The exact PowerShell command string or script block to execute.
        timeout (int, optional): Execution timeout in seconds. Default 45.
    """
    args = args or {}
    cmd = args.get("command", "").strip()
    if not cmd:
        raise ToolError("'command' parameter is required for executePowerShell.")

    # Apply safety validation
    _validate_powershell_safety(cmd)

    timeout = int(args.get("timeout", 45))

    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        code = proc.returncode

        output_parts = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"[STDERR]\n{stderr}")

        combined = "\n".join(output_parts) if output_parts else "[Command finished with no console output]"

        return {
            "result": combined,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": code,
            "success": (code == 0),
        }
    except subprocess.TimeoutExpired:
        raise ToolError(f"PowerShell command timed out after {timeout} seconds.")
    except Exception as e:
        raise ToolError(f"PowerShell execution failed: {e}") from e


@register("openPath")
def open_path(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Open any file, folder, document, media file, or executable on Windows using its default application.
    Examples:
      - Open a PDF or document: 'C:\\Users\\user\\Documents\\report.pdf'
      - Open a project in VS Code / Explorer: 'C:\\My Projects\\Personal Projects'
      - Open an image or video: 'C:\\Pictures\\photo.png'
    Args:
        path (str): The absolute or relative path to the file, folder, or application.
    """
    args = args or {}
    target_path = args.get("path", "").strip()
    if not target_path:
        raise ToolError("'path' parameter is required for openPath.")

    expanded = os.path.expandvars(os.path.expanduser(target_path))

    if not os.path.exists(expanded):
        raise ToolError(f"Path does not exist: {target_path}")

    try:
        if sys.platform.startswith("win"):
            os.startfile(expanded)
        else:
            subprocess.Popen(["xdg-open", expanded])

        item_type = "folder" if os.path.isdir(expanded) else "file"
        return {
            "result": f"Successfully opened {item_type}: {expanded}",
            "path": expanded,
            "type": item_type,
        }
    except Exception as e:
        raise ToolError(f"Failed to open path '{target_path}': {e}") from e


@register("listDrives")
def list_drives(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    List all physical and logical disk drives on Windows with capacity, free space, and usage.
    """
    try:
        import psutil

        drives = []
        for part in psutil.disk_partitions(all=False):
            if not part.mountpoint:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = round(usage.total / (1024**3), 1)
                free_gb = round(usage.free / (1024**3), 1)
                used_gb = round(usage.used / (1024**3), 1)
                drives.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "percent_used": usage.percent,
                })
            except Exception:
                continue

        summary = "\n".join(
            f"• Drive {d['device']} ({d['fstype']}): {d['free_gb']} GB free of {d['total_gb']} GB ({d['percent_used']}% used)"
            for d in drives
        )
        return {"result": f"System Storage Drives:\n{summary}", "drives": drives}
    except Exception as e:
        raise ToolError(f"Failed to query disk drives: {e}") from e


@register("manageProcess")
def manage_process(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Inspect, terminate, or kill running processes by name or PID.
    Args:
        name (str, optional): Process name to match (e.g. 'chrome.exe', 'notepad.exe').
        pid (int, optional): Process ID to terminate.
        action (str, optional): 'kill' (default) or 'info'.
    """
    args = args or {}
    name = str(args.get("name", "")).strip().lower()
    pid = args.get("pid")
    action = str(args.get("action", "kill")).lower()

    if not name and pid is None:
        raise ToolError("Either 'name' or 'pid' must be provided for manageProcess.")

    try:
        import psutil

        matched = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                if pid is not None and p.info["pid"] == int(pid):
                    matched.append(p)
                elif name and name in (p.info["name"] or "").lower():
                    matched.append(p)
            except Exception:
                continue

        if not matched:
            return {"result": f"No running processes found matching name='{name}' pid='{pid}'."}

        if action == "info":
            lines = [f"• PID {p.pid}: {p.name()} (Mem: {p.memory_info().rss // (1024*1024)} MB)" for p in matched[:15]]
            return {"result": f"Found {len(matched)} matching process(es):\n" + "\n".join(lines)}

        # Terminate
        killed_count = 0
        for p in matched:
            try:
                proc_name = (p.name() or "").lower()
                if proc_name in CRITICAL_SYSTEM_PROCESSES:
                    raise ToolError(f"Cannot terminate protected Windows system process '{proc_name}'.")
                p.kill()
                killed_count += 1
            except ToolError:
                raise
            except Exception:
                pass

        return {"result": f"Successfully terminated {killed_count} process(es) matching '{name or pid}'."}
    except Exception as e:
        raise ToolError(f"Failed to manage process: {e}") from e
