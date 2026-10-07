package plugin_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/astrovox/astrovox/internal/plugin"
)

type stubPlugin struct {
	name string
}

func (s *stubPlugin) Name() string                         { return s.name }
func (s *stubPlugin) Version() string                      { return "1.0.0" }
func (s *stubPlugin) Initialize(ctx *plugin.Context) error { return nil }
func (s *stubPlugin) Shutdown() error                      { return nil }

type memStore struct {
	data map[string][]byte
}

func (m *memStore) Get(key string) ([]byte, error) { return m.data[key], nil }
func (m *memStore) Set(key string, value []byte) error {
	m.data[key] = value
	return nil
}

func TestPluginRegistryRegister(t *testing.T) {
	r := plugin.NewRegistry()
	p := &stubPlugin{name: "test"}
	m := &plugin.Manifest{Name: "test", Version: "1.0.0", Entry: "test"}
	if err := r.Register(p, m); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if _, ok := r.Get("test"); !ok {
		t.Fatal("expected plugin registered")
	}
}

func TestPluginRegistryDuplicate(t *testing.T) {
	r := plugin.NewRegistry()
	p := &stubPlugin{name: "test"}
	m := &plugin.Manifest{Name: "test", Version: "1.0.0", Entry: "test"}
	_ = r.Register(p, m)
	if err := r.Register(p, m); err == nil {
		t.Fatal("expected error for duplicate registration")
	}
}

func TestPluginRegistryList(t *testing.T) {
	r := plugin.NewRegistry()
	_ = r.Register(&stubPlugin{name: "a"}, &plugin.Manifest{Name: "a", Version: "1.0.0", Entry: "a"})
	_ = r.Register(&stubPlugin{name: "b"}, &plugin.Manifest{Name: "b", Version: "1.0.0", Entry: "b"})
	if list := r.List(); len(list) != 2 {
		t.Fatalf("expected 2 plugins, got %d", len(list))
	}
}

func TestPluginRegistryManifest(t *testing.T) {
	r := plugin.NewRegistry()
	p := &stubPlugin{name: "test"}
	m := &plugin.Manifest{Name: "test", Version: "1.0.0", Entry: "test"}
	if err := r.Register(p, m); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	got, ok := r.Manifest("test")
	if !ok || got.Name != "test" {
		t.Fatal("expected manifest for plugin")
	}
}

func TestPluginLoaderVerify(t *testing.T) {
	l := plugin.NewLoader(plugin.NewRegistry(), &memStore{data: make(map[string][]byte)})
	data := []byte("hello")
	hash := "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
	if !l.Verify(data, hash) {
		t.Fatal("expected verification to pass")
	}
}

func TestPluginLoaderLoadFromDir(t *testing.T) {
	dir := t.TempDir()
	pluginDir := filepath.Join(dir, "test_plugin")
	if err := os.MkdirAll(pluginDir, 0755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	manifest := `{"name":"test_plugin","version":"1.0.0","entry":"plugin.zip"}`
	if err := os.WriteFile(filepath.Join(pluginDir, "manifest.json"), []byte(manifest), 0644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	r := plugin.NewRegistry()
	l := plugin.NewLoader(r, &memStore{data: make(map[string][]byte)})
	if err := l.LoadFromDir(dir); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if _, ok := r.Manifest("test_plugin"); !ok {
		t.Fatal("expected manifest loaded from dir")
	}
}

func TestPluginInstallerInstall(t *testing.T) {
	baseDir := t.TempDir()
	r := plugin.NewRegistry()
	store := &memStore{data: make(map[string][]byte)}
	i := plugin.NewInstaller(r, store, baseDir)
	m := &plugin.Manifest{Name: "test_plugin", Version: "1.0.0", Entry: "plugin.zip"}
	if err := i.Install("test_plugin", []byte("data"), m); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if _, ok := r.Manifest("test_plugin"); !ok {
		t.Fatal("expected plugin installed")
	}
	if _, err := os.ReadFile(filepath.Join(baseDir, "test_plugin", "manifest.json")); err != nil {
		t.Fatalf("expected manifest on disk: %v", err)
	}
}

func TestPluginPermissionChecker(t *testing.T) {
	p := plugin.NewPermissionChecker()
	p.Allow("test_plugin", "read")
	if !p.Allowed("test_plugin", "read") {
		t.Fatal("expected permission allowed")
	}
	if p.Allowed("test_plugin", "write") {
		t.Fatal("expected permission denied")
	}
}

func TestPluginContext(t *testing.T) {
	ctx := &plugin.Context{}
	if ctx == nil {
		t.Fatal("expected context")
	}
}

func TestPluginManifestStruct(t *testing.T) {
	m := plugin.Manifest{Name: "test", Version: "1.0.0"}
	if m.Name != "test" || m.Version != "1.0.0" {
		t.Fatal("unexpected manifest")
	}
}
