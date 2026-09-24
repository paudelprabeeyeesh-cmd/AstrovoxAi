from code_aware_retrieval.lsp_integration import (
    Diagnostic,
    LSPIntegration,
    Location,
)


def _make_lsp():
    lsp = LSPIntegration()
    lsp.register_symbol(
        "MyClass.foo",
        {
            "file_path": "file:///a.py",
            "line": 3,
            "col": 1,
            "doc": "doc string",
            "kind": "method",
        },
    )
    return lsp


def test_hover_returns_hover_result():
    lsp = _make_lsp()
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "hover",
        "params": {
            "textDocument": {"uri": "file:///a.py"},
            "position": {"line": 2, "character": 1},
        },
    }
    resp = lsp.handle_request(req)
    assert "result" in resp
    assert resp["result"] is not None
    assert resp["result"]["content"] == "doc string"
    assert resp["result"]["file_path"] == "file:///a.py"


def test_hover_no_match():
    lsp = _make_lsp()
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "hover",
        "params": {
            "textDocument": {"uri": "file:///z.py"},
            "position": {"line": 0, "character": 0},
        },
    }
    resp = lsp.handle_request(req)
    assert resp["result"] is None


def test_go_to_definition():
    lsp = _make_lsp()
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/definition",
        "params": {
            "textDocument": {"uri": "file:///a.py"},
            "position": {"line": 2, "character": 1},
        },
    }
    resp = lsp.handle_request(req)
    assert resp["result"] is not None
    assert resp["result"]["file_path"] == "file:///a.py"
    assert resp["result"]["line"] == 3


def test_go_to_definition_no_match():
    lsp = _make_lsp()
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/definition",
        "params": {
            "textDocument": {"uri": "file:///z.py"},
            "position": {"line": 0, "character": 0},
        },
    }
    resp = lsp.handle_request(req)
    assert resp["result"] is None


def test_references_with_refs_in_symbol():
    lsp = LSPIntegration()
    lsp.register_symbol(
        "MyClass.foo",
        {
            "file_path": "file:///a.py",
            "line": 3,
            "col": 1,
            "references": [
                {"file_path": "file:///b.py", "line": 2, "col": 1},
                {"file_path": "file:///c.py", "line": 5, "col": 2},
            ],
        },
    )
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "textDocument/references",
        "params": {
            "textDocument": {"uri": "file:///a.py"},
            "position": {"line": 2, "character": 1},
        },
    }
    resp = lsp.handle_request(req)
    assert len(resp["result"]) == 2
    paths = [r["file_path"] for r in resp["result"]]
    assert "file:///b.py" in paths
    assert "file:///c.py" in paths


def test_references_no_match():
    lsp = _make_lsp()
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "textDocument/references",
        "params": {
            "textDocument": {"uri": "file:///z.py"},
            "position": {"line": 0, "character": 0},
        },
    }
    resp = lsp.handle_request(req)
    assert resp["result"] == []


def test_diagnostic():
    lsp = LSPIntegration()
    diags = [Diagnostic(severity="error", file_path="file:///a.py", line=1, col=1, message="err")]
    lsp.publish_diagnostics(diags)
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "textDocument/diagnostic",
        "params": {"textDocument": {"uri": "file:///a.py"}},
    }
    resp = lsp.handle_request(req)
    assert len(resp["result"]["items"]) == 1
    assert resp["result"]["items"][0]["message"] == "err"


def test_diagnostic_no_match():
    lsp = _make_lsp()
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "textDocument/diagnostic",
        "params": {"textDocument": {"uri": "file:///z.py"}},
    }
    resp = lsp.handle_request(req)
    assert resp["result"]["items"] == []


def test_method_not_found():
    lsp = _make_lsp()
    req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "unknown/method",
    }
    resp = lsp.handle_request(req)
    assert "error" in resp
    assert resp["error"]["code"] == -32601


def test_publish_diagnostics_stores_them():
    lsp = LSPIntegration()
    diags = [Diagnostic(severity="warning", file_path="f.py", line=1, col=1, message="warn")]
    lsp.publish_diagnostics(diags)
    assert len(lsp._diagnostics) == 1


def test_register_symbol():
    lsp = LSPIntegration()
    lsp.register_symbol("x.f", {"file_path": "f.py", "line": 1, "col": 1, "kind": "func"})
    assert "x.f" in lsp._symbols