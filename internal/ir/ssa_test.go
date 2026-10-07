package ir

import "testing"

func TestNewFunction(t *testing.T) {
	fn := NewFunction("main")
	if fn.Name != "main" {
		t.Fatalf("expected name main, got %s", fn.Name)
	}
	if len(fn.Blocks) != 0 {
		t.Fatalf("expected 0 blocks")
	}
}

func TestAddBlock(t *testing.T) {
	fn := NewFunction("main")
	blk := &Block{ID: 1, Name: "entry"}
	fn.AddBlock(blk)
	if len(fn.Blocks) != 1 {
		t.Fatalf("expected 1 block")
	}
	if fn.Blocks[1] != blk {
		t.Fatal("expected same block")
	}
}

func TestAddValue(t *testing.T) {
	fn := NewFunction("main")
	v := &Value{ID: 1, Name: "x", Type: "int64"}
	fn.AddValue(v)
	if fn.Values[1] != v {
		t.Fatal("expected same value")
	}
}

func TestBuilderCreateValue(t *testing.T) {
	b := NewBuilder("main")
	v := b.CreateValue("x", "int64", 1)
	if v.Name != "x" || v.Type != "int64" || v.Block != 1 {
		t.Fatal("unexpected value")
	}
	if len(b.fn.Values) != 1 {
		t.Fatalf("expected 1 value")
	}
}

func TestBuilderCreateBlock(t *testing.T) {
	b := NewBuilder("main")
	blk := b.CreateBlock("entry")
	if blk.Name != "entry" {
		t.Fatalf("expected entry, got %s", blk.Name)
	}
	if len(b.fn.Blocks) != 1 {
		t.Fatalf("expected 1 block")
	}
}

func TestBuilderBuild(t *testing.T) {
	b := NewBuilder("main")
	b.CreateBlock("entry")
	b.CreateValue("x", "int64", 1)
	fn := b.Build()
	if fn.Name != "main" {
		t.Fatalf("expected main")
	}
}

func TestPhiNode(t *testing.T) {
	phi := &PhiNode{ID: 1}
	if phi.ID != 1 {
		t.Fatal("unexpected phi id")
	}
}

func TestPhiPair(t *testing.T) {
	pair := PhiPair{Predecessor: 2}
	if pair.Predecessor != 2 {
		t.Fatal("unexpected predecessor")
	}
}

func TestValueStruct(t *testing.T) {
	v := Value{ID: 1, Name: "x", Type: "int64", Block: 1}
	if v.ID != 1 || v.Name != "x" || v.Type != "int64" || v.Block != 1 {
		t.Fatal("unexpected value")
	}
}

func TestBlockStruct(t *testing.T) {
	blk := Block{ID: 1, Name: "entry"}
	if blk.ID != 1 || blk.Name != "entry" {
		t.Fatal("unexpected block")
	}
}
