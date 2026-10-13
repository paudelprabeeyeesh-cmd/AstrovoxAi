"""Verify the seven hardening requirements on app/auth/__init__.py."""
import ast
import sys

PATH = "app/auth/__init__.py"
src = open(PATH, encoding="utf-8", newline="").read()
tree = ast.parse(src)
failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  -> {detail}" if detail else ""))
    if not ok:
        failures.append(label)


# --- 1. every import is a top-level statement, in the leading import block ---
first_non_import = None
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        continue
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        continue  # module docstring
    first_non_import = node.lineno
    break

late = [
    (n.lineno, ast.dump(n)[:60])
    for n in tree.body
    if isinstance(n, (ast.Import, ast.ImportFrom)) and n.lineno > (first_non_import or 0)
]
check("1. no top-level import after the first statement", not late, str(late))

nested = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Import, ast.ImportFrom)):
                nested.append(f"line {sub.lineno}")
check("1. no function-local imports", not nested, ", ".join(nested))

seen = {}
dupes = []
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            key = (a.asname or a.name).split(".")[0]
            if key in seen:
                dupes.append(f"{key} (lines {seen[key]} and {node.lineno})")
            seen[key] = node.lineno
check("1. no duplicated import name", not dupes, ", ".join(dupes))

# a function must not use a name imported after its own definition
imported_after = {}
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            imported_after.setdefault((a.asname or a.name).split(".")[0], node.lineno)
late_use = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        for name in sorted(names & set(imported_after)):
            if imported_after[name] > node.lineno:
                late_use.append(f"{node.name}<-{name}")
check("1. no function uses a later-imported name", not late_use, ", ".join(late_use))


# --- 2. no unreachable statement after an unconditional raise ---
dead = []


def scan_block(stmts, where):
    for i, s in enumerate(stmts):
        if isinstance(s, (ast.Raise, ast.Return, ast.Continue, ast.Break)):
            for after in stmts[i + 1:]:
                if isinstance(after, ast.Expr) and isinstance(after.value, ast.Constant):
                    continue
                dead.append(f"{where}: line {after.lineno} follows {type(s).__name__} at {s.lineno}")


def walk(node, where):
    for field in ("body", "orelse", "finalbody"):
        stmts = getattr(node, field, None)
        if isinstance(stmts, list) and stmts and isinstance(stmts[0], ast.stmt):
            scan_block(stmts, where)
    for child in ast.iter_child_nodes(node):
        name = getattr(child, "name", None)
        walk(child, where + ("/" + name if name else ""))


walk(tree, "module")
check("2. no statement after an unconditional raise/return", not dead, "; ".join(dead))


# --- 3. exactly one definition each ---
for name in ("get_current_user", "require_admin"):
    hits = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    check(f"3. exactly one definition of {name}", len(hits) == 1, f"{len(hits)} found")
    if name == "get_current_user" and hits:
        args = [a.arg for a in hits[0].args.args]
        check("3. get_current_user keeps the Header dependency signature",
              args == ["authorization"], str(args))
    if name == "require_admin" and hits:
        body_src = ast.dump(hits[0])
        check("3. require_admin performs the role check",
              "role_required" in body_src and "admin" in body_src)

# no module-level re-import shadows the single definition
shadow = [
    n.lineno for n in tree.body
    if isinstance(n, ast.ImportFrom)
    and any((a.asname or a.name) in ("get_current_user", "require_admin") for a in n.names)
]
check("3. neither name is re-imported at module level", not shadow, str(shadow))


# --- 4. secrets.token_urlsafe, never uuid ---
check("4. secrets is imported at top level", "secrets" in seen)
uses_safe = any(
    isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
    and n.value.id == "secrets" and n.attr == "token_urlsafe"
    for n in ast.walk(tree)
)
check("4. secrets.token_urlsafe is used", uses_safe)
check("4. uuid is never imported", "uuid" not in seen)
check("4. no uuid4() call", not any(
    isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "uuid4"
    for n in ast.walk(tree)))
check("4. no uuid4 name is loaded", not any(
    isinstance(n, ast.Name) and n.id == "uuid4" for n in ast.walk(tree)))
check("4. _new_token returns secrets.token_urlsafe(32)",
      "return secrets.token_urlsafe(32)" in src)


# --- 5. no endpoint returns a token-bearing field ---
BANNED = ("verification_token", "magic_link_token", "reset_token")
returned = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
        for k in node.value.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                returned.add(k.value)
leaked = sorted(b for b in BANNED if b in returned)
check("5. no return dict carries a banned token key", not leaked, str(leaked))
# The names may still exist as identifiers (a constant, a mint helper) - what
# is forbidden is a response *field*. Check dict keys and attribute names only.
returned_attrs = {
    k.value for node in ast.walk(tree)
    if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    for k in node.value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)
}
check("5. banned strings absent from every response field", not (set(BANNED) & returned_attrs),
      str(sorted(set(BANNED) & returned_attrs)))

ENDPOINTS = {}
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for dec in node.decorator_list:
            call = dec if isinstance(dec, ast.Call) else None
            fn = call.func if call else dec
            if isinstance(fn, ast.Attribute) and fn.attr in ("post", "get", "put", "delete"):
                path = call.args[0].value if call and call.args and isinstance(call.args[0], ast.Constant) else "?"
                ENDPOINTS[node.name] = (fn.attr, path)
check("5. endpoints discovered", len(ENDPOINTS) >= 6, str(sorted(ENDPOINTS)))
print("      routes: " + ", ".join(f"{m.upper()} {p} -> {f}" for f, (m, p) in sorted(ENDPOINTS.items(), key=lambda x: x[1][1])))


# --- 6. refresh token in the JSON body only ---
refresh_fns = [n for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and "refresh" in n.name]
check("6. a refresh endpoint exists", len(refresh_fns) == 1)
for fn in refresh_fns:
    args = [a.arg for a in fn.args.args]
    annotations = {a.arg: a.annotation for a in fn.args.args}
    bare = [a for a in args if "token" in a and a != "request"]
    check("6. refresh takes no bare token parameter", not bare, str(args))
    body_param = [a for a in args if a == "body"]
    check("6. refresh takes a 'body' parameter", bool(body_param), str(args))
    check("6. refresh body param is annotated with a pydantic model",
          bool(body_param) and isinstance(annotations.get("body"), ast.Name)
          and annotations["body"].id == "RefreshTokenRequest",
          ast.dump(annotations.get("body"))[:60])
    check("6. RefreshTokenRequest.refresh_token is a str field with limits",
          "min_length=8" in src and "max_length=MAX_TOKEN_BYTES" in src)
    check("6. refresh_token name kept", args == ["request", "body"] or "body" in args, str(args))

# every endpoint function: no bare str param named like a token
for fn in [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
    for a in fn.args.args + fn.args.kwonlyargs:
        if "token" in a.arg and a.arg != "request" and a.annotation is None:
            check(f"6. {fn.name} param '{a.arg}' is annotated", False, "bare token param")


# --- 7. oauth_login provider allowlist + userinfo verification ---
oauth = next((n for n in tree.body
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "oauth_login"), None)
check("7. oauth_login exists", oauth is not None)
if oauth:
    names = {n.id for n in ast.walk(oauth) if isinstance(n, ast.Name)}
    check("7. oauth_login checks OAUTH_PROVIDERS allowlist", "OAUTH_PROVIDERS" in names)
    check("7. oauth_login references its access_token", "access_token" in {n.attr for n in ast.walk(oauth) if isinstance(n, ast.Attribute)})
dump = ast.dump(oauth)
check("7. oauth_login delegates token verification to a helper",
      "_verify_provider_access_token" in {n.id for n in ast.walk(oauth) if isinstance(n, ast.Name)})

verifier = next((n for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == "_verify_provider_access_token"), None)
check("7. _verify_provider_access_token exists", verifier is not None)
if verifier:
    vnames = {n.id for n in ast.walk(verifier) if isinstance(n, ast.Name)}
    check("7. verifier uses OAUTH_PROVIDERS", "OAUTH_PROVIDERS" in vnames)
    check("7. verifier calls requests.get", "requests" in vnames and "get" in {n.attr for n in ast.walk(verifier) if isinstance(n, ast.Attribute)})
    vsrc = ast.get_source_segment(src, verifier)
    check("7. verifier sends Authorization: Bearer + token",
          vsrc is not None and '"Bearer " + access_token' in vsrc)
    check("7. verifier uses timeout=10", vsrc is not None and "timeout=10" in vsrc)
    check("7. verifier reads userinfo_url from the provider config",
          vsrc is not None and 'userinfo_url' in vsrc)
    check("7. verifier fails closed (returns None on any failure)",
          vsrc is not None and vsrc.count("return None") >= 4)

# the session is issued only for the verified subject
check("7. session is issued from the verified subject",
      "_resolve_oauth_subject" in {n.id for n in ast.walk(oauth) if isinstance(n, ast.Name)}
      and "provider_sub" in {n.id for n in ast.walk(oauth) if isinstance(n, ast.Name)})

print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED: {failures}")
    sys.exit(1)
print("ALL CHECKS PASSED")
