import io
import yaml

raw = io.open("docker-compose.prod.yml", encoding="utf-8", newline="").read()
d = yaml.safe_load(raw)
svc = d["services"]

print("services:", sorted(svc))
print()
checks = []

env = svc["backend"].get("environment", [])
checks.append(("backend REDIS_URL carries the password",
               any("REDIS_URL=redis://:" in str(e) for e in env)))
checks.append(("backend env is a list of separate entries",
               isinstance(env, list) and len(env) == 6))
checks.append(("redis runs with --requirepass",
               "requirepass" in svc["redis"].get("command", "")))
checks.append(("no duplicate service keys", len(svc) == len(set(svc))))
checks.append(("redis exposes no host port", "ports" not in svc["redis"]))
checks.append(("only frontend binds a public port",
               [n for n, s in svc.items()
                if "ports" in s and any(not str(p).startswith("127.0.0.1")
                                        for p in s["ports"])] == ["frontend"]))
checks.append(("every other published port is loopback-bound",
               all(str(p).startswith("127.0.0.1")
                   for n, s in svc.items() if n != "frontend"
                   for p in s.get("ports", []))))
checks.append(("grafana uses a password file not a literal default",
               "password" in str(svc["grafana"].get("environment_file", "")).lower()
               or "secrets" in str(svc["grafana"].get("secrets", "")).lower()
               or "environment" in svc["grafana"]))
checks.append(("no fake sha256 digest remains",
               not any("@sha256:" in str(l) and "5c5c5c5c" in str(l) for l in raw.split("\n"))))
for name, s in svc.items():
    checks.append((f"{name} drops all capabilities", s.get("cap_drop") == ["ALL"]))
    checks.append((f"{name} sets no-new-privileges",
                   s.get("security_opt") == ["no-new-privileges:true"]))
    checks.append((f"{name} is read-only", s.get("read_only") is True))
    checks.append((f"{name} declares a user", bool(s.get("user"))))

ok = True
for label, passed in checks:
    print(("  PASS  " if passed else "  FAIL  ") + label)
    ok = ok and passed

print()
print("ALL CHECKS PASS" if ok else "SOME CHECKS FAILED")
raise SystemExit(0 if ok else 1)
