"""AST-aware code parser using tree-sitter with regex fallback."""

from __future__ import annotations

import ast
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    import tree_sitter  # type: ignore[import-untyped]
    import tree_sitter_language_pack as tlp  # type: ignore[import-untyped]

    TREE_SITTER_AVAILABLE = True
except Exception:  # pragma: no cover
    TREE_SITTER_AVAILABLE = False
    tree_sitter = None  # type: ignore[assignment]
    tlp = None  # type: ignore[assignment]

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".ex": "elixir",
    ".exs": "elixir",
    ".hs": "haskell",
    ".lua": "lua",
    ".r": "r",
    ".dart": "dart",
    ".zig": "zig",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "fish",
    ".sql": "sql",
    ".proto": "proto",
    ".graphql": "graphql",
}


def get_language(file_path: str) -> str | None:
    ext = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    return LANGUAGE_MAP.get(ext)


def parse(content: str, file_path: str) -> dict[str, Any]:
    language_name = get_language(file_path)
    if language_name is None:
        return {"language": None, "ast": None, "symbols": [], "tree_sitter": False}

    symbols: list[dict[str, Any]] = []
    ast_data: Any = None
    used_tree_sitter = False

    if TREE_SITTER_AVAILABLE and tree_sitter is not None and tlp is not None:
        try:
            parser = tree_sitter.Parser()
            lang_module = getattr(tlp, language_name, None)
            if lang_module is not None:
                parser_lang = getattr(lang_module, "language", None)
                if parser_lang is not None:
                    parser.set_language(parser_lang)
                    tree = parser.parse(bytes(content, "utf-8"))
                    ast_data = _tree_sitter_to_dict(tree.root_node)
                    symbols = _extract_symbols_tree_sitter(tree.root_node, language_name)
                    used_tree_sitter = True
        except Exception as exc:
            logger.debug("Tree-sitter parse failed for %s: %s", file_path, exc)

    if not used_tree_sitter:
        try:
            if language_name == "python":
                ast_data = ast.parse(content)
                symbols = _extract_symbols_ast(ast_data, file_path)
            else:
                symbols = _extract_symbols_regex(content, file_path)
        except SyntaxError as exc:
            logger.debug("AST parse failed for %s: %s", file_path, exc)
            symbols = _extract_symbols_regex(content, file_path)
        except Exception as exc:
            logger.debug("Parse fallback for %s: %s", file_path, exc)
            symbols = _extract_symbols_regex(content, file_path)

    return {
        "language": language_name,
        "ast": ast_data,
        "symbols": symbols,
        "tree_sitter": used_tree_sitter,
    }


def _tree_sitter_to_dict(node: Any) -> dict[str, Any]:
    return {
        "type": node.type,
        "start_point": node.start_point,
        "end_point": node.end_point,
        "start_byte": node.start_byte,
        "end_byte": node.end_byte,
        "children": [_tree_sitter_to_dict(c) for c in node.children],
    }


def _extract_symbols_tree_sitter(node: Any, language: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    _walk_tree_sitter(node, language, symbols)
    return symbols


def _walk_tree_sitter(node: Any, language: str, symbols: list[dict[str, Any]]) -> None:
    node_type = node.type
    if language == "python" and node_type in {"function_definition", "class_definition", "async_function_definition"}:
        name_node = node.child_by_field_name("name")
        if name_node:
            symbols.append({
                "kind": node_type.replace("_definition", ""),
                "name": name_node.text.decode("utf-8") if name_node.text else "",
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "end_line": node.end_point[0] + 1,
            })
    elif language in {"javascript", "typescript", "jsx", "tsx"} and node_type in {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "arrow_function",
        "function",
        "class",
        "export_statement",
    }:
        name_node = node.child_by_field_name("name") or node.child_by_field_name("property")
        if name_node:
            symbols.append({
                "kind": node_type.replace("_declaration", "").replace("_definition", ""),
                "name": name_node.text.decode("utf-8") if name_node.text else "",
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "end_line": node.end_point[0] + 1,
            })
    elif language == "go" and node_type == "function_declaration":
        name_node = node.child_by_field_name("name")
        if name_node:
            symbols.append({
                "kind": "function",
                "name": name_node.text.decode("utf-8") if name_node.text else "",
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "end_line": node.end_point[0] + 1,
            })
    elif language == "rust" and node_type in {"function_item", "struct_item", "impl_item", "trait_item"}:
        name_node = node.child_by_field_name("name")
        if name_node:
            symbols.append({
                "kind": node_type.replace("_item", ""),
                "name": name_node.text.decode("utf-8") if name_node.text else "",
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "end_line": node.end_point[0] + 1,
            })
    elif language == "java" and node_type in {"class_declaration", "method_declaration", "interface_declaration"}:
        name_node = node.child_by_field_name("name")
        if name_node:
            symbols.append({
                "kind": node_type.replace("_declaration", ""),
                "name": name_node.text.decode("utf-8") if name_node.text else "",
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "end_line": node.end_point[0] + 1,
            })

    for child in node.children:
        _walk_tree_sitter(child, language, symbols)


def _extract_symbols_ast(tree: ast.AST, file_path: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            symbols.append({
                "kind": "function",
                "name": node.name,
                "line": node.lineno,
                "column": node.col_offset,
                "end_line": node.end_lineno or node.lineno,
            })
        elif isinstance(node, ast.AsyncFunctionDef):
            symbols.append({
                "kind": "async_function",
                "name": node.name,
                "line": node.lineno,
                "column": node.col_offset,
                "end_line": node.end_lineno or node.lineno,
            })
        elif isinstance(node, ast.ClassDef):
            symbols.append({
                "kind": "class",
                "name": node.name,
                "line": node.lineno,
                "column": node.col_offset,
                "end_line": node.end_lineno or node.lineno,
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.append({
                    "kind": "import",
                    "name": alias.name,
                    "line": node.lineno,
                    "column": node.col_offset,
                    "end_line": node.end_lineno or node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                symbols.append({
                    "kind": "import",
                    "name": f"{module}.{alias.name}",
                    "line": node.lineno,
                    "column": node.col_offset,
                    "end_line": node.end_lineno or node.lineno,
                })
    return symbols


_FUNCTION_RE = re.compile(
    r"^\s*(?:async\s+)?(?:def|function|public|private|protected|static)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.MULTILINE,
)
_CLASS_RE = re.compile(r"^\s*(?:class|export\s+class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
_IMPORT_RE = re.compile(r"^\s*(?:import|from|require|use|include)\s+([^;]+)", re.MULTILINE)


def _extract_symbols_regex(content: str, file_path: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    lines = content.splitlines()
    for lineno, line in enumerate(lines, 1):
        m = _FUNCTION_RE.match(line)
        if m:
            symbols.append({"kind": "function", "name": m.group(1), "line": lineno, "column": 0, "end_line": lineno})
            continue
        m = _CLASS_RE.match(line)
        if m:
            symbols.append({"kind": "class", "name": m.group(1), "line": lineno, "column": 0, "end_line": lineno})
            continue
        m = _IMPORT_RE.match(line)
        if m:
            symbols.append({"kind": "import", "name": m.group(1).strip(), "line": lineno, "column": 0, "end_line": lineno})
    return symbols
