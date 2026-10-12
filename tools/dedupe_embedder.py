import io
import re

P = "internal/retrieval/retrieval_test.go"
s = io.open(P, encoding="utf-8", newline="").read()

# The package now provides hashEmbedder and NewHashEmbeddable, so the test's
# duplicate copy must go: it shadowed the real one and made the two
# implementations diverge silently.
start = s.find("// hashEmbedder is a deterministic embedder.")
if start == -1:
    start = s.find("type hashEmbedder struct {")
end = s.find("func testIndex(")
if start == -1 or end == -1:
    print("markers not found")
    raise SystemExit(1)

s = s[:start] + s[end:]

# Use the package constructor at the call sites.
s = s.replace("hashEmbedder{dim: 64}", "NewHashEmbeddable(64)")
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("test embedder replaced with the package one")
