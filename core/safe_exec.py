"""
core/safe_exec.py — AST-based allowlist validator for the small amount of
LLM-generated Python this project executes (desktop automation snippets,
GUI action scripts, workflow conditions).

Why this exists
----------------
The previous approach in several modules (actions/desktop.py,
actions/autonomous_autopilot.py, actions/workflow_engine.py,
actions/safe_code_executor.py) tried to sandbox generated code by either:
  - restricting the `__builtins__` dict passed to exec()/eval(), or
  - blocklisting a few keywords/substrings ("import", "eval", "__", ...).

Neither approach is a real sandbox. Attribute access is NOT gated by
`__builtins__` at all, so code like:

    ().__class__.__bases__[0].__subclasses__()

can walk from *any* object to os/subprocess-capable classes regardless of
what's in `__builtins__`, and keyword blocklists are trivially bypassed
with string concatenation, getattr(obj, 'imp'+'ort'), etc.

This module instead statically parses the code with `ast` and only allows
a small, explicit set of node types and call targets before anything is
executed. Nothing outside the allowlist is permitted, so unknown/unsafe
constructs fail closed (raise UnsafeCodeError) rather than silently pass
through.

This is still not a full security sandbox (CPU/memory/time exhaustion,
for instance, need a process-level timeout around the caller), but it
closes the specific escape class this project's generated snippets were
vulnerable to: reaching arbitrary attributes/dunder chains to get at
os/subprocess/builtins.
"""

from __future__ import annotations

import ast
from typing import Dict, Iterable, Set


class UnsafeCodeError(Exception):
    """Raised when generated code contains a construct outside the allowlist."""


# Statement types we allow at all. Deliberately excludes:
# Import, ImportFrom, ClassDef, FunctionDef, AsyncFunctionDef, Lambda,
# Global, Nonlocal, Delete, With, Try (exception handling can hide tricks
# and isn't needed for these short automation snippets), Raise.
_ALLOWED_STMT_TYPES = (
    ast.Expr,
    ast.Assign,
    ast.AugAssign,
    ast.AnnAssign,
    ast.If,
    ast.For,
    ast.While,
    ast.Pass,
    ast.Break,
    ast.Continue,
)

# Expression node types we allow.
_ALLOWED_EXPR_TYPES = (
    ast.Call,
    ast.Attribute,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Subscript,
    ast.Index,  # py<3.9 compat, harmless if unused
    ast.Slice,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.FloorDiv,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.USub,
    ast.UAdd,
    ast.keyword,
)

_ALWAYS_BLOCKED_NAMES = {
    "eval", "exec", "compile", "open", "input", "__import__",
    "globals", "locals", "vars", "dir", "delattr", "setattr",
    "getattr", "hasattr", "memoryview", "breakpoint", "help",
}


# Pure, side-effect-free builtins that are safe to call bare (not via
# attribute access) in every snippet, regardless of caller-specific
# allowlists. Deliberately excludes getattr/setattr/eval/exec/open/etc.
_SAFE_BARE_CALLS = {
    "range", "len", "str", "int", "float", "bool", "abs", "round",
    "min", "max", "sum", "enumerate", "sorted", "list", "dict", "tuple",
    "print",
}


def validate_ast(
    code: str,
    allowed_names: Iterable[str],
    allowed_attrs: Dict[str, Set[str]],
) -> None:
    """Raise UnsafeCodeError if `code` contains anything outside the allowlist.

    allowed_names:  bare names the snippet may reference, e.g. {"pyautogui",
                     "time", "Path"} — these are the pre-injected objects.
    allowed_attrs:  for each allowed base name, the set of attribute names
                     that may be accessed on it, e.g.
                     {"pyautogui": {"click", "moveTo", "hotkey"},
                      "time": {"sleep"}}.
                     Chained/deep attribute access beyond one level is
                     rejected — snippets should be flat calls like
                     `pyautogui.click(x, y)`, not `a.b.c.d()`.
    """
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        raise UnsafeCodeError(f"Code failed to parse: {e}") from e

    allowed_names = set(allowed_names)

    for node in ast.walk(tree):
        # Any statement/expression type not explicitly allowed -> reject.
        if isinstance(node, ast.stmt) and not isinstance(node, _ALLOWED_STMT_TYPES):
            raise UnsafeCodeError(f"Disallowed statement: {type(node).__name__}")
        if isinstance(node, ast.expr) and not isinstance(node, _ALLOWED_EXPR_TYPES):
            raise UnsafeCodeError(f"Disallowed expression: {type(node).__name__}")

        # Block every dunder / private-looking attribute outright. This is
        # what kills the classic ().__class__.__bases__... escape chain.
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise UnsafeCodeError(f"Attribute access to '{node.attr}' is not allowed.")
            if not isinstance(node.value, ast.Name):
                raise UnsafeCodeError("Only single-level attribute access is allowed (e.g. module.func).")
            base = node.value.id
            if base not in allowed_attrs or node.attr not in allowed_attrs[base]:
                raise UnsafeCodeError(f"'{base}.{node.attr}' is not on the allowlist.")

        if isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise UnsafeCodeError(f"Name '{node.id}' is not allowed.")
            if node.id in _ALWAYS_BLOCKED_NAMES:
                raise UnsafeCodeError(f"'{node.id}' is explicitly blocked.")
            # A bare name is only ever valid as an allowed pre-injected
            # object (used before a `.` for an allowed attribute) or as a
            # local variable target (ast.Store handled implicitly by not
            # restricting Store here — assignment targets are checked by
            # the Name node covering both Load and Store contexts).
            if isinstance(node.ctx, ast.Load) and node.id not in allowed_names:
                # Allow simple local variables: if it's not a known
                # pre-injected object, it must have appeared as a Store
                # target earlier in this same snippet.
                pass  # local variable use — fine, Python's own NameError
                       # will fire at runtime if it was never assigned.

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in _ALWAYS_BLOCKED_NAMES:
                    raise UnsafeCodeError(f"Calling '{func.id}' is not allowed.")
                if func.id not in _SAFE_BARE_CALLS and func.id not in allowed_names:
                    raise UnsafeCodeError(
                        f"Calling bare function '{func.id}' is not allowed."
                    )
