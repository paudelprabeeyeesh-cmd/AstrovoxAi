package plugin_test

import (
	"testing"

	"github.com/astrovox/astrovox/internal/plugin"
)

func TestPluginManagerCreate(t *testing.T) {
	m := plugin.NewManager("test_plugins")
	if m == nil {
		t.Fatal("expected manager")
	}
}

func TestPluginRegistry(t *testing.T) {
	r := plugin.NewRegistry()
	if r == nil {
		t.Fatal("expected registry")
	}
}

func TestPluginEventBus(t *testing.T) {
	bus := plugin.NewEventBus()
	if bus == nil {
		t.Fatal("expected event bus")
	}
}

func TestPluginContext(t *testing.T) {
	ctx := plugin.NewContext()
	if ctx == nil {
		t.Fatal("expected context")
	}
}

func TestPluginLoader(t *testing.T) {
	loader := plugin.NewLoader()
	if loader == nil {
		t.Fatal("expected loader")
	}
}

func TestPluginInstaller(t *testing.T) {
	installer := plugin.NewInstaller()
	if installer == nil {
		t.Fatal("expected installer")
	}
}

func TestPluginManagerRegister(t *testing.T) {
	m := plugin.NewManager("test_plugins")
	p := &plugin.Plugin{Name: "test"}
	m.Register(p)
	if !m.Has("test") {
		t.Fatal("expected plugin registered")
	}
}

func TestPluginManagerUnregister(t *testing.T) {
	m := plugin.NewManager("test_plugins")
	p := &plugin.Plugin{Name: "test"}
	m.Register(p)
	m.Unregister("test")
	if m.Has("test") {
		t.Fatal("expected plugin unregistered")
	}
}

func TestPluginRegistryAdd(t *testing.T) {
	r := plugin.NewRegistry()
	p := &plugin.Plugin{Name: "test"}
	r.Add(p)
	if !r.Has("test") {
		t.Fatal("expected plugin in registry")
	}
}

func TestPluginRegistryRemove(t *testing.T) {
	r := plugin.NewRegistry()
	p := &plugin.Plugin{Name: "test"}
	r.Add(p)
	r.Remove("test")
	if r.Has("test") {
		t.Fatal("expected plugin removed")
	}
}

func TestPluginEventBusSubscribe(t *testing.T) {
	bus := plugin.NewEventBus()
	received := false
	bus.Subscribe("test", func(e plugin.Event) { received = true })
	bus.Publish(plugin.Event{Type: "test"})
	if !received {
		t.Fatal("expected event received")
	}
}

func TestPluginEventBusUnsubscribe(t *testing.T) {
	bus := plugin.NewEventBus()
	received := false
	bus.Subscribe("test", func(e plugin.Event) { received = true })
	bus.Unsubscribe("test", func(e plugin.Event) { received = true })
	bus.Publish(plugin.Event{Type: "test"})
	if received {
		t.Fatal("expected event not received after unsubscribe")
	}
}

func TestPluginContextSet(t *testing.T) {
	ctx := plugin.NewContext()
	ctx.Set("key", "value")
	if ctx.Get("key") != "value" {
		t.Fatal("expected value")
	}
}

func TestPluginContextGetMissing(t *testing.T) {
	ctx := plugin.NewContext()
	if ctx.Get("missing") != nil {
		t.Fatal("expected nil")
	}
}

func TestPluginLoaderLoad(t *testing.T) {
	loader := plugin.NewLoader()
	p, err := loader.Load("test_plugin")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if p == nil {
		t.Fatal("expected plugin")
	}
}

func TestPluginInstallerInstall(t *testing.T) {
	installer := plugin.NewInstaller()
	err := installer.Install("test_plugin")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestPluginInstallerUninstall(t *testing.T) {
	installer := plugin.NewInstaller()
	installer.Install("test_plugin")
	err := installer.Uninstall("test_plugin")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestPluginStruct(t *testing.T) {
	p := plugin.Plugin{Name: "test", Version: "1.0.0"}
	if p.Name != "test" || p.Version != "1.0.0" {
		t.Fatal("unexpected plugin")
	}
}

func TestPluginEventStruct(t *testing.T) {
	e := plugin.Event{Type: "test", Plugin: "p"}
	if e.Type != "test" || e.Plugin != "p" {
		t.Fatal("unexpected event")
	}
}

func TestPluginManagerList(t *testing.T) {
	m := plugin.NewManager("test_plugins")
	m.Register(&plugin.Plugin{Name: "a"})
	m.Register(&plugin.Plugin{Name: "b"})
	plugins := m.List()
	if len(plugins) != 2 {
		t.Fatalf("expected 2 plugins, got %d", len(plugins))
	}
}
