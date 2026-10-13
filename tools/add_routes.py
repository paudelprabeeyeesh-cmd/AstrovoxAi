import io

P = "cmd/api/mount.go"
s = io.open(P, encoding="utf-8", newline="").read()

if "/auth/verify" in s:
    print("already registered")
    raise SystemExit(0)

old = '\trouter.Handle(http.MethodPost, "/auth/logout", h.logout)\n'
new = (
    '\trouter.Handle(http.MethodPost, "/auth/logout", h.logout)\n'
    '\t// Email-token flows. None of them return a token: the token is only\n'
    '\t// ever in the email, and a response that carried one would be an\n'
    '\t// account-takeover primitive.\n'
    '\trouter.Handle(http.MethodPost, "/auth/verify", h.verifyEmail)\n'
    '\trouter.Handle(http.MethodPost, "/auth/reset-request", h.requestReset)\n'
    '\trouter.Handle(http.MethodPost, "/auth/reset", h.resetPassword)\n'
    '\trouter.Handle(http.MethodPost, "/auth/magic-link", h.magicLink)\n'
    '\trouter.Handle(http.MethodPost, "/auth/magic-login", h.magicLogin)\n'
)

if old not in s:
    print("anchor not found")
    raise SystemExit(1)
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("email routes registered")
