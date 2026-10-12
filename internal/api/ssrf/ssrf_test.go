package ssrf

import (
	"context"
	"errors"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

// pinnedResolver returns a fixed set of addresses, so a test can drive the
// guard without DNS.
func pinnedResolver(addrs ...net.IP) func(ctx context.Context, host string) ([]net.IP, error) {
	return func(_ context.Context, _ string) ([]net.IP, error) {
		return addrs, nil
	}
}

func TestALiteralPrivateAddressIsRefused(t *testing.T) {
	g := New()
	for _, raw := range []string{
		"http://127.0.0.1/",
		"http://localhost:8080/",
		"http://10.0.0.1/x",
		"http://192.168.1.1/",
		"http://172.16.0.5/",
		"http://[::1]/",
	} {
		if _, err := g.Validate(raw); !errors.Is(err, ErrBlocked) {
			t.Errorf("Validate(%q) = %v, want a refusal", raw, err)
		}
	}
}

func TestCloudMetadataIsRefused(t *testing.T) {
	// The link-local metadata address is the single most valuable SSRF
	// target: it returns credentials.
	g := New()
	for _, raw := range []string{
		"http://169.254.169.254/latest/meta-data/",
		"http://metadata.google.internal/computeMetadata/v1/",
		"http://metadata/",
		"http://instance-data/",
	} {
		if _, err := g.Validate(raw); !errors.Is(err, ErrBlocked) {
			t.Errorf("Validate(%q) = %v, want a refusal", raw, err)
		}
	}
}

func TestAPublicLiteralAddressIsAllowed(t *testing.T) {
	g := New()
	u, err := g.Validate("https://example.com/a?b=c")
	if err != nil {
		t.Fatalf("a public address was refused: %v", err)
	}
	if u.Host != "example.com" {
		t.Fatalf("host = %q, want example.com", u.Host)
	}
}

func TestAResolvedPrivateAddressIsRefused(t *testing.T) {
	// The hostname is a thing a client controls, so a public-looking name
	// resolving to a private address must be refused on the address.
	g := New()
	g.Resolver = pinnedResolver(net.ParseIP("10.1.2.3"))
	if _, err := g.Validate("http://sneaky.example.com/"); !errors.Is(err, ErrBlocked) {
		t.Fatalf("err = %v, want a refusal for a hostname resolving privately", err)
	}
}

func TestAMixedResolutionIsRefused(t *testing.T) {
	// A hostname returning one public and one private address must be
	// refused: checking only the first lets the second through.
	g := New()
	g.Resolver = pinnedResolver(net.ParseIP("93.184.216.34"), net.ParseIP("127.0.0.1"))
	if _, err := g.Validate("http://split.example.com/"); !errors.Is(err, ErrBlocked) {
		t.Fatalf("err = %v, want a refusal when any address is private", err)
	}
}

func TestAResolutionFailureIsARefusal(t *testing.T) {
	// A hostname that fails to resolve is indistinguishable from one a
	// resolver has been told to hide, so it must not be an allow.
	g := New()
	g.Resolver = func(context.Context, string) ([]net.IP, error) {
		return nil, errors.New("nxdomain")
	}
	if _, err := g.Validate("http://nxdomain.example.com/"); !errors.Is(err, ErrBlocked) {
		t.Fatalf("err = %v, want a refusal on a resolution failure", err)
	}
}

func TestAnEmptyResolutionIsARefusal(t *testing.T) {
	g := New()
	g.Resolver = pinnedResolver()
	if _, err := g.Validate("http://empty.example.com/"); !errors.Is(err, ErrBlocked) {
		t.Fatal("an empty resolution was allowed")
	}
}

func TestNonHttpSchemesAreRefused(t *testing.T) {
	// file:// reads the filesystem, gopher:// reaches other services, and
	// every other scheme is one this platform has not audited.
	g := New()
	for _, raw := range []string{
		"file:///etc/passwd",
		"gopher://127.0.0.1:6379/_INFO",
		"ftp://example.com/",
		"dial://internal:1234",
	} {
		if _, err := g.Validate(raw); !errors.Is(err, ErrBlocked) {
			t.Errorf("Validate(%q) = %v, want a refusal", raw, err)
		}
	}
}

func TestMissingHostIsRefused(t *testing.T) {
	for _, raw := range []string{"http://", "https:///path", "not a url"} {
		if _, err := New().Validate(raw); !errors.Is(err, ErrBlocked) {
			t.Errorf("Validate(%q) = %v, want a refusal", raw, err)
		}
	}
}

func TestIPv4MappedIPv6IsRecognised(t *testing.T) {
	// ::ffff:127.0.0.1 must be seen as loopback rather than as an exotic
	// IPv6 address, which is how a mapped address would slip through.
	if !isBlocked(net.ParseIP("::ffff:127.0.0.1")) {
		t.Error("a mapped loopback address was not blocked")
	}
	if !isBlocked(net.ParseIP("::ffff:169.254.169.254")) {
		t.Error("a mapped link-local address was not blocked")
	}
}

func TestRedirectGuardRefusesTooManyHops(t *testing.T) {
	g := New()
	g.MaxRedirects = 2
	var via []*http.Request

	for i := 6; i > 0; i-- {
		req := httptest.NewRequest("GET", "https://example.com/", nil)
		if err := g.RedirectGuard(req, via); err != nil {
			if !errors.Is(err, ErrBlocked) {
				t.Fatalf("hop %d: %v", i, err)
			}
			return
		}
		via = append(via, req)
	}
	t.Fatal("a redirect chain ran past the cap without being stopped")
}

func TestSafeClientCarriesTheTimeout(t *testing.T) {
	g := New()
	c := g.SafeClient(5 * time.Second)
	if c.Timeout != 5*time.Second {
		t.Fatalf("timeout = %s, want 5s", c.Timeout)
	}
	if c.CheckRedirect == nil {
		t.Fatal("the redirect guard was not installed")
	}
}
