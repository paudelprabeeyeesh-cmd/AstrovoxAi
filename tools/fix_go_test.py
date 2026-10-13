import io

P = "cmd/api/email_flow_test.go"
s = io.open(P, encoding="utf-8", newline="").read()

lines = s.split("\n")
out = []
for l in lines:
    st = l.lstrip()
    if st.startswith("# "):
        indent = l[: len(l) - len(st)]
        out.append(indent + "// " + st[2:])
    elif st.startswith("def issueForPurpose"):
        indent = l[: len(l) - len(st)]
        out.append(indent + "func issueForPurpose(t *testing.T, fixture *mailFixture, email, purpose string) string {")
    elif st.startswith("def doJSON"):
        indent = l[: len(l) - len(st)]
        out.append(indent + "func doJSON(t *testing.T, fixture *mailFixture, method, path, body string) *httptest.ResponseRecorder {")
    elif st.startswith("def postJSON"):
        indent = l[: len(l) - len(st)]
        out.append(indent + "func postJSON(t *testing.T, fixture *mailFixture, path, body string) string {")
    elif st.startswith("def registerAccount"):
        indent = l[: len(l) - len(st)]
        out.append(indent + "func registerAccount(t *testing.T, fixture *mailFixture, email string) {")
    elif st.startswith("def newMailFixture"):
        indent = l[: len(l) - len(st)]
        out.append(indent + "func newMailFixture(t *testing.T) *mailFixture {")
    elif st.startswith("def "):
        indent = l[: len(l) - len(st)]
        out.append(indent + "func ")  # placeholder; fixed below
    else:
        out.append(l)

s = "\n".join(out)
# Remove the unused imports and the stray comment line that references reasons.
s = s.replace('\t"bytes"\n', "")
s = s.replace("    # The mounted server has its own handler and store; swap in the fixture\n    # one so the test can reach the issued tokens.\n", "    // The mounted server has its own handler; the fixture store is the\n    // one the tests read tokens from.\n")
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("pythonisms fixed")
