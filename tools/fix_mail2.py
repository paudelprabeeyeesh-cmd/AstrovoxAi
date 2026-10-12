import io

P = "internal/api/mail/mail.go"
s = io.open(P, encoding="utf-8", newline="").read()

start = s.find("func template(purpose, token string) (string, string) {")
if start == -1:
    raise SystemExit("template func not found")
end = s.find("\n}\n", start)

new_func = '''func template(purpose, token string) (string, string) {
	switch purpose {
	case PurposeVerifyEmail:
		return "Confirm your email address", fmt.Sprintf(
			"Use this code: %s\\n\\nIt expires in 24 hours. If you did not request it, ignore this email.", token)
	case PurposeResetPassword:
		return "Reset your password", fmt.Sprintf(
			"Use this code: %s\\n\\nIt expires in 1 hour. If you did not request it, ignore this email.", token)
	case PurposeMagicLink:
		return "Your sign-in link", fmt.Sprintf(
			"Use this code: %s\\n\\nIt expires in 15 minutes. If you did not request it, ignore this email.", token)
	default:
		return "Your security code", fmt.Sprintf(
			"Use this code: %s\\n\\nIt expires in 1 hour.", token)
	}
}'''

s = s[:start] + new_func + s[end:]
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("template rewritten with single-line format strings")
