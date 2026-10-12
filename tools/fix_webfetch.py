import io

P = "internal/api/webfetch/webfetch.go"
lines = io.open(P, encoding="utf-8", newline="").read().split("\n")
out = []
for l in lines:
    st = l.lstrip()
    if st.startswith("# "):
        indent = l[: len(l) - len(st)]
        out.append(indent + "// " + st[2:])
    else:
        out.append(l)
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out))
print("comments fixed")
