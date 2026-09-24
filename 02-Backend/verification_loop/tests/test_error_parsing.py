from verification_loop.error_parsing import ErrorParser


TSV_OUTPUT = "src/app.ts(10,5): error TS2322: Type 'string' is not assignable to type 'number'. [ts(2322)]"
MYPY_OUTPUT = "src/main.py:42: error: Incompatible types in assignment (expression has type int, variable has type str)  [assignment]"
RUSTC_OUTPUT = "src/lib.rs:15:10: error[E0308]: mismatched types\n --> src/lib.rs:15:10\n  |\n15 |     let x: &str = 5;\n  |          -- expected `&str`, found integer\n  |\n  = note: expected reference `&str`\n             found integer\n"
ESLINT_OUTPUT = "src/app.js:line 3, col 12, Error, no-unused-vars - 'x' is defined but never used"


def test_parse_tsc_errors():
    parser = ErrorParser()
    result = parser.parse("tsc", TSV_OUTPUT)
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.tool == "tsc"
    assert err.file_path == "src/app.ts"
    assert err.line == 10
    assert err.column == 5
    assert err.severity == "error"
    assert err.rule == "TS2322"
    assert "Type 'string'" in err.message


def test_parse_mypy_errors():
    parser = ErrorParser()
    result = parser.parse("mypy", MYPY_OUTPUT)
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.file_path == "src/main.py"
    assert err.line == 42
    assert err.severity == "error"
    assert err.rule == "assignment"
    assert "Incompatible types" in err.message


def test_parse_rustc_errors():
    parser = ErrorParser()
    result = parser.parse("rustc", RUSTC_OUTPUT)
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.file_path == "src/lib.rs"
    assert err.line == 15
    assert err.column == 10
    assert err.severity == "error"
    assert err.rule == "E0308"
    assert "mismatched types" in err.message


def test_parse_eslint_errors():
    parser = ErrorParser()
    result = parser.parse("eslint", ESLINT_OUTPUT)
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.file_path == "src/app.js"
    assert err.line == 3
    assert err.column == 12
    assert err.severity == "Error"
    assert err.rule == "no-unused-vars"
    assert "never used" in err.message


def test_parse_multiple_errors():
    parser = ErrorParser()
    output = "\n".join([TSV_OUTPUT, MYPY_OUTPUT])
    result = parser.parse("tsc", output)
    assert len(result.errors) == 1


def test_structured_errors_returns_list_of_dicts():
    parser = ErrorParser()
    structured = parser.structured_errors("tsc", TSV_OUTPUT)
    assert isinstance(structured, list)
    assert len(structured) == 1
    assert "tool" in structured[0]
    assert "file" in structured[0]
    assert "line" in structured[0]
    assert "message" in structured[0]


def test_parse_unsupported_tool_raises():
    parser = ErrorParser()
    try:
        parser.parse("unknown_tool", "some output")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for unsupported tool")


def test_summary_counts_by_severity():
    parser = ErrorParser()
    result = parser.parse("tsc", TSV_OUTPUT)
    assert "total_errors" in result.summary
    assert "by_severity" in result.summary
    assert result.summary["total_errors"] == 1
    assert result.summary["by_severity"]["error"] == 1
