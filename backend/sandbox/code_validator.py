"""
Validates generated Python sandbox code for unsafe operations.
"""

import ast

from ..config import ALLOWED_IMPORTS, FORBIDDEN_IMPORTS
from ..utils.error_handler import SandboxRuntimeError, SandboxSecurityError


def validate_code(code: str) -> None:
    """Validate that sandbox code contains only allowed imports and safe calls."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise SandboxRuntimeError(f"Syntax error in generated code: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                package_name = alias.name.split(".")[0]
                if package_name not in ALLOWED_IMPORTS:
                    raise SandboxSecurityError(f"Import of '{package_name}' is forbidden")

        elif isinstance(node, ast.ImportFrom):
            module_name = (node.module or "").split(".")[0]
            if module_name and module_name not in ALLOWED_IMPORTS:
                raise SandboxSecurityError(f"Import from '{module_name}' is forbidden")

        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in {"exec", "eval", "compile", "__import__", "open"}:
                raise SandboxSecurityError(f"Use of '{func.id}' is forbidden")
            if isinstance(func, ast.Attribute):
                attr_name = func.attr
                if attr_name in {"system", "popen", "call", "check_output", "check_call", "run"}:
                    raise SandboxSecurityError(f"Use of '{attr_name}' is forbidden")

        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in FORBIDDEN_IMPORTS:
                raise SandboxSecurityError(f"Access to '{node.value.id}' is forbidden")

        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_IMPORTS:
                raise SandboxSecurityError(f"Use of '{node.id}' is forbidden")
