package kernel

import "sync"

// Cache stores recently used kernel dispatch results.
type Cache struct {
	entries map[string]*Entry
	order   []string
	mu      sync.RWMutex
	maxSize int
}

// NewCache creates a new cache.
func NewCache(maxSize int) *Cache {
	return &Cache{
		entries: make(map[string]*Entry),
		maxSize: maxSize,
	}
}

// Get retrieves a cached entry.
func (c *Cache) Get(key string) *Entry {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.entries[key]
}

// Put stores an entry.
func (c *Cache) Put(key string, entry *Entry) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if _, exists := c.entries[key]; !exists {
		c.order = append(c.order, key)
	}
	c.entries[key] = entry
	if len(c.order) > c.maxSize {
		oldest := c.order[0]
		c.order = c.order[1:]
		delete(c.entries, oldest)
	}
}

// Clear empties the cache.
func (c *Cache) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.entries = make(map[string]*Entry)
	c.order = nil
}

// Size returns the number of cached entries.
func (c *Cache) Size() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.entries)
}
