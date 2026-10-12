import io

P = "internal/api/mail/mail.go"
s = io.open(P, encoding="utf-8", newline="").read()

# Go requires parentheses around an implicitly concatenated string that
# spans lines when it is the format argument. The literal newline inside the
# format string makes this one of the cases that trip the parser.
pairs = [
    (
        '\t\t"Use this code: %s\\n\\nIt expires in 24 hours. "\n\t\t\t"If you did not request it, ignore this email.", token)',
        '\t\t\t("Use this code: %s\\n\\nIt expires in 24 hours. "\n\t\t\t "If you did not request it, ignore this email."), token)',
    ),
    (
        '\t\t"Use this code: %s\\n\\nIt expires in 1 hour. "\n\t\t\t"If you did not request it, ignore this email.", token)',
        '\t\t\t("Use this code: %s\\n\\nIt expires in 1 hour. "\n\t\t\t "If you did not request it, ignore this email."), token)',
    ),
    (
        '\t\t"Use this code: %s\\n\\nIt expires in 15 minutes. "\n\t\t\t"If you did not request it, ignore this email.", token)',
        '\t\t\t("Use this code: %s\\n\\nIt expires in 15 minutes. "\n\t\t\t "If you did not request it, ignore this email."), token)',
    ),
]

fixed = 0
for old, new in pairs:
    if old in s:
        s = s.replace(old, new)
        fixed += 1

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("fixed", fixed, "format strings")
