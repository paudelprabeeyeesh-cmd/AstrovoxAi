from app.executor.dsl import parse
from app.executor.compiler import Compiler, compile_program, PlanCache, StepKind
from app.executor.compiler import ExecutionGraph

original_compile = Compiler.compile

def debug_compile(self, program):
    self.steps = []
    self.bindings = {}
    self.optimizations_applied = []
    for stmt in program.statements:
        step = self._lower_statement(stmt)
        print(f"Lowered {type(stmt).__name__}: {step}")
        if step is not None:
            self.steps.append(step)
            if step.outputs:
                self.bindings[step.outputs[0]] = step.id
        print(f"After append: steps={len(self.steps)}, bindings={self.bindings}")
        self._optimize()
        print(f"After optimize: steps={len(self.steps)}, opts={self.optimizations_applied}")
    total_cost = sum(step.estimated_cost for step in self.steps)
    graph = ExecutionGraph(
        id=self._cache_key(program),
        name=program.__class__.__name__,
        steps=list(self.steps),
        parallel_groups=self._detect_parallel_groups(),
        cache_key=self._cache_key(program),
        bindings=dict(self.bindings),
        total_estimated_cost=total_cost,
        optimizations_applied=list(self.optimizations_applied),
    )
    print(f"Final graph: steps={len(graph.steps)}")
    return graph

Compiler.compile = debug_compile

program = parse('LOAD "doc.pdf" AS doc\nSEARCH "auth" IN doc LIMIT 5 AS hits\nSUMMARIZE hits LENGTH 200 AS summary\n')
cache = PlanCache()
compiler = Compiler(cache=cache)
graph = compiler.compile(program)
print("Steps:", len(graph.steps))
for s in graph.steps:
    print(" ", s.id, s.kind, s.inputs, s.outputs)
print("Bindings:", graph.bindings)
print("Optimizations:", graph.optimizations_applied)
print("Total cost:", graph.total_estimated_cost)
print("Cache hits:", cache.hits, "misses:", cache.misses)
