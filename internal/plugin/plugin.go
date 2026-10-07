package plugin

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Manifest describes a plugin package.
type Manifest struct {
	Name        string            `json:"name"`
	Version     string            `json:"version"`
	Entry       string            `json:"entry"`
	Permissions []string          `json:"permissions,omitempty"`
	API         string            `json:"api_version,omitempty"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

// Plugin is the base interface for all plugins.
type Plugin interface {
	// Name returns the plugin name.
	Name() string
	// Version returns the plugin version.
	Version() string
	// Initialize sets up the plugin.
	Initialize(ctx *Context) error
	// Shutdown cleans up resources.
	Shutdown() error
}

// Context provides services to plugins.
type Context struct {
	events EventBus
	perms  PermissionChecker
	store  PluginStore
}

// EventBus allows plugins to communicate via events.
type EventBus interface {
	Publish(topic string, payload interface{})
	Subscribe(topic string, handler func(payload interface{})) Unsubscribe
}

// Unsubscribe removes a subscription.
type Unsubscribe func()

// PermissionChecker validates plugin permissions.
type PermissionChecker interface {
	Allowed(plugin string, perm string) bool
}

// PluginStore persists plugin data.
type PluginStore interface {
	Get(key string) ([]byte, error)
	Set(key string, value []byte) error
}

// Registry manages installed plugins.
type Registry struct {
	plugins map[string]Plugin
	manifests map[string]*Manifest
	mu      sync.RWMutex
}

// NewRegistry creates a new plugin registry.
func NewRegistry() *Registry {
	return &Registry{
		plugins:  make(map[string]Plugin),
		manifests: make(map[string]*Manifest),
	}
}

// Register adds a plugin to the registry.
func (r *Registry) Register(p Plugin, m *Manifest) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, exists := r.plugins[p.Name()]; exists {
		return fmt.Errorf("plugin %s already registered", p.Name())
	}
	r.plugins[p.Name()] = p
	r.manifests[p.Name()] = m
	return nil
}

// Get returns a plugin by name.
func (r *Registry) Get(name string) (Plugin, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	p, ok := r.plugins[name]
	return p, ok
}

// Manifest returns the manifest for a plugin.
func (r *Registry) Manifest(name string) (*Manifest, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	m, ok := r.manifests[name]
	return m, ok
}

// List returns all registered plugin names.
func (r *Registry) List() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	names := make([]string, 0, len(r.plugins))
	for name := range r.plugins {
		names = append(names, name)
	}
	return names
}

// Loader loads plugins from disk or remote sources.
type Loader struct {
	registry *Registry
	store    PluginStore
	http     *http.Client
}

// NewLoader creates a new plugin loader.
func NewLoader(registry *Registry, store PluginStore) *Loader {
	return &Loader{
		registry: registry,
		store:    store,
		http:     &http.Client{Timeout: 30 * time.Second},
	}
}

// LoadFromDir loads plugins from a directory.
func (l *Loader) LoadFromDir(dir string) error {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		pluginDir := filepath.Join(dir, entry.Name())
		manifestPath := filepath.Join(pluginDir, "manifest.json")
		data, err := os.ReadFile(manifestPath)
		if err != nil {
			continue
		}
		var m Manifest
		if err := json.Unmarshal(data, &m); err != nil {
			continue
		}
		// For now, just register manifest; actual loading is backend-specific.
		l.registry.manifests[m.Name] = &m
	}
	return nil
}

// Download fetches a plugin archive from a URL.
func (l *Loader) Download(url string) ([]byte, error) {
	resp, err := l.http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("download failed: %s", resp.Status)
	}
	return io.ReadAll(resp.Body)
}

// Verify checks a plugin archive hash.
func (l *Loader) Verify(data []byte, expectedHash string) bool {
	hash := sha256.Sum256(data)
	return fmt.Sprintf("%x", hash) == expectedHash
}

// Installer installs a plugin from bytes.
type Installer struct {
	registry *Registry
	store    PluginStore
	baseDir  string
}

// NewInstaller creates a new plugin installer.
func NewInstaller(registry *Registry, store PluginStore, baseDir string) *Installer {
	return &Installer{
		registry: registry,
		store:    store,
		baseDir:  baseDir,
	}
}

// Install writes plugin data to disk and registers it.
func (i *Installer) Install(name string, data []byte, m *Manifest) error {
	pluginDir := filepath.Join(i.baseDir, name)
	if err := os.MkdirAll(pluginDir, 0755); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(pluginDir, "manifest.json"), []byte(mustMarshal(m)), 0644); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(pluginDir, "plugin.zip"), data, 0644); err != nil {
		return err
	}
	if err := i.store.Set("plugin_"+name, data); err != nil {
		return err
	}
	i.registry.manifests[name] = m
	return nil
}

func mustMarshal(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}

// PermissionCheckerImpl validates permissions.
type PermissionCheckerImpl struct {
	allowed map[string]map[string]bool
	mu      sync.RWMutex
}

// NewPermissionChecker creates a new permission checker.
func NewPermissionChecker() *PermissionCheckerImpl {
	return &PermissionCheckerImpl{allowed: make(map[string]map[string]bool)}
}

// Allow grants a permission to a plugin.
func (p *PermissionCheckerImpl) Allow(plugin, perm string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.allowed[plugin] == nil {
		p.allowed[plugin] = make(map[string]bool)
	}
	p.allowed[plugin][perm] = true
}

// Allowed checks if a plugin has a permission.
func (p *PermissionCheckerImpl) Allowed(plugin, perm string) bool {
	p.mu.RLock()
	defer p.mu.RUnlock()
	if perms, ok := p.allowed[plugin]; ok {
		return perms[perm]
	}
	return false
}

// MarketplaceClient interacts with a plugin marketplace.
type MarketplaceClient struct {
	baseURL string
	client  *http.Client
}

// NewMarketplaceClient creates a new marketplace client.
func NewMarketplaceClient(baseURL string) *MarketplaceClient {
	return &MarketplaceClient{
		baseURL: baseURL,
		client:  &http.Client{Timeout: 30 * time.Second},
	}
}

// Search searches for plugins.
func (m *MarketplaceClient) Search(query string) ([]*Manifest, error) {
	url := fmt.Sprintf("%s/search?q=%s", m.baseURL, query)
	resp, err := m.client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("search failed: %s", resp.Status)
	}
	var results []*Manifest
	if err := json.NewDecoder(resp.Body).Decode(&results); err != nil {
		return nil, err
	}
	return results, nil
}

// Download downloads a plugin package.
func (m *MarketplaceClient) Download(name, version string) ([]byte, error) {
	url := fmt.Sprintf("%s/download/%s/%s", m.baseURL, name, version)
	resp, err := m.client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("download failed: %s", resp.Status)
	}
	return io.ReadAll(resp.Body)
}
