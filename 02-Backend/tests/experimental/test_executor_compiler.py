"""Tests for the compiler and plan cache."""

from __future__ import annotations

import unittest

from app.executor.compiler import (
    Compiler,
    ExecutionGraph,
    PlanCache,
    Step,
    StepKind,
    StepState,
    compile_program,
)
from app.executor.dsl import parse


class CompilerTest(unittest.TestCase):
    def test_compile_load(self):
        program = parse('LOAD "doc.pdf" AS doc')
        graph = compile_program(program)
        self.assertEqual(len(graph.steps), 1)
        self.assertEqual(graph.steps[0].kind, StepKind.LOAD)
        self.assertEqual(graph.bindings.get("doc"), graph.steps[0].id)

    def test_compile_chain(self):
        program = parse(
            'LOAD "doc.pdf" AS doc\n'
            'SEARCH "auth" IN doc LIMIT 5 AS hits\n'
            'SUMMARIZE hits LENGTH 200 AS summary\n'
        )
        graph = compile_program(program)
        # After fusion, SEARCH+SUMMARIZE become a single step.
        self.assertEqual(len(graph.steps), 2)
        self.assertEqual(graph.bindings.get("hits"), graph.steps[1].id)
        self.assertEqual(graph.bindings.get("summary"), graph.steps[1].id)
        # Dependencies flow through.
        self.assertIn(graph.steps[0].id, graph.steps[1].inputs)

    def test_topological_order(self):
        program = parse(
            'LOAD "a" AS a\n'
            'LOAD "b" AS b\n'
            'ASK "combine a and b" AS result\n'
        )
        graph = compile_program(program)
        order = graph.topological()
        self.assertEqual(len(order), 3)
        self.assertLess(order.index(graph.bindings["a"]), order.index(graph.bindings["result"]))

    def test_parallel_groups(self):
        program = parse(
            'PARALLEL {\n'
            '  LOAD "a" AS a\n'
            '  LOAD "b" AS b\n'
            '}\n'
            'ASK "combine" AS c\n'
        )
        graph = compile_program(program)
        # All three are independent in this program.
        self.assertGreaterEqual(len(graph.parallel_groups), 1)
        self.assertEqual(len(graph.parallel_groups[0]), 3)

    def test_cost_estimation(self):
        program = parse(
            'LOAD "a" AS a\n'
            'ASK "x" AS q\n'
        )
        graph = compile_program(program)
        self.assertGreater(graph.total_estimated_cost, 0)
        costs = {s.kind: s.estimated_cost for s in graph.steps}
        self.assertIn(StepKind.ASK, costs)

    def test_dead_step_elimination(self):
        program = parse(
            'LOAD "a" AS a\n'
            'ASK "x" AS q\n'
            'SUMMARIZE q LENGTH 50 AS unused\n'
            'ASK "final" AS final_result\n'
        )
        graph = compile_program(program)
        # 'unused' has no consumer and is not first or last; should be removed.
        outputs = {s.output for s in graph.steps if s.output}
        self.assertNotIn("unused", outputs)
        # First and last steps should be preserved
        self.assertIn("a", outputs)
        self.assertIn("final_result", outputs)

    def test_fusion(self):
        program = parse(
            'LOAD "doc" AS doc\n'
            'SEARCH "auth" IN doc LIMIT 5 AS hits\n'
            'SUMMARIZE hits LENGTH 100 AS summary\n'
        )
        graph = compile_program(program)
        self.assertIn("execution_fusion", ",".join(graph.metadata.get("optimizations", [])))

    def test_plan_cache(self):
        program = parse('LOAD "x" AS x\n')
        cache = PlanCache()
        compiler = Compiler(cache=cache)
        g1 = compiler.compile(program)
        g2 = compiler.compile(program)
        self.assertEqual(cache.hits, 1)
        self.assertEqual(cache.misses, 1)

    def test_ready_steps(self):
        program = parse(
            'LOAD "a" AS a\n'
            'ASK "q" AS q\n'
        )
        graph = compile_program(program)
        # Mark first step as done.
        graph.steps[0].state = StepState.SUCCEEDED
        ready = graph.ready()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].kind, StepKind.ASK)

    def test_fusion_multiple_chains(self):
        program = parse(
            'LOAD "doc" AS doc\n'
            'SEARCH "auth" IN doc LIMIT 5 AS hits1\n'
            'SUMMARIZE hits1 LENGTH 100 AS summary1\n'
            'SEARCH "auth2" IN doc LIMIT 5 AS hits2\n'
            'SUMMARIZE hits2 LENGTH 100 AS summary2\n'
        )
        graph = compile_program(program)
        self.assertEqual(len(graph.steps), 3)
        self.assertIn("execution_fusion", ",".join(graph.metadata.get("optimizations", [])))

    def test_fusion_skips_non_adjacent(self):
        program = parse(
            'LOAD "doc" AS doc\n'
            'SEARCH "auth" IN doc LIMIT 5 AS hits\n'
            'ASK "break" AS q\n'
            'SUMMARIZE hits LENGTH 100 AS summary\n'
        )
        graph = compile_program(program)
        self.assertEqual(len(graph.steps), 4)

    def test_dead_step_preserves_email_save(self):
        program = parse(
            'LOAD "a" AS a\n'
            'EMAIL "a" TO "x@example.com"\n'
            'SAVE a TO "out.txt"\n'
        )
        graph = compile_program(program)
        kinds = {s.kind for s in graph.steps}
        self.assertIn(StepKind.EMAIL, kinds)
        self.assertIn(StepKind.SAVE, kinds)

    def test_parallel_block_multiple_groups(self):
        program = parse(
            'PARALLEL {\n'
            '  LOAD "a" AS a\n'
            '  LOAD "b" AS b\n'
            '}\n'
            'PARALLEL {\n'
            '  LOAD "c" AS c\n'
            '  LOAD "d" AS d\n'
            '}\n'
            'ASK "combine" AS result\n'
        )
        graph = compile_program(program)
        self.assertEqual(len(graph.steps), 5)
        kinds = {s.kind for s in graph.steps}
        self.assertEqual(kinds, {StepKind.LOAD, StepKind.ASK})

    def test_cache_key_stable(self):
        program = parse('LOAD "x" AS x\n')
        compiler = Compiler()
        g1 = compiler.compile(program)
        g2 = compiler.compile(program)
        self.assertEqual(g1.cache_key, g2.cache_key)

    def test_topological_order_with_dependencies(self):
        program = parse(
            'LOAD "a" AS a\n'
            'SEARCH "x" IN a LIMIT 1 AS hits\n'
            'SUMMARIZE hits LENGTH 10 AS summary\n'
            'ASK "final" AS result\n'
        )
        graph = compile_program(program)
        order = graph.topological()
        self.assertEqual(len(order), len(graph.steps))


if __name__ == "__main__":
    unittest.main()