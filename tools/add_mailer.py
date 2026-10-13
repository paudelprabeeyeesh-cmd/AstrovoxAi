import io

P = "cmd/api/mount.go"
s = io.open(P, encoding="utf-8", newline="").read()

if "func defaultMailer()" in s:
    print("already present")
    raise SystemExit(0)

addition = (
    "\n"
    "// defaultMailer returns the configured mailer, or the null one when no\n"
    "// SMTP host is set. A deployment that forgets to configure mail gets a\n"
    "// registration endpoint that fails visibly rather than one that claims an\n"
    "// email was sent when it was not.\n"
    "func defaultMailer() mail.Mailer {\n"
    "\tcfg := mail.Config{\n"
    '\t\tHost:     os.Getenv("SMTP_HOST"),\n'
    '\t\tPort:     intEnv("SMTP_PORT", 587),\n'
    '\t\tUsername: os.Getenv("SMTP_USER"),\n'
    '\t\tPassword: os.Getenv("SMTP_PASSWORD"),\n'
    '\t\tFrom:     os.Getenv("SMTP_FROM"),\n'
    "\t}\n"
    "\tm, err := mail.NewSMTP(cfg)\n"
    "\tif err != nil {\n"
    "\t\treturn mail.NullMailer{}\n"
    "\t}\n"
    "\treturn m\n"
    "}\n"
    "\n"
    "func intEnv(name string, def int) int {\n"
    '\tv := os.Getenv(name)\n'
    '\tif v == "" {\n'
    "\t\treturn def\n"
    "\t}\n"
    "\tn := 0\n"
    "\tfor _, r := range v {\n"
    "\t\tif r < '0' || r > '9' {\n"
    "\t\t\treturn def\n"
    "\t\t}\n"
    "\t\tn = n*10 + int(r-'0')\n"
    "\t}\n"
    "\treturn n\n"
    "}\n"
)

s = s.rstrip() + "\n" + addition
if '"os"' not in s:
    s = s.replace('import (\n\t"net/http"', 'import (\n\t"net/http"\n\t"os"', 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("defaultMailer added")
