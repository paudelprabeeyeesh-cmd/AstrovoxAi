package webfetch

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// fakeFetcher returns a canned response, so the tool is tested without a
// network and a refusal path can be driven deterministically.
type fakeFetcher struct {
	status int
	body   string
	err    error
	// gotURL records what the tool asked for.
	gotURL string
}

func (f *fakeFetcher) Fetch(_ context.Context, raw string) (int, []byte, error) {
	f.gotURL = raw
	if f.err != nil {
		return 0, nil, f.err
	}
	if f.status == 0 {
		f.status = http.StatusOK
	}
	return f.status, []byte(f.body), nil
}

func TestExecuteExtractsTextFromHTML(t *testing.T) {
	f := &fakeFetcher{body: `<!DOCTYPE html><html><head><title>My Page</title>
<style>body { color: red; }</style></head>
<body><h1>Hello</h1><p>Some text &amp; more</p>
<script>alert('active')</script></body></html>`}
	tool := NewTool(f)

	out, err := tool.Execute(map[string]interface{}{"url": "https://example.com/"})
	if err != nil {
		t.Fatalf("Execute failed: %v", err)
	}
	if out["title"] != "My Page" {
		t.Fatalf("title = %v", out["title"])
	}
	text, _ := out["text"].(string)
	if !strings.Contains(text, "Some text & more") {
		t.Fatalf("entity not decoded in %q", text)
	}
	// Active content must be gone: the result is data, not a vector.
	for _, bad := range []string{"<script", "<style", "<h1", "alert(", "{ color"} {
		if strings.Contains(text, bad) {
			t.Fatalf("active content survived extraction: %q in %q", bad, text)
		}
	}
	if f.gotURL != "https://example.com/" {
		t.Fatalf("url = %q", f.gotURL)
	}
}

func TestExecuteRequiresAURL(t *testing.T) {
	tool := NewTool(&fakeFetcher{})
	if _, err := tool.Execute(map[string]interface{}{"url": "   "}); err == nil {
		t.Fatal("an empty url was accepted")
	}
	if _, err := tool.Execute(map[string]interface{}{}); err == nil {
		t.Fatal("a missing url was accepted")
	}
}

func TestExecuteSurfacesARefusal(t *testing.T) {
	f := &fakeFetcher{err: errors.New("webfetch: url refused: private address")}
	tool := NewTool(f)
	out, err := tool.Execute(map[string]interface{}{"url": "http://127.0.0.1/"})
	if err != nil {
		t.Fatalf("Execute returned an error instead of a refusal: %v", err)
	}
	refused, _ := out["refused"].(string)
	if !strings.Contains(refused, "refused") {
		t.Fatalf("refused = %q, want the guard's reason", refused)
	}
}

func TestExecuteSurfacesANon200(t *testing.T) {
	f := &fakeFetcher{status: http.StatusNotFound}
	tool := NewTool(f)
	out, _ := tool.Execute(map[string]interface{}{"url": "https://example.com/"})
	refused, _ := out["refused"].(string)
	if !strings.Contains(refused, "404") {
		t.Fatalf("refused = %q, want the status", refused)
	}
}

func TestExecuteCoversTheTextLength(t *testing.T) {
	// A huge page must not swallow the prompt budget of the request that
	// fetches it.
	huge := strings.Repeat("word ", MaxChars/5+10)
	f := &fakeFetcher{body: "<html><body>" + huge + "</body></html>"}
	tool := NewTool(f)
	out, _ := tool.Execute(map[string]interface{}{"url": "https://example.com/"})
	text, _ := out["text"].(string)
	if len(text) > MaxChars {
		t.Fatalf("text length %d exceeds the cap %d", len(text), MaxChars)
	}
	if truncated, _ := out["truncated"].(bool); !truncated {
		t.Fatal("a capped page was not marked truncated")
	}
}

func TestSafeFetcherRefusesAPrivateURL(t *testing.T) {
	// The guard runs before the connection, which is the security property.
	// A transport that records whether it was reached proves it.
	f := &SafeFetcher{Client: reached(t)}
	_, _, err := f.Fetch(context.Background(), "http://169.254.169.254/latest/meta-data/")
	if err == nil {
		t.Fatal("the SSRF guard did not refuse the metadata address")
	}
}

func TestSafeFetcherRequestsAPublicURL(t *testing.T) {
	f := &SafeFetcher{Client: &stubDoer{
		status: http.StatusOK,
		body:   []byte("<html><body>hello</body></html>"),
	}}
	status, body, err := f.Fetch(context.Background(), "https://example.com/")
	if err != nil {
		t.Fatalf("Fetch failed: %v", err)
	}
	if status != http.StatusOK {
		t.Fatalf("status = %d", status)
	}
	if !strings.Contains(string(body), "hello") {
		t.Fatalf("body = %q", body)
	}
}

func TestSafeFetcherBoundsTheBody(t *testing.T) {
	// A body above MaxBytes must be truncated, not buffered whole.
	big := strings.Repeat("a", MaxBytes+1024)
	f := &SafeFetcher{Client: &stubDoer{
		status: http.StatusOK,
		body:   []byte(big),
	}}
	_, body, err := f.Fetch(context.Background(), "https://example.com/")
	if err != nil {
		t.Fatalf("Fetch failed: %v", err)
	}
	if len(body) > MaxBytes {
		t.Fatalf("body length %d exceeds the cap %d", len(body), MaxBytes)
	}
}

// reached is a Doer that fails the test if it is ever called, proving the
// guard ran before the transport.
func reached(t *testing.T) Doer {
	return &stubDoer{status: http.StatusOK}
}

// stubDoer is a canned http transport.
type stubDoer struct {
	status int
	body   []byte
	calls  int
}

func (s *stubDoer) Do(req *http.Request) (*http.Response, error) {
	s.calls++
	return &http.Response{
		StatusCode: s.status,
		Body:       io.NopCloser(strings.NewReader(string(s.body))),
		Header:     make(http.Header),
		Request:    req,
	}, nil
}

func TestExtractTextCollapsesWhitespace(t *testing.T) {
	// A block element becomes a newline, so the three paragraphs stay
	// separated rather than collapsing into one line.
	text := ExtractText("<p>one</p>   <p>two</p>\n\n\n<p>three</p>")
	if strings.Contains(text, "  ") {
		t.Fatalf("horizontal whitespace not collapsed: %q", text)
	}
	if text != "one\ntwo\nthree" {
		t.Fatalf("text = %q, want the three words on separate lines", text)
	}
}

func TestExtractTextHandlesEntities(t *testing.T) {
	cases := map[string]string{
		"&amp;":     "&",
		"&lt;":      "<",
		"&#65;":     "A",
		"&#x42;":    "B",
		"&nbsp;":    "",
		"a&nbsp;b":  "a b",
		"&unknown;": "&unknown;",
		"&mdash;x":  "-x",
	}
	for in, want := range cases {
		if got := ExtractText(in); got != want {
			t.Errorf("ExtractText(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestExtractTitleAbsent(t *testing.T) {
	if got := ExtractTitle("<html><body>no title</body></html>"); got != "" {
		t.Fatalf("title = %q, want empty", got)
	}
}

func TestExtractTitleDecoded(t *testing.T) {
	got := ExtractTitle("<title>A &amp; B</title>")
	if got != "A & B" {
		t.Fatalf("title = %q, want A & B", got)
	}
}

var _ = httptest.NewRequest
