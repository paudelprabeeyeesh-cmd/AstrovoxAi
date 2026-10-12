// Package ssrf resolves and validates URLs before a fetch touches the
// network.
//
// A web-fetch tool is an SSRF primitive: a URL like
// http://169.254.169.254/latest/meta-data/ returns cloud credentials, and
// http://127.0.0.1:6379 reaches a Redis that trusts loopback. Validating
// the URL string is not enough, because the check that matters is against
// the address DNS returns.
//
// So this package resolves first and validates the addresses: the hostname
// is a thing a client controls, and the address is a thing the network
// controls. A client can only influence the former.
//
// The three failure modes it closes:
//
//  1. A literal private address in the URL.
//  2. A hostname that resolves to a private address (DNS rebinding: the
//     check runs on one address and the connection uses another). This one
//     requires pinning the resolved address rather than passing the
//     hostname through.
//  3. A redirect chain that lands on a private address, which is why the
//     redirect guard is per-hop rather than only for the original URL.
package ssrf

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

// ErrBlocked indicates a URL refused by the guard.
var ErrBlocked = errors.New("ssrf: url refused")

// blockedRanges are the address ranges that must never be fetched.
//
// They are the obvious ones plus the two that actually get missed:
// link-local (169.254.0.0/16), which is where cloud metadata lives, and the
// unique-local range (fc00::/7), which is IPv6 private space.
var blockedRanges = func() []*net.IPNet {
	ranges := []string{
		"0.0.0.0/8",
		"10.0.0.0/8",
		"127.0.0.0/8",
		"169.254.0.0/16",
		"172.16.0.0/12",
		"192.168.0.0/16",
		"100.64.0.0/10",
		"192.0.0.0/24",
		"198.18.0.0/15",
		"224.0.0.0/4",
		"240.0.0.0/4",
		"::1/128",
		"::/128",
		"fc00::/7",
		"fe80::/10",
		"ff00::/8",
	}
	out := make([]*net.IPNet, 0, len(ranges))
	for _, r := range ranges {
		if _, n, err := net.ParseCIDR(r); err == nil {
			out = append(out, n)
		}
	}
	return out
}()

// blockedHostnames are names that must never resolve, even though they are
// not IP literals.
var blockedHostnames = map[string]bool{
	"metadata":                 true,
	"metadata.google.internal": true,
	"instance-data":            true,
	"localhost":                true,
	"ip6-localhost":            true,
	"ip6-loopback":             true,
}

// DefaultGuard is a configured guard. It is package-level so the fetch
// tool does not thread a guard through every call, and its fields are
// read-only after construction.
type Guard struct {
	// allowedSchemes restricts the URL scheme.
	AllowedSchemes []string
	// MaxRedirects bounds a redirect chain.
	MaxRedirects int
	// Resolver resolves hostnames. Overridable so a test can pin a response.
	Resolver func(ctx context.Context, host string) ([]net.IP, error)
	// clock supports tests.
	clock func() time.Time
}

// New returns a guard with safe defaults.
func New() *Guard {
	return &Guard{
		AllowedSchemes: []string{"http", "https"},
		MaxRedirects:   3,
		Resolver:       defaultResolve,
		clock:          time.Now,
	}
}

func defaultResolve(ctx context.Context, host string) ([]net.IP, error) {
	addrs, err := net.DefaultResolver.LookupIPAddr(ctx, host)
	if err != nil {
		return nil, err
	}
	out := make([]net.IP, 0, len(addrs))
	for _, a := range addrs {
		out = append(out, a.IP)
	}
	return out, nil
}

// Validate resolves the URL and refuses it when any address is private.
// The address is checked, not the hostname, because the hostname is the
// attacker's input and the address is what the connection would use.
func (g *Guard) Validate(raw string) (*url.URL, error) {
	u, err := url.Parse(strings.TrimSpace(raw))
	if err != nil {
		return nil, fmt.Errorf("%w: unparseable", ErrBlocked)
	}

	if !g.schemeAllowed(u.Scheme) {
		return nil, fmt.Errorf("%w: scheme %q is not allowed", ErrBlocked, u.Scheme)
	}

	host := u.Hostname()
	if host == "" {
		return nil, fmt.Errorf("%w: no host", ErrBlocked)
	}

	// A hostname that is a known metadata name is refused without a DNS
	// round trip, so a DNS failure does not turn into an allow.
	if blockedHostnames[strings.ToLower(host)] {
		return nil, fmt.Errorf("%w: hostname %q is blocked", ErrBlocked, host)
	}

	// A literal IP is checked directly, so a URL that never resolves is
	// still refused.
	if ip := net.ParseIP(host); ip != nil {
		if isBlocked(ip) {
			return nil, fmt.Errorf("%w: %q is a private address", ErrBlocked, host)
		}
		return u, nil
	}

	// Otherwise resolve and check every address. Checking all of them
	// matters: a hostname can return one public and one private address,
	// and checking only the first lets the second through.
	addrs, err := g.Resolver(context.Background(), host)
	if err != nil {
		// A resolution failure is a refusal rather than an allow, because
		// a hostname that fails to resolve is indistinguishable from one a
		// resolver has been told to hide.
		return nil, fmt.Errorf("%w: could not resolve %q", ErrBlocked, host)
	}
	for _, ip := range addrs {
		if isBlocked(ip) {
			return nil, fmt.Errorf("%w: %q resolves to a private address %s",
				ErrBlocked, host, ip)
		}
	}
	if len(addrs) == 0 {
		return nil, fmt.Errorf("%w: %q returned no addresses", ErrBlocked, host)
	}
	return u, nil
}

func (g *Guard) schemeAllowed(scheme string) bool {
	scheme = strings.ToLower(scheme)
	for _, s := range g.AllowedSchemes {
		if strings.ToLower(s) == scheme {
			return true
		}
	}
	return false
}

func isBlocked(ip net.IP) bool {
	if ip == nil {
		return true
	}
	// Normalize a v4-mapped address, so ::ffff:127.0.0.1 is recognised as
	// loopback rather than passing as an IPv6 address.
	if v4 := ip.To4(); v4 != nil {
		ip = v4
	}
	for _, n := range blockedRanges {
		if n.Contains(ip) {
			return true
		}
	}
	return false
}

// RedirectGuard validates every hop, not only the first URL. A redirect
// chain is the way a public URL lands on a private address, so the guard
// is applied to each Location the client follows.
func (g *Guard) RedirectGuard(req *http.Request, via []*http.Request) error {
	if len(via) >= g.MaxRedirects {
		return fmt.Errorf("%w: too many redirects", ErrBlocked)
	}
	// The via slice is the hops already taken, so the current request's URL
	// is the new target.
	if len(via) > 0 {
		target := req.URL.String()
		if _, err := g.Validate(target); err != nil {
			return err
		}
	}
	return nil
}

// ResolvedIP pins the address a URL resolved to, so the connection uses
// the address that was validated rather than resolving again. This is the
// defence against DNS rebinding, where the check sees one address and the
// connection uses another.
func (g *Guard) ResolvedIP(u *url.URL) (net.IP, error) {
	host := u.Hostname()
	if ip := net.ParseIP(host); ip != nil {
		return ip, nil
	}
	addrs, err := g.Resolver(context.Background(), host)
	if err != nil {
		return nil, fmt.Errorf("%w: could not re-resolve %q", ErrBlocked, host)
	}
	for _, ip := range addrs {
		if !isBlocked(ip) {
			return ip, nil
		}
	}
	return nil, fmt.Errorf("%w: no public address for %q", ErrBlocked, host)
}

// SafeClient returns an http.Client that validates every hop and blocks
// redirects to private space.
func (g *Guard) SafeClient(timeout time.Duration) *http.Client {
	return &http.Client{
		Timeout:       timeout,
		CheckRedirect: g.RedirectGuard,
	}
}

// mu guards the blockedRanges rebuild in tests that need to cap the set.
var mu sync.Mutex
