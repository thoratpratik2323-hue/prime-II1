"""
plugin_registry.py — Plugin Auto-Discovery & Dynamic Tool Registry for Prime AI.

Enables seamless registration and lazy auto-discovery of actions/ tools.
Any action module can declare itself as a Prime tool using the @prime_tool decorator.
Auto-converts registered tools to both OpenAI function specs and Gemini function declarations.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("prime.plugins")


class PrimeToolMeta:
    """Metadata container for a registered plugin tool."""

    def __init__(
        self,
        func: Callable,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        required: Optional[List[str]] = None,
        category: str = "general",
        requires: Optional[List[str]] = None,
    ):
        self.func = func
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        self.required = required or []
        self.category = category.lower()
        self.requires = requires or []
        self.disabled = False
        self.disabled_reason: Optional[str] = None

        # Check required dependencies
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        missing = []
        for pkg in self.requires:
            try:
                if importlib.util.find_spec(pkg) is None:
                    missing.append(pkg)
            except Exception:
                missing.append(pkg)
        if missing:
            self.disabled = True
            self.disabled_reason = f"Missing packages: {', '.join(missing)}"

    def to_openai_spec(self) -> Dict[str, Any]:
        """Convert to standard OpenAI Function Calling specification."""
        properties = {}
        for prop_name, prop_spec in self.parameters.items():
            properties[prop_name] = {
                "type": prop_spec.get("type", "string"),
                "description": prop_spec.get("description", ""),
            }
            if "enum" in prop_spec:
                properties[prop_name]["enum"] = prop_spec["enum"]

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": self.required,
                },
            },
        }

    def to_gemini_declaration(self) -> Dict[str, Any]:
        """Convert to Google Gemini Function Declaration format."""
        properties = {}
        type_mapping = {
            "string": "STRING",
            "integer": "INTEGER",
            "number": "NUMBER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT",
        }
        for prop_name, prop_spec in self.parameters.items():
            raw_type = prop_spec.get("type", "string").lower()
            gem_type = type_mapping.get(raw_type, "STRING")
            prop_def: Dict[str, Any] = {
                "type": gem_type,
                "description": prop_spec.get("description", ""),
            }
            if "enum" in prop_spec:
                prop_def["enum"] = prop_spec["enum"]
            properties[prop_name] = prop_def

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": self.required,
            },
        }


class PluginRegistry:
    """Central registry for discovering, inspecting, and executing Prime plugins."""

    def __init__(self):
        self.tools: Dict[str, PrimeToolMeta] = {}
        self._scanned = False

    def register(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        required: Optional[List[str]] = None,
        category: str = "general",
        requires: Optional[List[str]] = None,
    ) -> Callable:
        """Decorator to register a function as a Prime tool."""

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip() or f"Execute {tool_name}"
            meta = PrimeToolMeta(
                func=func,
                name=tool_name,
                description=tool_desc,
                parameters=parameters,
                required=required,
                category=category,
                requires=requires,
            )
            self.tools[tool_name] = meta
            if meta.disabled:
                log.debug("Registered tool %s [DISABLED: %s]", tool_name, meta.disabled_reason)
            else:
                log.debug("Registered plugin tool: %s (Category: %s)", tool_name, category)
            return func

        return decorator

    @property
    def active_tools(self) -> Dict[str, PrimeToolMeta]:
        return {k: v for k, v in self.tools.items() if not v.disabled}

    @property
    def disabled_tools(self) -> Dict[str, PrimeToolMeta]:
        return {k: v for k, v in self.tools.items() if v.disabled}

    def has_tool(self, name: str) -> bool:
        return name in self.active_tools

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        """Return all active tools in OpenAI format."""
        return [t.to_openai_spec() for t in self.active_tools.values()]

    def get_gemini_declarations(self) -> List[Dict[str, Any]]:
        """Return all active tools in Gemini FunctionDeclaration format."""
        return [t.to_gemini_declaration() for t in self.active_tools.values()]

    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered tool by name with arguments."""
        tool = self.active_tools.get(name)
        if not tool:
            if name in self.disabled_tools:
                return {
                    "ok": False,
                    "error": f"Tool '{name}' is currently disabled: {self.disabled_tools[name].disabled_reason}",
                }
            return {"ok": False, "error": f"Tool '{name}' not found in plugin registry."}

        try:
            sig = inspect.signature(tool.func)
            params = sig.parameters
            call_kwargs = {}

            # If function accepts single dict parameter like (parameters: dict)
            if len(params) == 1 and ("parameters" in params or "params" in params or "args" in params):
                res = tool.func(args)
            elif any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
                res = tool.func(**args)
            else:
                # Bind matching kwargs
                for p_name in params:
                    if p_name in args:
                        call_kwargs[p_name] = args[p_name]
                    elif params[p_name].default is not inspect.Parameter.empty:
                        call_kwargs[p_name] = params[p_name].default
                res = tool.func(**call_kwargs)

            # Unpack result if already formatted
            if isinstance(res, dict) and "ok" in res:
                return res
            return {"ok": True, "result": res}
        except Exception as e:
            log.exception("Plugin tool '%s' execution failed: %s", name, e)
            return {"ok": False, "error": f"Plugin execution error: {e}"}

    def scan_plugins(self, actions_dir: Optional[Path] = None) -> int:
        """Scan actions/ directory and import modules to trigger @prime_tool decorators."""
        if self._scanned:
            return len(self.tools)

        if actions_dir is None:
            actions_dir = Path(__file__).resolve().parent / "actions"

        if not actions_dir.exists():
            log.warning("Actions directory not found at: %s", actions_dir)
            return 0

        loaded_count = 0
        skipped_count = 0

        for file_path in actions_dir.glob("*.py"):
            mod_name = file_path.stem
            if mod_name.startswith("__") or mod_name in ("chess_gui", "web_hud"):
                continue

            try:
                importlib.import_module(f"actions.{mod_name}")
                loaded_count += 1
            except Exception as e:
                skipped_count += 1
                log.debug("Skipped action module '%s' during scan: %s", mod_name, e)

        self._scanned = True
        log.info(
            "Plugin scan complete. Scanned %d modules. Registered %d active tools (%d disabled).",
            loaded_count,
            len(self.active_tools),
            len(self.disabled_tools),
        )
        return len(self.active_tools)

    def list_categories(self) -> List[str]:
        return sorted(list({t.category for t in self.tools.values()}))

    def get_tools_by_category(self, category: str) -> List[PrimeToolMeta]:
        cat = category.lower().strip()
        return [t for t in self.tools.values() if t.category == cat]


registry = PluginRegistry()
prime_tool = registry.register
