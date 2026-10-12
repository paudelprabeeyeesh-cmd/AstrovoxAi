import io
import sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
lines = s.split("\n")
out = []
for l in lines:
    st = l.lstrip()
    if st.startswith("# "):
        indent = l[: len(l) - len(st)]
        out.append(indent + "// " + st[2:])
    elif st == "#":
        indent = l[: len(l) - len(st)]
        out.append(indent + "//")
    elif st.startswith("#"):
        indent = l[: len(l) - len(st)]
        out.append(indent + "// " + st[1:].lstrip())
    else:
        out.append(l)
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out))
left = sum(1 for l in out if l.lstrip().startswith("#"))
print("hash comments converted;", left, "remaining in", P)
