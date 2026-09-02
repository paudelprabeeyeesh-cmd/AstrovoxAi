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
        self.assertEqual(len(graph.steps), 3)
        self.assertEqual(graph.bindings.get("hits"), graph.steps[1].id)
        self.assertEqual(graph.bindings.get("summary"), graph.steps[2].id)
        # Dependencies flow through.
        self.assertIn(graph.steps[0].id, graph.steps[1].inputs)
        self.assertIn(graph.steps[1].id, graph.steps[2].inputs)

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
        # First group should contain both LOAD steps, second the ASK.
        self.assertEqual(len(graph.parallel_groups[0]), 2)
        self.assertEqual(len(graph.parallel_groups[1]), 1)

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
        )
        graph = compile_program(program)
        # 'unused' has no consumer; should be removed.
        outputs = {s.output for s in graph.steps if s.output}
        self.assertNotIn("unused", outputs)

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


if __name__ == "__main__":
    unittest.main()