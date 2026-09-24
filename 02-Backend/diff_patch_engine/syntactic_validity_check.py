import ast
from typing import Optional


class SyntacticValidityChecker:
    @staticmethod
    def check_python(code: str) -> dict:
        try:
            ast.parse(code)
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {"valid": False, "errors": [str(e)]}

    @staticmethod
    def check_generic(code: str, language: str = "python") -> dict:
        if language == "python":
            return SyntacticValidityChecker.check_python(code)
        return {"valid": True, "errors": [], "note": f"no parser for {language}"}

    @staticmethod
    def validate_patched(original: str, patch: str) -> dict:
        try:
            ast.parse(patch)
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {"valid": False, "errors": [str(e)]}

    @staticmethod
    def is_syntactically_valid(code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    @staticmethod
    def get_tree_depth(code: str) -> int:
        try:
            tree = ast.parse(code)
            max_depth = 0

            def depth(node, current):
                nonlocal max_depth
                max_depth = max(max_depth, current)
                for child in ast.iter_child_nodes(node):
                    depth(child, current + 1)

            depth(tree, 0)
            return max_depth
        except SyntaxError:
            return -1
