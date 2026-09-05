from app.executor.dsl import parse
from app.executor.compiler import compile_program

program = parse('LOAD "doc.pdf" AS doc\nSEARCH "auth" IN doc LIMIT 5 AS hits\nSUMMARIZE hits LENGTH 200 AS summary\n')
print("Statements:", len(program.statements))
for s in program.statements:
    print(" ", type(s).__name__, s)

try:
    graph = compile_program(program)
    print("Steps:", len(graph.steps))
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
