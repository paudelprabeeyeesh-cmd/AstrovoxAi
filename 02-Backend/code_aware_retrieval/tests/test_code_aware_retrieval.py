import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, r"C:\AstrovoxAi\02-Backend")

from code_aware_retrieval.ast_structural_search import (
    ASTPattern,
    ASTStructuralSearch,
    _node_matches,
    _search,
)
from code_aware_retrieval.call_graph import CallGraph, FunctionDef
from code_aware_retrieval.context_packing import ContextItem, ContextPacking
from code_aware_retrieval.dependency_graph import DependencyGraph, ModuleNode
from code_aware_retrieval.index_maintenance import FileEvent, IndexMaintenance
from code_aware_retrieval.lsp_integration import (
    Diagnostic,
    HoverResult,
    LSPIntegration,
    Location,
)
from code_aware_retrieval.symbol_graph import SymbolDef, SymbolGraph
from code_aware_retrieval.tree_sitter_integration import (
    ASTNode,
    Scope,
    Symbol,
    TreeSitterIntegration,
)


# ============================================================
# Task 81: Tree-sitter Integration
# ============================================================
class TestTreeSitterIntegration:
    def test_parse_returns_ast_node(self):
        tsi = TreeSitterIntegration()
        node = tsi.parse("test.py", "x = 1")
        assert isinstance(node, ASTNode)
        assert node.kind == "Module"

    def test_parse_caches(self):
        tsi = TreeSitterIntegration()
        a = tsi.parse("test.py", "x = 1")
        b = tsi.parse("test.py", "x = 1")
        assert a is b

    def test_parse_different_content(self):
        tsi = TreeSitterIntegration()
        a = tsi.parse("test.py", "x = 1")
        b = tsi.parse("test.py", "x = 2")
        assert a is not b

    def test_parse_syntax_error(self):
        tsi = TreeSitterIntegration()
        node = tsi.parse("bad.py", "def foo(\n")
        assert node.kind == "error"

    def test_extract_symbols_functions(self):
        tsi = TreeSitterIntegration()
        code = "def foo():\n    pass\ndef bar():\n    pass\n"
        syms = tsi.extract_symbols("m.py", code)
        fqns = [s.fqn for s in syms]
        assert "foo" in fqns
        assert "bar" in fqns

    def test_extract_symbols_classes(self):
        tsi = TreeSitterIntegration()
        code = "class MyClass:\n    pass\n"
        syms = tsi.extract_symbols("m.py", code)
        kinds = {s.kind for s in syms}
        assert "class" in kinds

    def test_extract_symbols_variables(self):
        tsi = TreeSitterIntegration()
        code = "x = 1\ny = 2\n"
        syms = tsi.extract_symbols("m.py", code)
        fqns = [s.fqn for s in syms]
        assert "x" in fqns
        assert "y" in fqns

    def test_extract_symbols_scope(self):
        tsi = TreeSitterIntegration()
        code = "def foo():\n    pass\n"
        syms = tsi.extract_symbols("m.py", code)
        assert all(s.scope == "<module>" for s in syms)

    def test_build_scope_tree(self):
        tsi = TreeSitterIntegration()
        code = "def foo():\n    pass\nclass Bar:\n    def baz(self):\n        pass\n"
        scope = tsi.build_scope_tree("m.py", code)
        assert scope.name == "module"
        assert any(c.name == "foo" for c in scope.children)
        bar = next(c for c in scope.children if c.name == "Bar")
        assert any(c.name == "baz" for c in bar.children)

    def test_scope_tree_line_numbers(self):
        tsi = TreeSitterIntegration()
        code = "def foo():\n    pass\n"
        scope = tsi.build_scope_tree("m.py", code)
        foo = next(c for c in scope.children if c.name == "foo")
        assert foo.line == 1

    def test_get_ast_cached(self):
        tsi = TreeSitterIntegration()
        tsi.parse("test.py", "x = 1")
        node = tsi.get_ast("test.py")
        assert node is not None
        assert node.kind == "Module"

    def test_get_ast_missing(self):
        tsi = TreeSitterIntegration()
        assert tsi.get_ast("nonexistent.py") is None


# ============================================================
# Task 82: Symbol Graph
# ============================================================
class TestSymbolGraph:
    def test_index_file(self):
        g = SymbolGraph()
        syms = [SymbolDef(fqn="mod.foo", kind="function", file_path="a.py", line=1, col=0)]
        g.index_file("a.py", syms)
        assert g.get_definition("mod.foo") is not None

    def test_get_definition_missing(self):
        g = SymbolGraph()
        assert g.get_definition("missing") is None

    def test_cross_ref(self):
        g = SymbolGraph()
        g.index_file("a.py", [SymbolDef("a.foo", "function", "a.py", 1, 0)])
        g.add_cross_ref("a.foo", "b.bar")
        refs = g.get_references("b.bar")
        assert "a.foo" in refs

    def test_build_adjacency(self):
        g = SymbolGraph()
        g.index_file(
            "a.py",
            [
                SymbolDef("a.foo", "function", "a.py", 1, 0),
                SymbolDef("b.bar", "function", "b.py", 1, 0),
            ],
        )
        g.add_cross_ref("a.foo", "b.bar")
        adj = g.build_adjacency()
        assert adj.shape == (2, 2)
        assert adj[0, 1] == 1

    def test_adjacency_numpy_dtype(self):
        g = SymbolGraph()
        g.index_file("a.py", [SymbolDef("a.foo", "function", "a.py", 1, 0)])
        adj = g.build_adjacency()
        assert adj.dtype == np.int32

    def test_shortest_path(self):
        g = SymbolGraph()
        g.index_file("a.py", [SymbolDef("a.x", "function", "a.py", 1, 0)])
        g.index_file("b.py", [SymbolDef("b.y", "function", "b.py", 1, 0)])
        g.index_file("c.py", [SymbolDef("c.z", "function", "c.py", 1, 0)])
        g.add_cross_ref("a.x", "b.y")
        g.add_cross_ref("b.y", "c.z")
        path = g.shortest_file_path("a.py", "c.py")
        assert path is not None
        assert path[0] == "a.py"
        assert path[-1] == "c.py"

    def test_shortest_path_no_route(self):
        g = SymbolGraph()
        g.index_file("a.py", [SymbolDef("a.x", "function", "a.py", 1, 0)])
        g.index_file("b.py", [SymbolDef("b.y", "function", "b.py", 1, 0)])
        assert g.shortest_file_path("a.py", "b.py") is None

    def test_multiple_files_adjacency(self):
        g = SymbolGraph()
        for i in range(5):
            g.index_file(f"f{i}.py", [SymbolDef(f"f{i}.f", "function", f"f{i}.py", 1, 0)])
        g.add_cross_ref("f0.f", "f1.f")
        g.add_cross_ref("f1.f", "f2.f")
        g.add_cross_ref("f2.f", "f3.f")
        g.add_cross_ref("f3.f", "f4.f")
        adj = g.build_adjacency()
        assert adj.shape == (5, 5)
        assert adj[0, 1] == 1
        assert adj[4, 0] == 0


# ============================================================
# Task 83: Call Graph
# ============================================================
class TestCallGraph:
    def test_register_function(self):
        cg = CallGraph()
        cg.register_function("foo", "f.py", 1)
        assert cg._funcs["foo"].file_path == "f.py"

    def test_add_call(self):
        cg = CallGraph()
        cg.register_function("caller", "a.py", 1)
        cg.register_function("callee", "b.py", 1)
        cg.add_call("caller", "callee", "a.py", 5)
        mat, funcs = cg.build_matrix()
        ci = funcs.index("caller")
        di = funcs.index("callee")
        assert mat[ci, di] == 1

    def test_callees_of(self):
        cg = CallGraph()
        cg.register_function("caller", "a.py", 1)
        cg.register_function("callee", "b.py", 1)
        cg.add_call("caller", "callee", "a.py", 5)
        callees = cg.callees_of("caller")
        assert "callee" in callees

    def test_callers_of(self):
        cg = CallGraph()
        cg.register_function("caller", "a.py", 1)
        cg.register_function("callee", "b.py", 1)
        cg.add_call("caller", "callee", "a.py", 5)
        callers = cg.callers_of("callee")
        assert "caller" in callers

    def test_dynamic_dispatch_class_method(self):
        cg = CallGraph()
        cg.register_function("MyClass.method", "a.py", 1)
        cg.register_function("Other.method", "b.py", 1)
        cg.register_function("caller", "c.py", 1)
        cg.add_call("caller", "method", "c.py", 5)
        resolved = cg.resolve_dynamic("method", "MyClass")
        assert "MyClass.method" in resolved

    def test_dynamic_dispatch_no_class_fallback(self):
        cg = CallGraph()
        cg.register_function("standalone", "a.py", 1)
        cg.register_function("caller", "b.py", 1)
        cg.add_call("caller", "standalone", "b.py", 5)
        resolved = cg.resolve_dynamic("standalone", None)
        assert "standalone" in resolved

    def test_matrix_numpy_shape(self):
        cg = CallGraph()
        for i in range(3):
            cg.register_function(f"f{i}", "x.py", 1)
        mat, funcs = cg.build_matrix()
        assert mat.shape == (3, 3)
        assert mat.dtype == np.int32

    def test_callees_of_missing(self):
        cg = CallGraph()
        assert cg.callees_of("nonexistent") == []


# ============================================================
# Task 84: Dependency Graph
# ============================================================
class TestDependencyGraph:
    def test_add_module(self):
        dg = DependencyGraph()
        dg.add_module("mod_a", "mod_a.py", ["mod_b"])
        assert dg._modules["mod_a"].file_path == "mod_a.py"

    def test_module_of(self):
        dg = DependencyGraph()
        dg.add_module("mod_a", "mod_a.py", [])
        assert dg.module_of("mod_a.py") == "mod_a"

    def test_detect_cycles_simple(self):
        dg = DependencyGraph()
        dg.add_module("a", "a.py", ["b"])
        dg.add_module("b", "b.py", ["a"])
        cycles = dg.detect_cycles()
        assert len(cycles) >= 1
        flat = [c for cycle in cycles for c in cycle]
        assert "a" in flat
        assert "b" in flat

    def test_no_cycles(self):
        dg = DependencyGraph()
        dg.add_module("a", "a.py", ["b"])
        dg.add_module("b", "b.py", ["c"])
        dg.add_module("c", "c.py", [])
        assert dg.detect_cycles() == []

    def test_topo_sort(self):
        dg = DependencyGraph()
        dg.add_module("c", "c.py", [])
        dg.add_module("b", "b.py", ["c"])
        dg.add_module("a", "a.py", ["b"])
        order = dg.topo_sort()
        assert order.index("c") < order.index("b")
        assert order.index("b") < order.index("a")

    def test_dependents_of(self):
        dg = DependencyGraph()
        dg.add_module("a", "a.py", ["b"])
        dg.add_module("b", "b.py", [])
        deps = dg.dependents_of("b")
        assert "a" in deps

    def test_dependents_of_nonexistent(self):
        dg = DependencyGraph()
        assert dg.dependents_of("missing") == []

    def test_complex_dependencies(self):
        dg = DependencyGraph()
        for i in range(5):
            imports = [f"m{j}" for j in range(max(0, i - 1), i)]
            dg.add_module(f"m{i}", f"m{i}.py", imports)
        cycles = dg.detect_cycles()
        assert len(cycles) == 0


# ============================================================
# Task 85: LSP Integration
# ============================================================
class TestLSPIntegration:
    def test_hover_found(self):
        lsp = LSPIntegration()
        lsp.register_symbol("foo", {"file_path": "a.py", "line": 1, "col": 0, "doc": "hello"})
        resp = lsp.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "hover",
                "params": {
                    "textDocument": {"uri": "a.py"},
                    "position": {"line": 0, "character": 0},
                    "id": 1,
                },
            }
        )
        assert resp["result"]["content"] == "hello"

    def test_hover_not_found(self):
        lsp = LSPIntegration()
        resp = lsp.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "hover",
                "params": {
                    "textDocument": {"uri": "a.py"},
                    "position": {"line": 0, "character": 0},
                    "id": 1,
                },
            }
        )
        assert resp["result"] is None

    def test_go_to_definition(self):
        lsp = LSPIntegration()
        lsp.register_symbol("foo", {"file_path": "a.py", "line": 5, "col": 2, "kind": "function"})
        resp = lsp.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/definition",
                "params": {
                    "textDocument": {"uri": "a.py"},
                    "position": {"line": 4, "character": 2},
                    "id": 1,
                },
            }
        )
        assert resp["result"]["line"] == 5

    def test_references(self):
        lsp = LSPIntegration()
        lsp.register_symbol(
            "foo",
            {
                "file_path": "a.py",
                "line": 1,
                "col": 0,
                "references": [{"file_path": "a.py", "line": 3, "col": 0}],
            },
        )
        resp = lsp.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/references",
                "params": {
                    "textDocument": {"uri": "a.py"},
                    "position": {"line": 0, "character": 0},
                    "id": 1,
                },
            }
        )
        assert len(resp["result"]) == 1

    def test_diagnostics(self):
        lsp = LSPIntegration()
        lsp.publish_diagnostics([Diagnostic("error", "a.py", 1, 0, "syntax error")])
        resp = lsp.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/diagnostic",
                "params": {
                    "textDocument": {"uri": "a.py"},
                    "id": 1,
                },
            }
        )
        assert len(resp["result"]["items"]) == 1
        assert resp["result"]["items"][0]["message"] == "syntax error"

    def test_unknown_method(self):
        lsp = LSPIntegration()
        resp = lsp.handle_request({"jsonrpc": "2.0", "method": "unknown", "id": 1})
        assert "error" in resp

    def test_diagnostics_filter_by_file(self):
        lsp = LSPIntegration()
        lsp.publish_diagnostics(
            [
                Diagnostic("error", "a.py", 1, 0, "err1"),
                Diagnostic("error", "b.py", 1, 0, "err2"),
            ]
        )
        resp = lsp.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/diagnostic",
                "params": {
                    "textDocument": {"uri": "b.py"},
                    "id": 1,
                },
            }
        )
        assert len(resp["result"]["items"]) == 1
        assert resp["result"]["items"][0]["file_path"] == "b.py"


# ============================================================
# Task 86: AST-Structural Search
# ============================================================
class TestASTStructuralSearch:
    def _make_node(self, kind: str, text: str = "", children: list = None) -> ASTNode:
        return ASTNode(
            id=1,
            kind=kind,
            text=text,
            start_line=1,
            start_col=0,
            end_line=1,
            end_col=1,
            children=children or [],
        )

    def test_node_matches_kind(self):
        node = self._make_node("FunctionDef", "foo")
        pat = ASTPattern(kind="FunctionDef")
        assert _node_matches(node, pat)

    def test_node_matches_text(self):
        node = self._make_node("FunctionDef", "my_func")
        pat = ASTPattern(kind="FunctionDef", text_substr="func")
        assert _node_matches(node, pat)

    def test_node_no_match_kind(self):
        node = self._make_node("ClassDef", "Foo")
        pat = ASTPattern(kind="FunctionDef")
        assert not _node_matches(node, pat)

    def test_search_finds_match(self):
        child = self._make_node("FunctionDef", "target")
        root = self._make_node("Module", children=[child])
        searcher = ASTStructuralSearch()
        searcher.index([root])
        results = searcher.query(ASTPattern(kind="FunctionDef", text_substr="target"))
        assert len(results) == 1

    def test_search_multiple_matches(self):
        children = [self._make_node("FunctionDef", f"fn{i}") for i in range(3)]
        root = self._make_node("Module", children=children)
        searcher = ASTStructuralSearch()
        searcher.index([root])
        results = searcher.query(ASTPattern(kind="FunctionDef"))
        assert len(results) == 3

    def test_query_with_score(self):
        child = self._make_node("FunctionDef", "important_func")
        root = self._make_node("Module", children=[child])
        searcher = ASTStructuralSearch()
        searcher.index([root])
        scored = searcher.query_with_score(ASTPattern(kind="FunctionDef", text_substr="func"))
        assert len(scored) == 1
        assert scored[0][1] == 1.0

    def test_search_no_match(self):
        root = self._make_node("Module", children=[self._make_node("Assign", "x = 1")])
        searcher = ASTStructuralSearch()
        searcher.index([root])
        results = searcher.query(ASTPattern(kind="FunctionDef"))
        assert results == []

    def test_search_empty_index(self):
        searcher = ASTStructuralSearch()
        results = searcher.query(ASTPattern(kind="FunctionDef"))
        assert results == []

    def test_search_children_pattern(self):
        inner = self._make_node("Name", "arg")
        func = self._make_node("FunctionDef", "foo", children=[inner])
        root = self._make_node("Module", children=[func])
        searcher = ASTStructuralSearch()
        searcher.index([root])
        results = searcher.query(
            ASTPattern(kind="FunctionDef", children_patterns=[ASTPattern(kind="Name")])
        )
        assert len(results) == 1


# ============================================================
# Task 87: Context Packing
# ============================================================
class TestContextPacking:
    def test_empty_pack(self):
        cp = ContextPacking(budget=100)
        assert cp.pack() == []

    def test_pack_basic(self):
        cp = ContextPacking(budget=100)
        cp.add(ContextItem("a", "hello world", recency=1.0, graph_distance=0, is_anchor=True))
        cp.add(ContextItem("b", "foo bar baz", recency=0.5, graph_distance=2, is_anchor=False))
        result = cp.pack()
        assert len(result) >= 1
        assert all(len(i.content) <= 100 for i in result)

    def test_anchor_priority(self):
        cp = ContextPacking(budget=100)
        cp.add(ContextItem("a", "anchor_content_that_is_long", recency=0.1, graph_distance=10, is_anchor=True))
        cp.add(ContextItem("b", "short", recency=1.0, graph_distance=0, is_anchor=False))
        result = cp.pack()
        top = result[0]
        assert top.id == "a"

    def test_pack_exceeds_budget_downgrade(self):
        cp = ContextPacking(budget=20)
        cp.add(ContextItem("a", "0123456789", recency=1.0, graph_distance=0, is_anchor=False))
        cp.add(ContextItem("b", "0123456789", recency=0.9, graph_distance=0, is_anchor=False))
        result = cp.pack()
        total = sum(len(i.content) for i in result)
        assert total <= 20 or all(i.score < 1.0 for i in result)

    def test_recency_influences_score(self):
        cp = ContextPacking(budget=1000)
        cp.add(ContextItem("a", "A" * 100, recency=1.0, graph_distance=5, is_anchor=False))
        cp.add(ContextItem("b", "B" * 100, recency=0.1, graph_distance=0, is_anchor=False))
        result = cp.pack()
        assert result[0].id == "a"

    def test_set_budget(self):
        cp = ContextPacking(budget=100)
        cp.set_budget(200)
        assert cp._budget == 200

    def test_pack_all_fit(self):
        cp = ContextPacking(budget=10000)
        for i in range(10):
            cp.add(
                ContextItem(
                    str(i),
                    f"content_{i}",
                    recency=float(i) / 10,
                    graph_distance=i,
                    is_anchor=(i == 0),
                )
            )
        result = cp.pack()
        assert len(result) == 10

    def test_numpy_usage_in_scoring(self):
        cp = ContextPacking(budget=1000)
        for i in range(5):
            cp.add(
                ContextItem(
                    str(i),
                    f"content_{i}",
                    recency=float(i),
                    graph_distance=5 - i,
                    is_anchor=(i == 4),
                )
            )
        result = cp.pack()
        scores = np.array([i.score for i in result])
        assert np.all(np.diff(scores) <= 1e-6)


# ============================================================
# Task 88: Index Maintenance
# ============================================================
class TestIndexMaintenance:
    def _make_parser(self):
        class _P:
            def parse(self, path, content):
                return {"kind": "Module", "path": path}

        return _P()

    def test_full_reindex(self):
        im = IndexMaintenance(self._make_parser())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            name = f.name
        try:
            count = im.full_reindex([name])
            assert count == 1
            assert name in im._index
        finally:
            os.unlink(name)

    def test_incremental_reindex(self):
        im = IndexMaintenance(self._make_parser())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            name = f.name
        try:
            im.full_reindex([name])
            event = FileEvent(path=name, event_type="modified", content_hash="abc")
            im.on_file_event(event)
            count = im.incremental_reindex()
            assert count == 1
        finally:
            os.unlink(name)

    def test_incremental_no_change(self):
        im = IndexMaintenance(self._make_parser())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            name = f.name
        try:
            im.full_reindex([name])
            with open(name, "r") as f:
                content = f.read()
            event = FileEvent(path=name, event_type="modified", content_hash=im._hash_content(name, content))
            im.on_file_event(event)
            count = im.incremental_reindex()
            assert count == 0
        finally:
            os.unlink(name)

    def test_consistency_check_consistent(self):
        im = IndexMaintenance(self._make_parser())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            name = f.name
        try:
            im.full_reindex([name])
            stats = im.consistency_check()
            assert stats["consistent"] is True
            assert stats["in_index_not_hashed"] == []
            assert stats["in_hash_not_indexed"] == []
        finally:
            os.unlink(name)

    def test_get_index_stats(self):
        im = IndexMaintenance(self._make_parser())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            name = f.name
        try:
            im.full_reindex([name])
            stats = im.get_index_stats()
            assert stats["total_files"] == 1
        finally:
            os.unlink(name)

    def test_on_file_event_sets_dirty(self):
        im = IndexMaintenance(self._make_parser())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            name = f.name
        try:
            event = FileEvent(path=name, event_type="created", content_hash="xyz")
            im.on_file_event(event)
            assert name in im._dirty
            assert im._hashes[name] == "xyz"
        finally:
            os.unlink(name)

    def test_multiple_files_reindex(self):
        im = IndexMaintenance(self._make_parser())
        names = []
        try:
            for i in range(3):
                tf = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
                tf.write(f"x = {i}\n")
                tf.close()
                names.append(tf.name)
            count = im.full_reindex(names)
            assert count == 3
        finally:
            for n in names:
                if os.path.exists(n):
                    os.unlink(n)

    def test_missing_file_handled(self):
        im = IndexMaintenance(self._make_parser())
        count = im.full_reindex(["nonexistent_file.py"])
        assert count == 0

    def test_numpy_adjacency_shape(self):
        im = IndexMaintenance(self._make_parser())
        names = []
        try:
            for i in range(5):
                tf = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
                tf.write(f"x = {i}\n")
                tf.close()
                names.append(tf.name)
            im.full_reindex(names)
            stats = im.get_index_stats()
            assert stats["total_files"] == 5
            assert isinstance(stats["total_files"], (int, np.integer))
        finally:
            for n in names:
                if os.path.exists(n):
                    os.unlink(n)
