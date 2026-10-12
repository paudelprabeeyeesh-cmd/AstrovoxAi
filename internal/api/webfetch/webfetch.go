// Package webfetch implements the web fetch tool: guard the URL, fetch,
// strip active content, and extract text with a size cap.
//
// The tool is the composition of the guards that each exist for a reason:
// the SSRF guard validates before the connection is made, the response
// size is bounded while it streams so a large body cannot exhaust memory,
// active content is stripped so the result is data rather than a vector,
// and the extracted text is capped so a huge page cannot swallow a prompt
// budget.
//
// The order is the security property: guard, then connect. A tool that
// connects and then checks is a tool that has already been SSRF'd.
package webfetch

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/astrovox/astrovox/internal/api/ssrf"
)

// MaxBytes bounds the response body. A 5 MB page is either an attack or a
// mistake, and either way it must not be buffered whole.
const MaxBytes = 5 << 20

// MaxChars bounds the extracted text, so a page cannot swallow the prompt
// budget of the request that fetches it.
const MaxChars = 50_000

// DefaultTimeout bounds the whole fetch.
const DefaultTimeout = 10 * time.Second

// NewSafeFetcher returns the fetcher the stock tools use: the SSRF guard
# with its default timeout, and the real transport.
//
# The constructor exists so a caller has no reason to assemble the guard
# and the timeout by hand, which is how a timeout would silently default
# to zero and hang.
func NewSafeFetcher() *SafeFetcher {
	return &SafeFetcher{
		Guard:   ssrf.New(),
		Timeout: DefaultTimeout,
	}
}

// Fetcher performs the HTTP request. It is a seam so the tool is testable
// without a network and a deployment can plug a transport that pins the
# resolved address.
type Fetcher interface {
	Fetch(ctx context.Context, raw string) (status int, body []byte, err error)
}

// Doer is the http.Client surface the fetcher needs.
type Doer interface {
	Do(req *http.Request) (*http.Response, error)
}

// SafeFetcher is the default Fetcher. It uses the SSRF guard's client, so
// every redirect hop is validated as well as the original URL.
type SafeFetcher struct {
	Guard   *ssrf.Guard
	Timeout time.Duration
	Client  Doer
}

func (f *SafeFetcher) client() Doer {
	if f.Client != nil {
		return f.Client
	}
	guard := f.Guard
	if guard == nil {
		guard = ssrf.New()
	}
	timeout := f.Timeout
	if timeout <= 0 {
		timeout = DefaultTimeout
	}
	return guard.SafeClient(timeout)
}

// Fetch validates, requests, and returns the status and the capped body.
func (f *SafeFetcher) Fetch(ctx context.Context, raw string) (int, []byte, error) {
	guard := f.Guard
	if guard == nil {
		guard = ssrf.New()
	}
	url, err := guard.Validate(raw)
	if err != nil {
		return 0, nil, fmt.Errorf("webfetch: url refused: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url.String(), nil)
	if err != nil {
		return 0, nil, err
	}
	req.Header.Set("User-Agent", "astrovox-webfetch/1.0")
	resp, err := f.client().Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer func() { _ = resp.Body.Close() }()
	// A bounded read: a larger body is truncated rather than buffered, so
	// one page cannot exhaust memory.
	body, err := io.ReadAll(io.LimitReader(resp.Body, MaxBytes))
	if err != nil {
		return resp.StatusCode, nil, err
	}
	return resp.StatusCode, body, nil
}

// Result is the tool's output.
type Result struct {
	URL       string `json:"url"`
	Status    int    `json:"status,omitempty"`
	Title     string `json:"title,omitempty"`
	Text      string `json:"text"`
	Truncated bool   `json:"truncated,omitempty"`
	Refused   string `json:"refused,omitempty"`
}

// Tool adapts the fetcher to the tool registry's interface, so an agent
// calls it through the same guard path as every other tool.
type Tool struct {
	fetcher Fetcher
}

// NewTool returns a fetch tool wrapping the fetcher.
func NewTool(f Fetcher) *Tool {
	return &Tool{fetcher: f}
}

// Name implements the tool registry's naming contract.
func (t *Tool) Name() string { return "web.fetch" }

// Execute runs one fetch. The URL is validated by the fetcher, which is
// where the guard belongs: the registry validates arguments against a
// schema, and a schema cannot express "not a private address".
func (t *Tool) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	url, _ := args["url"].(string)
	if strings.TrimSpace(url) == "" {
		return nil, fmt.Errorf("webfetch: url is required")
	}
	status, body, err := t.fetcher.Fetch(context.Background(), url)
	if err != nil {
		return map[string]interface{}{"url": url, "refused": err.Error()}, nil
	}
	if status != http.StatusOK {
		return map[string]interface{}{
			"url":     url,
			"status":  status,
			"refused": "unexpected status " + strconv.Itoa(status),
		}, nil
	}
	html := string(body)
	text := ExtractText(html)
	truncated := len(text) > MaxChars
	if truncated {
		text = text[:MaxChars]
	}
	return map[string]interface{}{
		"url":       url,
		"status":    status,
		"title":     ExtractTitle(html),
		"text":      text,
		"truncated": truncated,
	}, nil
}

// --- Extraction ------------------------------------------------------------

var (
	// A backreference would compress these into one pattern, but Go's
	// regexp does not support \1 in the way PCRE does, and a silent no-op
	// here would leave script content in the extracted text. Each pair is
	// written out instead, so the compiler proves the pattern is what it
	// looks like.
	scriptRe   = regexp.MustCompile(`(?is)<script\b[^>]*>.*?</script\s*>`)
	styleRe    = regexp.MustCompile(`(?is)<style\b[^>]*>.*?</style\s*>`)
	noscriptRe = regexp.MustCompile(`(?is)<noscript\b[^>]*>.*?</noscript\s*>`)
	templateRe = regexp.MustCompile(`(?is)<template\b[^>]*>.*?</template\s*>`)
	commentRe  = regexp.MustCompile(`(?s)<!--.*?-->`)
	tagRe      = regexp.MustCompile(`(?s)<[^>]+>`)
	titleRe    = regexp.MustCompile(`(?is)<title[^>]*>(.*?)</title>`)
	spaceRe    = regexp.MustCompile(`[ \t]+`)
	lineRe     = regexp.MustCompile(`(?:[ \t]*\n[ \t]*)+`)
	entityRe   = regexp.MustCompile(`&(#x?[0-9a-fA-F]+|[a-zA-Z]+);`)
	// Block elements become a newline, so a paragraph break survives the
	// extraction and a caller can split on it.
	blockRe = regexp.MustCompile(`(?is)</?(p|div|br|li|tr|h[1-6]|table|section|article|blockquote)\b[^>]*>`)
)

// entities covers the common HTML escapes, because a decoded entity is a
// character a caller may search for.
var entities = map[string]string{
	"amp": "&", "lt": "<", "gt": ">", "quot": "\"", "apos": "'",
	"nbsp": " ", "mdash": "-", "ndash": "-", "hellip": "...",
	"copy": "(c)", "reg": "(r)", "trade": "(tm)",
}

// ExtractText removes active content and tags, decodes the common escapes,
// and collapses whitespace, so the result is text a model can read rather
// than markup it must parse.
// ExtractText removes active content and tags, decodes the common escapes,
// and collapses whitespace, so the result is text a model can read rather
// than markup it must parse.
//
// The newline between block elements is preserved rather than collapsed
// into a space, because a rendered paragraph break is meaningful signal for
// a retrieval chunker and a plain space is not.
func ExtractText(html string) string {
	out := commentRe.ReplaceAllString(html, " ")
	// Active content is removed before the general tag strip, and each
	// element is named explicitly rather than matched by a group.
	out = scriptRe.ReplaceAllString(out, " ")
	out = styleRe.ReplaceAllString(out, " ")
	out = noscriptRe.ReplaceAllString(out, " ")
	out = templateRe.ReplaceAllString(out, " ")
	// A block element becomes a newline, so paragraphs stay separated.
	out = blockRe.ReplaceAllString(out, "\n")
	out = tagRe.ReplaceAllString(out, " ")
	out = decodeEntities(out)
	out = spaceRe.ReplaceAllString(out, " ")
	out = lineRe.ReplaceAllString(out, "\n")
	return strings.Trim(out, " \n\t")
}

func decodeEntities(s string) string {
	return entityRe.ReplaceAllStringFunc(s, func(m string) string {
		key := m[1 : len(m)-1]
		if strings.HasPrefix(key, "#") {
			base := 10
			digits := key[1:]
			if digits != "" && (digits[0] == 'x' || digits[0] == 'X') {
				base, digits = 16, digits[1:]
			}
			if digits != "" {
				if code, err := strconv.ParseInt(digits, base, 32); err == nil {
					return string(rune(code))
				}
			}
		}
		if decoded, ok := entities[strings.ToLower(key)]; ok {
			return decoded
		}
		return m
	})
}

// ExtractTitle returns the page title, empty when there is none.
func ExtractTitle(html string) string {
	m := titleRe.FindStringSubmatch(html)
	if len(m) < 2 {
		return ""
	}
	return strings.TrimSpace(decodeEntities(m[1]))
}
