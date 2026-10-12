import io

P = "cmd/api/mount.go"
s = io.open(P, encoding="utf-8", newline="").read()

# The mount* funcs pass "METHOD /path" as the first argument; the router API
# takes method and pattern separately. Split them, and uppercase the method
# to the http.MethodX constant form.
for verb in ("GET", "POST", "PATCH", "PUT", "DELETE"):
    src = 'router.Handle("' + verb + ' '
    dst = "router.Handle(http.Method" + verb.capitalize() + ', "'
    s = s.replace(src, dst)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("split method and path arguments")
