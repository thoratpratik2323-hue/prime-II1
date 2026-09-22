"""
mcp_bridge.py — Model Context Protocol (MCP) Bridge for Prime AI.
Inherited from OpenJarvis extensible MCP architecture.

Allows Prime AI to dynamically connect to standard MCP servers (Filesystem, GitHub,
Brave Search, PostgreSQL, Notion, SQLite, etc.) via JSON-RPC 2.0 over stdio and expose
their tools seamlessly to the AI brain alongside Prime's native desktop automation arsenal.
"""

from __future__ import annotations

import os
import sys
import json
import logging
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from rich.console import Console
from rich.table import Table

log = logging.getLogger("prime.mcp")
console = Console()

BASE_DIR = Path(__file__).resolve().parent
MCP_CONFIG_PATH = BASE_DIR / "mcp_servers.json"


class MCPSession:
    """Manages an active JSON-RPC stdio subprocess session with an MCP server."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self._msg_id = 0
        self._lock = threading.Lock()
        self.tools: List[Dict[str, Any]] = []

    def start(self) -> bool:
        """Spawn the server process and execute the MCP initialization handshake."""
        cmd = self.config.get("command", "npx")
        args = self.config.get("args", [])
        env = os.environ.copy()
        if "env" in self.config and isinstance(self.config["env"], dict):
            env.update({k: str(v) for k, v in self.config["env"].items()})

        full_cmd = [cmd] + args
        try:
            self.process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding="utf-8",
                bufsize=1,
                shell=(sys.platform == "win32"),
            )
            log.info("Spawned MCP server '%s' with PID %d", self.name, self.process.pid)

            # Perform initialize handshake
            init_res = self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "prime-ai", "version": "2.0.0"},
                },
            )
            if not init_res:
                log.warning("MCP server '%s' initialization response empty.", self.name)
                return False

            # Send initialized notification
            self._send_notification("notifications/initialized", {})

            # Discover available tools
            tools_res = self._send_request("tools/list", {})
            if tools_res and "result" in tools_res and "tools" in tools_res["result"]:
                self.tools = tools_res["result"]["tools"]
                log.info("Discovered %d tools from MCP server '%s'", len(self.tools), self.name)

            return True
        except Exception as e:
            log.warning("Failed to start MCP server '%s': %s", self.name, e)
            self.stop()
            return False

    def stop(self) -> None:
        """Terminate the server process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via MCP JSON-RPC 'tools/call'."""
        res = self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
        if not res:
            return {"ok": False, "error": "No response from MCP server."}
        if "error" in res:
            return {"ok": False, "error": res["error"].get("message", "MCP Tool Error")}
        result_data = res.get("result", {})
        # MCP tools return content blocks
        content = result_data.get("content", [])
        text_out = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                text_out.append(c.get("text", ""))
            else:
                text_out.append(str(c))
        final_str = "\n".join(text_out) if text_out else str(result_data)
        return {"ok": True, "result": final_str}

    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.process or self.process.poll() is not None:
                return None
            self._msg_id += 1
            payload = {
                "jsonrpc": "2.0",
                "id": self._msg_id,
                "method": method,
                "params": params,
            }
            try:
                msg_str = json.dumps(payload) + "\n"
                self.process.stdin.write(msg_str)
                self.process.stdin.flush()

                # Read response line
                line = self.process.stdout.readline()
                if not line:
                    return None
                return json.loads(line.strip())
            except Exception as e:
                log.warning("MCP send_request failed on '%s': %s", self.name, e)
                return None

    def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        with self._lock:
            if not self.process or self.process.poll() is not None:
                return
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
            try:
                msg_str = json.dumps(payload) + "\n"
                self.process.stdin.write(msg_str)
                self.process.stdin.flush()
            except Exception as e:
                log.warning("MCP send_notification failed: %s", e)


class MCPBridge:
    """Manages external MCP server configurations, lifecycle, and tool proxying."""

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, MCPSession] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load MCP server definitions from mcp_servers.json."""
        if not MCP_CONFIG_PATH.exists():
            template = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", str(Path.home())],
                        "enabled": False,
                        "description": "Standard MCP Filesystem server"
                    },
                    "github": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github"],
                        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
                        "enabled": False,
                        "description": "Standard MCP GitHub server"
                    },
                    "brave-search": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                        "env": {"BRAVE_API_KEY": ""},
                        "enabled": False,
                        "description": "Standard MCP Brave Search server"
                    }
                }
            }
            try:
                with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(template, f, indent=2)
            except Exception:
                pass

        try:
            with open(MCP_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.servers = data.get("mcpServers", {})
        except Exception:
            self.servers = {}

    def get_server_list(self) -> List[Dict[str, Any]]:
        """Return formatted list of all configured MCP servers."""
        out = []
        for name, cfg in self.servers.items():
            out.append({
                "name": name,
                "command": cfg.get("command", ""),
                "enabled": cfg.get("enabled", False),
                "running": name in self.active_sessions,
                "description": cfg.get("description", "MCP Server"),
                "tools_count": len(self.active_sessions[name].tools) if name in self.active_sessions else 0,
            })
        return out

    def enable_server(self, name: str, enable: bool = True) -> bool:
        """Enable or disable an MCP server, starting or stopping its process."""
        if name in self.servers:
            self.servers[name]["enabled"] = enable
            try:
                with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump({"mcpServers": self.servers}, f, indent=2)

                if enable:
                    return self.start_server(name)
                else:
                    self.stop_server(name)
                    return True
            except Exception:
                return False
        return False

    def start_server(self, name: str) -> bool:
        """Start an active session with an enabled MCP server."""
        if name not in self.servers:
            return False
        cfg = self.servers[name]
        session = MCPSession(name, cfg)
        if session.start():
            self.active_sessions[name] = session
            # Auto-register tools into plugin registry
            self._register_mcp_tools(name, session)
            return True
        return False

    def stop_server(self, name: str) -> None:
        """Stop an active MCP server session."""
        if name in self.active_sessions:
            self.active_sessions[name].stop()
            del self.active_sessions[name]

    def _register_mcp_tools(self, server_name: str, session: MCPSession) -> None:
        """Register discovered MCP tools into plugin_registry so AI can call them."""
        try:
            from plugin_registry import registry
            for t in session.tools:
                t_name = f"mcp_{server_name}_{t.get('name', '')}"
                desc = t.get("description", f"MCP Tool from {server_name}")
                input_schema = t.get("inputSchema", {})
                props = input_schema.get("properties", {})
                req = input_schema.get("required", [])

                # Create wrapper closure
                orig_tool_name = t.get("name", "")
                def make_wrapper(s_sess, o_name):
                    return lambda **kwargs: s_sess.call_tool(o_name, kwargs)

                tool_func = make_wrapper(session, orig_tool_name)
                tool_func.__doc__ = desc
                tool_func.__name__ = t_name

                registry.register(
                    name=t_name,
                    description=desc,
                    parameters=props,
                    required=req,
                    category=f"mcp-{server_name}",
                )(tool_func)

            log.info("Registered %d MCP tools from '%s' into plugin registry.", len(session.tools), server_name)
        except Exception as e:
            log.warning("Could not register MCP tools for '%s': %s", server_name, e)

    def render_mcp_table(self) -> Table:
        """Render Rich table of configured MCP servers."""
        table = Table(title="🔌 MODEL CONTEXT PROTOCOL (MCP) SERVERS", border_style="bright_cyan")
        table.add_column("Server", style="bold cyan", width=16)
        table.add_column("Status", justify="center", width=14)
        table.add_column("Tools", justify="center", width=8)
        table.add_column("Command", style="dim white", width=25)
        table.add_column("Description", style="white")

        for s in self.get_server_list():
            if s["running"]:
                status = "[bold green]ONLINE[/bold green]"
            elif s["enabled"]:
                status = "[yellow]ENABLED[/yellow]"
            else:
                status = "[dim]DISABLED[/dim]"
            table.add_row(
                s["name"],
                status,
                str(s["tools_count"]),
                s["command"],
                s["description"]
            )
        return table


mcp_bridge = MCPBridge()
