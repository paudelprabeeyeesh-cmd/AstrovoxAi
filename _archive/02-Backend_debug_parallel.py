from app.executor.dsl import parse
from app.executor.compiler import compile_program

program = parse('''PARALLEL {
  LOAD "a" AS a
  LOAD "b" AS b
}
PARALLEL {
  LOAD "c" AS c
  LOAD "d" AS d
}
ASK "combine" AS result
''')
graph = compile_program(program)
print("Steps:", len(graph.steps))
for s in graph.steps:
    print(f"  {s.id}: {s.kind} inputs={s.inputs} outputs={s.outputs}")
print("Parallel groups:", graph.parallel_groups)
print("Group count:", len(graph.parallel_groups))
