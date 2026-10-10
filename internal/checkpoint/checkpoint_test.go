package checkpoint

import (
	"context"
	"testing"
	"time"
)

func TestMemoryStoreSaveLoad(t *testing.T) {
	s := NewMemoryStore(4)
	if err := s.Save(&Snapshot{Version: 1, Shards: map[string]*Shard{"a": {Name: "a", Data: []float64{1}}}}); err != nil {
		t.Fatal(err)
	}
	got, err := s.Load(1)
	if err != nil {
		t.Fatal(err)
	}
	if got.Version != 1 || got.ParamCount() != 1 {
		t.Error("snapshot contents")
	}
	if _, err := s.Load(2); err == nil {
		t.Error("expected missing version error")
	}
}

func TestMemoryStoreLatest(t *testing.T) {
	s := NewMemoryStore(4)
	s.Save(&Snapshot{Version: 1})
	s.Save(&Snapshot{Version: 2})
	latest, err := s.Latest()
	if err != nil {
		t.Fatal(err)
	}
	if latest.Version != 2 {
		t.Errorf("expected 2, got %d", latest.Version)
	}
}

func TestMemoryStoreEmpty(t *testing.T) {
	if _, err := NewMemoryStore(4).Latest(); err == nil {
		t.Error("expected no snapshot error")
	}
}

func TestMemoryStoreRetention(t *testing.T) {
	s := NewMemoryStore(2)
	s.Save(&Snapshot{Version: 1})
	s.Save(&Snapshot{Version: 2})
	s.Save(&Snapshot{Version: 3})
	if s.Count() != 2 {
		t.Errorf("expected 2 retained, got %d", s.Count())
	}
	if vs := s.Versions(); len(vs) != 2 || vs[0] != 2 {
		t.Errorf("unexpected versions %v", vs)
	}
}

func TestCoordinatorSave(t *testing.T) {
	store := NewMemoryStore(4)
	c := NewCoordinator(store, 2)
	if err := c.PutShard(&Shard{Name: "w", Data: []float64{1, 2, 3}}); err != nil {
		t.Fatal(err)
	}
	if c.ShardCount() != 1 {
		t.Error("shard count")
	}
	snap, err := c.Save("commit-1")
	if err != nil {
		t.Fatal(err)
	}
	if snap.Version != 1 || snap.Commit != "commit-1" {
		t.Errorf("snapshot: %+v", snap)
	}
	if snap.ParamCount() != 3 {
		t.Errorf("expected 3 params, got %d", snap.ParamCount())
	}
	if c.Stats().Saved.Load() != 1 {
		t.Error("saved stat")
	}
}

func TestCoordinatorSaveAsync(t *testing.T) {
	store := NewMemoryStore(4)
	c := NewCoordinator(store, 1)
	c.PutShard(&Shard{Name: "w", Data: []float64{1}})
	if err := <-c.SaveAsync("c"); err != nil {
		t.Fatal(err)
	}
	if c.Stats().AsyncSaves.Load() != 1 {
		t.Error("async stat")
	}
}

func TestCoordinatorSync(t *testing.T) {
	store := NewMemoryStore(4)
	c := NewCoordinator(store, 1)
	c.PutShard(&Shard{Name: "w", Data: []float64{7}})
	c.Save("c1")

	var applied []float64
	snap, err := c.Sync(context.Background(), func(sh *Shard) error {
		applied = append(applied, sh.Data...)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if snap.Version != 1 || len(applied) != 1 || applied[0] != 7 {
		t.Errorf("sync: %v", applied)
	}
	if c.Stats().Synced.Load() != 1 {
		t.Error("synced stat")
	}
}

func TestCoordinatorVerify(t *testing.T) {
	store := NewMemoryStore(4)
	c := NewCoordinator(store, 1)
	c.PutShard(&Shard{Name: "w", Data: []float64{1.5, 2.5}})
	c.Save("c")
	if !c.Verify() {
		t.Error("expected valid hashes")
	}
}

func TestCoordinatorDiff(t *testing.T) {
	store := NewMemoryStore(4)
	c := NewCoordinator(store, 2)
	c.PutShard(&Shard{Name: "a", Data: []float64{1}})
	c.Save("v1")
	c.PutShard(&Shard{Name: "b", Data: []float64{2}})
	c.Save("v2")
	changed, err := c.Diff(1)
	if err != nil {
		t.Fatal(err)
	}
	// Shard "b" is new relative to the first snapshot's local state.
	found := false
	for _, n := range changed {
		if n == "b" {
			found = true
		}
	}
	if !found {
		t.Errorf("expected b in diff, got %v", changed)
	}
}

func TestGetShard(t *testing.T) {
	store := NewMemoryStore(4)
	c := NewCoordinator(store, 1)
	c.PutShard(&Shard{Name: "w", Data: []float64{3}})
	c.Save("c")
	sh, err := c.GetShard("w")
	if err != nil {
		t.Fatal(err)
	}
	if sh.Data[0] != 3 {
		t.Error("shard data")
	}
	if _, err := c.GetShard("nope"); err == nil {
		t.Error("expected missing shard error")
	}
}

func TestPutShardInvalid(t *testing.T) {
	c := NewCoordinator(NewMemoryStore(1), 1)
	if c.PutShard(nil) == nil {
		t.Error("expected nil error")
	}
	if c.PutShard(&Shard{}) == nil {
		t.Error("expected empty name error")
	}
}

func TestSnapshotShardNames(t *testing.T) {
	s := &Snapshot{Shards: map[string]*Shard{"a": {}, "b": {}}}
	names := s.ShardNames()
	if len(names) != 2 {
		t.Errorf("got %v", names)
	}
}

func TestHashFloatsDistinct(t *testing.T) {
	if hashFloats([]float64{1, 2}) == hashFloats([]float64{2, 1}) {
		t.Error("order must matter")
	}
	if hashFloats([]float64{1, 2}) != hashFloats([]float64{1, 2}) {
		t.Error("hash must be deterministic")
	}
}

func TestSyncCancelled(t *testing.T) {
	store := NewMemoryStore(4)
	c := NewCoordinator(store, 1)
	c.PutShard(&Shard{Name: "w", Data: []float64{1}})
	c.Save("c")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := c.Sync(ctx, func(sh *Shard) error { return nil }); err == nil {
		t.Error("expected cancellation error")
	}
}

var _ = time.Now
