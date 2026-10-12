import os

root = "internal"
go_pkgs = []
py_pkgs = []
for name in sorted(os.listdir(root)):
    d = os.path.join(root, name)
    if not os.path.isdir(d):
        continue
    files = os.listdir(d)
    go = [f for f in files if f.endswith(".go")]
    py = [f for f in files if f.endswith(".py")]
    if go:
        go_pkgs.append((name, len(go)))
    elif py:
        py_pkgs.append((name, len(py)))

print("Go packages (%d):" % len(go_pkgs))
for n, c in go_pkgs:
    print("   internal/%-20s %3d" % (n, c))
print()
print("Python-only packages (%d):" % len(py_pkgs))
for n, c in py_pkgs:
    print("   internal/%-20s %3d" % (n, c))
