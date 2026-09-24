import ast
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional



@dataclass
class ASTNode:
    id: int
    kind: str
    text: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    children: List["ASTNode"] = field(default_factory=list)
    value: Optional[str] = None
    type_annotation: Optional[str] = None


@dataclass
class Symbol:
    fqn: str
    kind: str
    file_path: str
    line: int
    col: int
    scope: str


@dataclass
class Scope:
    name: str
    kind: str
    file_path: str
    line: int
    children: List["Scope"] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)


class TreeSitterIntegration:
    def __init__(self) -> None:
        self._next_id: int = 0
        self._ast_cache: Dict[str, ASTNode] = {}
        self._file_ast: Dict[str, ASTNode] = {}
        self._symbols: Dict[str, Symbol] = {}
        self._scopes: Dict[str, Scope] = {}

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _hash(self, file_path: str, content: str) -> str:
        return hashlib.sha256(f"{file_path}:{content}".encode()).hexdigest()

    def parse(self, file_path: str, content: str) -> ASTNode:
        key = self._hash(file_path, content)
        if key in self._ast_cache:
            node = self._ast_cache[key]
        else:
            try:
                tree = ast.parse(content)
                node = self._python_ast_to_node(tree, file_path, content)
                self._ast_cache[key] = node
            except SyntaxError:
                node = ASTNode(
                    id=self._new_id(),
                    kind="error",
                    text=f"<syntax error in {file_path}>",
                    start_line=0,
                    start_col=0,
                    end_line=0,
                    end_col=0,
                )
                self._ast_cache[key] = node
        self._file_ast[file_path] = node
        return node

    def _python_ast_to_node(
        self, node: ast.AST, file_path: str, content: str
    ) -> ASTNode:
        lines = content.splitlines()
        start_line = getattr(node, "lineno", 1) or 1
        start_col = getattr(node, "col_offset", 0) or 0
        end_line = getattr(node, "end_lineno", start_line) or start_line
        end_col = getattr(node, "end_col_offset", start_col) or start_col
        kind = type(node).__name__
        if kind == "Name":
            text = getattr(node, "id", "")
        elif kind in ("FunctionDef", "AsyncFunctionDef", "ClassDef"):
            text = getattr(node, "name", "")
        else:
            text = lines[start_line - 1][start_col:] if start_line <= len(lines) else ""
        children_nodes = [
            self._python_ast_to_node(child, file_path, content)
            for child in ast.iter_child_nodes(node)
        ]
        return ASTNode(
            id=self._new_id(),
            kind=kind,
            text=text,
            start_line=start_line,
            start_col=start_col,
            end_line=end_line,
            end_col=end_col,
            children=children_nodes,
        )

    def _name_of(self, node: ASTNode) -> Optional[str]:
        for child in node.children:
            if child.kind == "Name":
                return child.text
        return None

    def _extract_names(self, node: ASTNode) -> List[str]:
        names: List[str] = []
        for child in node.children:
            if child.kind == "Name":
                names.append(child.text)
        return names

    def extract_symbols(self, file_path: str, content: str) -> List[Symbol]:
        root = self.parse(file_path, content)
        symbols: List[Symbol] = []
        self._walk_symbols(root, file_path, "", symbols)
        for sym in symbols:
            self._symbols[sym.fqn] = sym
        return symbols

    def _walk_symbols(
        self,
        node: ASTNode,
        file_path: str,
        parent_scope: str,
        out: List[Symbol],
    ) -> None:
        scope_prefix = f"{parent_scope}." if parent_scope else ""
        if node.kind == "FunctionDef":
            fqn = f"{scope_prefix}{node.text}"
            out.append(
                Symbol(
                    fqn=fqn,
                    kind="function",
                    file_path=file_path,
                    line=node.start_line,
                    col=node.start_col,
                    scope=parent_scope or "<module>",
                )
            )
            for child in node.children:
                self._walk_symbols(child, file_path, fqn, out)
        elif node.kind == "ClassDef":
            fqn = f"{scope_prefix}{node.text}"
            out.append(
                Symbol(
                    fqn=fqn,
                    kind="class",
                    file_path=file_path,
                    line=node.start_line,
                    col=node.start_col,
                    scope=parent_scope or "<module>",
                )
            )
            for child in node.children:
                self._walk_symbols(child, file_path, fqn, out)
        elif node.kind in ("Assign",):
            for name in self._extract_names(node):
                out.append(
                    Symbol(
                        fqn=f"{scope_prefix}{name}",
                        kind="variable",
                        file_path=file_path,
                        line=node.start_line,
                        col=node.start_col,
                        scope=parent_scope or "<module>",
                    )
                )
        elif node.kind == "AnnAssign":
            for child in node.children:
                if child.kind == "Name":
                    out.append(
                        Symbol(
                            fqn=f"{scope_prefix}{child.text}",
                            kind="variable",
                            file_path=file_path,
                            line=node.start_line,
                            col=node.start_col,
                            scope=parent_scope or "<module>",
                        )
                    )
                    break
        else:
            for child in node.children:
                self._walk_symbols(child, file_path, parent_scope, out)

    def build_scope_tree(self, file_path: str, content: str) -> Scope:
        root = self.parse(file_path, content)
        scope = Scope(
            name="module",
            kind="module",
            file_path=file_path,
            line=1,
        )
        self._walk_scopes(root, file_path, "", scope)
        key = f"{file_path}:scope"
        self._scopes[key] = scope
        return scope

    def _walk_scopes(
        self,
        node: ASTNode,
        file_path: str,
        parent_name: str,
        parent_scope: Scope,
    ) -> None:
        prefix = f"{parent_name}." if parent_name else ""
        if node.kind == "FunctionDef":
            new_scope = Scope(
                name=node.text,
                kind="function",
                file_path=file_path,
                line=node.start_line,
            )
            parent_scope.children.append(new_scope)
            parent_scope.symbols.append(node.text)
            for child in node.children:
                self._walk_scopes(child, file_path, f"{prefix}{node.text}", new_scope)
        elif node.kind == "ClassDef":
            new_scope = Scope(
                name=node.text,
                kind="class",
                file_path=file_path,
                line=node.start_line,
            )
            parent_scope.children.append(new_scope)
            parent_scope.symbols.append(node.text)
            for child in node.children:
                self._walk_scopes(child, file_path, f"{prefix}{node.text}", new_scope)
        else:
            for child in node.children:
                self._walk_scopes(child, file_path, parent_name, parent_scope)

    def get_ast(self, file_path: str) -> Optional[ASTNode]:
        return self._file_ast.get(file_path, None)
