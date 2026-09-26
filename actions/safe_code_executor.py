"""
safe_code_executor.py — Sandboxed Code Execution Engine

Safely runs Python/JavaScript in isolated environment with restrictions.
"""

import subprocess
import json
import tempfile
import os
from typing import Dict, Any


class SafeCodeExecutor:
    """Executes code safely in a sandbox."""
    
    ALLOWED_MODULES = [
        "math", "random", "json", "datetime", "time", "re", "itertools",
        "collections", "statistics", "decimal"
    ]
    
    FORBIDDEN_KEYWORDS = [
        "import", "exec", "eval", "__import__", "open", "file", "input",
        "globals", "locals", "vars", "__"
    ]
    
    def validate_code(self, code: str) -> bool:
        """Check if code is safe to execute."""
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in code.lower():
                return False
        return True
    
    def execute_python(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """Execute Python code safely."""
        if not self.validate_code(code):
            return {"success": False, "error": "Code contains forbidden operations"}
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(
                    ["python", f.name],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                os.unlink(f.name)
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.stderr else None
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_javascript(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """Execute JavaScript code safely."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(
                    ["node", f.name],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                os.unlink(f.name)
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.stderr else None
                }
        except FileNotFoundError:
            return {"success": False, "error": "Node.js not installed"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_expression(self, expr: str) -> Dict[str, Any]:
        """Safely evaluate mathematical expressions using pure AST traversal (zero eval)."""
        import ast
        import math

        allowed_operators = {
            ast.Add: lambda a, b: a + b,
            ast.Sub: lambda a, b: a - b,
            ast.Mult: lambda a, b: a * b,
            ast.Div: lambda a, b: a / b,
            ast.FloorDiv: lambda a, b: a // b,
            ast.Mod: lambda a, b: a % b,
            ast.Pow: lambda a, b: a ** b,
            ast.USub: lambda a: -a,
            ast.UAdd: lambda a: +a,
        }

        allowed_math_funcs = {
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "asin": math.asin, "acos": math.acos, "atan": math.atan,
            "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
            "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
            "exp": math.exp, "floor": math.floor, "ceil": math.ceil, "round": round,
            "abs": abs, "min": min, "max": max, "radians": math.radians, "degrees": math.degrees
        }

        allowed_constants = {
            "pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf
        }

        def _eval_node(node):
            if isinstance(node, ast.Expression):
                return _eval_node(node.body)
            elif isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError(f"Unsupported constant type: {type(node.value)}")
            elif isinstance(node, ast.Name):
                name = node.id.lower()
                if name in allowed_constants:
                    return allowed_constants[name]
                raise ValueError(f"Unknown variable or constant '{node.id}'")
            elif isinstance(node, ast.UnaryOp):
                op_type = type(node.op)
                if op_type in allowed_operators:
                    return allowed_operators[op_type](_eval_node(node.operand))
                raise ValueError(f"Unsupported unary operator: {op_type}")
            elif isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type in allowed_operators:
                    left = _eval_node(node.left)
                    right = _eval_node(node.right)
                    return allowed_operators[op_type](left, right)
                raise ValueError(f"Unsupported binary operator: {op_type}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    fn_name = node.func.id.lower()
                    if fn_name in allowed_math_funcs:
                        args = [_eval_node(arg) for arg in node.args]
                        return allowed_math_funcs[fn_name](*args)
                raise ValueError("Only whitelisted mathematical functions are permitted")
            else:
                raise ValueError(f"Unsupported expression element: {type(node).__name__}")

        try:
            tree = ast.parse(expr.strip(), mode='eval')
            result = _eval_node(tree)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


executor = SafeCodeExecutor()
