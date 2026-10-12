import io

P = "cmd/api/stock_tools.go"
s = io.open(P, encoding="utf-8", newline="").read()

addition = (
    "\n"
    "\t// web.fetch is a guard composition rather than a plain HTTP client: the\n"
    "\t// SSRF guard runs before the transport, so an agent cannot be pointed\n"
    "\t// at an internal address by a URL in its prompt.\n"
    "\t_ = r.Register(tools.Schema{\n"
    "\t\tName:        \"web.fetch\",\n"
    '\t\tDescription: "Fetch a public web page and return its text.",\n'
    "\t\tRisk:        tools.RiskRead,\n"
    "\t\tTimeout:     15 * time.Second,\n"
    "\t\tParams: map[string]tools.Param{\n"
    '\t\t\t"url": {Kind: tools.KindString, Required: true, MinLength: 8, MaxLength: 2048},\n'
    "\t\t},\n"
    "\t}, webfetch.NewTool(webfetch.NewSafeFetcher()))\n"
)

if "web.fetch" in s:
    print("already registered")
else:
    s = s.rstrip() + "\n" + addition
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("web.fetch registered")
