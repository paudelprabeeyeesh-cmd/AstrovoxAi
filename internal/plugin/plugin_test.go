package plugin

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

type fakePlugin struct {
	name string
}

func (f *fakePlugin) Name() string        { return f.name }
func (f *fakePlugin) Version() string     { return "0.1.0" }
func (f *fakePlugin) Initialize(ctx *Context) error { return nil }
func (f *fakePlugin) Shutdown() error     { return nil }

func TestRegistryRegister(t *testing.T) {
	r := NewRegistry()
	p := &fakePlugin{name: "fake"}
	m := &Manifest{Name: "fake", Version: "0.1.0", Entry: "fake"}
	if err := r.Register(p, m); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if _, ok := r.Get("fake"); !ok {
		t.Fatal("expected plugin to be registered")
	}
}

func TestRegistryDuplicate(t *testing.T) {
	r := NewRegistry()
	p := &fakePlugin{name: "fake"}
	m := &Manifest{Name: "fake", Version: "0.1.0", Entry: "fake"}
	_ = r.Register(p, m)
	if err := r.Register(p, m); err == nil {
		t.Fatal("expected error for duplicate registration")
	}
}

func TestRegistryList(t *testing.T) {
	r := NewRegistry()
	_ = r.Register(&fakePlugin{name: "a"}, &Manifest{Name: "a", Version: "0.1.0", Entry: "a"})
	_ = r.Register(&fakePlugin{name: "b"}, &Manifest{Name: "b", Version: "0.1.0", Entry: "b"})
	list := r.List()
	if len(list) != 2 {
		t.Fatalf("expected 2 plugins, got %d", len(list))
	}
}

func TestPermissionChecker(t *testing.T) {
	p := NewPermissionChecker()
	p.Allow("plugin1", "read")
	if !p.Allowed("plugin1", "read") {
		t.Fatal("expected permission to be allowed")
	}
	if p.Allowed("plugin1", "write") {
		t.Fatal("expected permission to be denied")
	}
}

func TestMarketplaceSearch(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[{"name":"plugin1","version":"1.0.0"}]`))
	}))
	defer server.Close()
	client := NewMarketplaceClient(server.URL)
	results, err := client.Search("query")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(results) != 1 || results[0].Name != "plugin1" {
		t.Fatalf("unexpected search results: %v", results)
	}
}

func TestMarketplaceDownload(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/octet-stream")
		_, _ = w.Write([]byte("plugin-data"))
	}))
	defer server.Close()
	client := NewMarketplaceClient(server.URL)
	data, err := client.Download("plugin1", "1.0.0")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if string(data) != "plugin-data" {
		t.Fatalf("unexpected download data: %s", string(data))
	}
}

func TestLoaderVerify(t *testing.T) {
	l := &Loader{}
	data := []byte("hello")
	hash := "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
	if !l.Verify(data, hash) {
		t.Fatal("expected verification to pass")
	}
}

func TestContextEventBus(t *testing.T) {
	bus := &fakeEventBus{handlers: make(map[string][]func(interface{}))}
	ctx := &Context{events: bus}
	received := false
	bus.handlers["test"] = []func(interface{}){func(_ interface{}) { received = true }}
	ctx.events.Publish("test", nil)
	if !received {
		t.Fatal("expected event to be received")
	}
}

type fakeEventBus struct {
	handlers map[string][]func(interface{})
}

func (f *fakeEventBus) Publish(topic string, payload interface{}) {
	for _, h := range f.handlers[topic] {
		h(payload)
	}
}

func (f *fakeEventBus) Subscribe(topic string, handler func(interface{})) Unsubscribe {
	if f.handlers == nil {
		f.handlers = make(map[string][]func(interface{}))
	}
	f.handlers[topic] = append(f.handlers[topic], handler)
	return func() {}
}
