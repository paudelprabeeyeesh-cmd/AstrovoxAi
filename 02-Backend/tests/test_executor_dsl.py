"""Tests for the AI DSL (lexer + parser + AST)."""

from __future__ import annotations

import unittest

from app.executor.dsl import (
    AnalyzeStatement,
    AskStatement,
    EmailStatement,
    GenerateStatement,
    Lexer,
    LexerError,
    LoadStatement,
    ParallelBlock,
    ParseError,
    Parser,
    Program,
    SearchStatement,
    SummarizeStatement,
    TokenType,
    parse,
)


class LexerTest(unittest.TestCase):
    def test_keywords_and_identifiers(self):
        tokens = Lexer("LOAD foo\nSEARCH bar").tokenize()
        self.assertEqual(tokens[0].type, TokenType.KEYWORD)
        self.assertEqual(tokens[0].value, "LOAD")
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].value, "foo")
        self.assertEqual(tokens[2].type, TokenType.NEWLINE)
        self.assertEqual(tokens[3].value, "SEARCH")
        self.assertEqual(tokens[4].value, "bar")

    def test_strings(self):
        tokens = Lexer('LOAD "document.pdf" AS doc').tokenize()
        self.assertEqual(tokens[0].value, "LOAD")
        self.assertEqual(tokens[1].type, TokenType.STRING)
        self.assertEqual(tokens[1].value, "document.pdf")
        self.assertEqual(tokens[2].value, "AS")
        self.assertEqual(tokens[3].value, "doc")

    def test_numbers(self):
        tokens = Lexer("SUMMARIZE doc LENGTH 200").tokenize()
        numbers = [t for t in tokens if t.type == TokenType.NUMBER]
        self.assertEqual(numbers[-1].value, 200)

    def test_comments_are_skipped(self):
        tokens = Lexer("# hello\nLOAD doc").tokenize()
        # First non-newline token is LOAD
        first = next(t for t in tokens if t.type != TokenType.NEWLINE)
        self.assertEqual(first.value, "LOAD")
        self.assertEqual(tokens[-2].value, "doc")

    def test_unterminated_string_raises(self):
        with self.assertRaises(LexerError):
            Lexer('LOAD "unterminated').tokenize()


class ParserTest(unittest.TestCase):
    def test_load_with_alias(self):
        program = parse('LOAD "doc.pdf" AS doc')
        self.assertEqual(len(program.statements), 1)
        self.assertIsInstance(program.statements[0], LoadStatement)
        self.assertEqual(program.statements[0].alias, "doc")
        self.assertEqual(program.statements[0].target, "doc.pdf")

    def test_search_with_limit_and_alias(self):
        program = parse('SEARCH "auth" IN doc LIMIT 5 AS hits')
        stmt = program.statements[0]
        self.assertIsInstance(stmt, SearchStatement)
        self.assertEqual(stmt.query, "auth")
        self.assertEqual(stmt.target, "doc")
        self.assertEqual(stmt.limit, 5)
        self.assertEqual(stmt.alias, "hits")

    def test_summarize(self):
        program = parse("SUMMARIZE hits LENGTH 200 AS summary")
        stmt = program.statements[0]
        self.assertIsInstance(stmt, SummarizeStatement)
        self.assertEqual(stmt.length, 200)
        self.assertEqual(stmt.alias, "summary")

    def test_generate(self):
        program = parse('GENERATE "report.md" TEMPLATE "default" AS out')
        stmt = program.statements[0]
        self.assertIsInstance(stmt, GenerateStatement)
        self.assertEqual(stmt.target, "report.md")
        self.assertEqual(stmt.template, "default")

    def test_email(self):
        program = parse('EMAIL "report.md" TO "alice@example.com"')
        stmt = program.statements[0]
        self.assertIsInstance(stmt, EmailStatement)
        self.assertEqual(stmt.recipient, "alice@example.com")

    def test_analyze(self):
        program = parse("ANALYZE doc AS doc_analysis")
        stmt = program.statements[0]
        self.assertIsInstance(stmt, AnalyzeStatement)
        self.assertEqual(stmt.alias, "doc_analysis")

    def test_ask(self):
        program = parse('ASK "What is the conclusion?" AS answer')
        stmt = program.statements[0]
        self.assertIsInstance(stmt, AskStatement)
        self.assertEqual(stmt.alias, "answer")

    def test_save(self):
        program = parse('SAVE result TO "out.json"')
        stmt = program.statements[0]
        from app.executor.dsl import SaveStatement
        self.assertIsInstance(stmt, SaveStatement)
        self.assertEqual(stmt.destination, "out.json")

    def test_parallel_block(self):
        program = parse(
            'PARALLEL {\n'
            '  LOAD "a.txt" AS a\n'
            '  LOAD "b.txt" AS b\n'
            '}\n'
        )
        stmt = program.statements[0]
        self.assertIsInstance(stmt, ParallelBlock)
        self.assertEqual(len(stmt.statements), 2)

    def test_full_program(self):
        src = (
            'LOAD "document.pdf" AS doc\n'
            'SEARCH "auth" IN doc LIMIT 5 AS hits\n'
            'SUMMARIZE hits LENGTH 200 AS summary\n'
            'GENERATE "report.md" FROM summary TEMPLATE "default" AS report\n'
            'EMAIL "report.md" TO "alice@example.com"\n'
        )
        program = parse(src)
        self.assertEqual(len(program.statements), 5)
        self.assertEqual(program.statements[0].__class__.__name__, "LoadStatement")
        self.assertEqual(program.statements[4].__class__.__name__, "EmailStatement")

    def test_invalid_keyword_raises(self):
        with self.assertRaises(ParseError):
            parse("UNKNOWN foo")


if __name__ == "__main__":
    unittest.main()