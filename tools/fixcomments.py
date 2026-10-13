import io
import sys
import re

# Convert stray hash comments to Go comments in the given files.
targets = sys.argv[1:]
for P in targets:
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

# Ensure the mail import is present in mount.go.
P = "cmd/api/mount.go"
s = io.open(P, encoding="utf-8", newline="").read()
if "internal/api/mail" not in s:
    s = s.replace(
        '\t"github.com/astrovox/astrovox/internal/api/logging"\n',
        '\t"github.com/astrovox/astrovox/internal/api/logging"\n'
        '\t"github.com/astrovox/astrovox/internal/api/mail"\n',
        1,
    )
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("mail import added")
print("hash comments converted")
