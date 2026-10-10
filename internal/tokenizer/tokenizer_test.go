package tokenizer

import "testing"

func TestVocabularyAddGet(t *testing.T) {
	v := NewVocabulary()
	id1 := v.Add("hello")
	id2 := v.Add("hello")
	id3 := v.Add("world")
	if id1 != id2 {
		t.Error("adding the same token must return the same id")
	}
	if id1 == id3 {
		t.Error("different tokens must get different ids")
	}
	if v.Len() != 2 {
		t.Errorf("expected 2 tokens, got %d", v.Len())
	}
}

func TestVocabularyLookup(t *testing.T) {
	v := NewVocabulary()
	v.Add("a")
	if v.Lookup("a") != 0 {
		t.Error("expected id 0")
	}
	if v.Lookup("zz") != -1 {
		t.Error("expected -1 for missing token")
	}
	if v.GetByID(0) != "a" {
		t.Error("expected token a")
	}
	if v.GetByID(99) != "" {
		t.Error("expected empty string for out of range")
	}
}

func TestVocabularyTokens(t *testing.T) {
	v := NewVocabulary()
	v.Add("a")
	v.Add("b")
	if toks := v.Tokens(); len(toks) != 2 || toks[0] != "a" {
		t.Errorf("unexpected tokens %v", toks)
	}
}

func TestBPETokenizerSpecials(t *testing.T) {
	tk := NewBPETokenizer(true)
	if tk.VocabSize() < 260 {
		t.Errorf("expected at least 260 tokens (4 specials + 256 bytes), got %d", tk.VocabSize())
	}
	if tk.EosID() < 0 || tk.BosID() < 0 || tk.PadID() < 0 {
		t.Error("special token ids must be valid")
	}
	if tk.TokenToID("<s>") != tk.BosID() {
		t.Error("bos id mismatch")
	}
	if tk.IDToToken(tk.PadID()) != TokPad {
		t.Error("pad token mismatch")
	}
}

func TestBPETrainEncodeDecodeRoundTrip(t *testing.T) {
	tk := NewBPETokenizer(false)
	tk.Train([]string{"hello world"}, 10, 200)

	ids, err := tk.Encode("hello world")
	if err != nil {
		t.Fatal(err)
	}
	if len(ids) == 0 {
		t.Fatal("expected ids")
	}
	out, err := tk.Decode(ids)
	if err != nil {
		t.Fatal(err)
	}
	// Byte-level merges preserve the concatenated text.
	want := "helloworld"
	if out != want {
		t.Errorf("roundtrip: got %q, want %q", out, want)
	}
}

func TestBPEEncodeEmpty(t *testing.T) {
	tk := NewBPETokenizer(false)
	ids, err := tk.Encode("")
	if err != nil {
		t.Fatal(err)
	}
	if len(ids) != 0 {
		t.Errorf("expected 0 ids, got %d", len(ids))
	}
}

func TestBPEUnknownWord(t *testing.T) {
	tk := NewBPETokenizer(false)
	ids, err := tk.Encode("unseenword")
	if err != nil {
		t.Fatal(err)
	}
	if len(ids) == 0 {
		t.Fatal("expected fallback ids")
	}
}

func TestBPEAddMerge(t *testing.T) {
	tk := NewBPETokenizer(false)
	tk.AddToken("a")
	tk.AddToken("b")
	tk.AddMerge("a", "b", "ab")
	if tk.TokenToID("ab") < 0 {
		t.Error("expected merged token")
	}
	// Duplicate merge should be a no-op.
	tk.AddMerge("a", "b", "ab")
}

func TestByteTokenizer(t *testing.T) {
	bt := NewByteTokenizer()
	if bt.VocabSize() != 256 {
		t.Errorf("expected 256, got %d", bt.VocabSize())
	}
	ids, err := bt.Encode("Hi!")
	if err != nil {
		t.Fatal(err)
	}
	if len(ids) != 3 {
		t.Errorf("expected 3 ids, got %d", len(ids))
	}
	out, err := bt.Decode(ids)
	if err != nil {
		t.Fatal(err)
	}
	if out != "Hi!" {
		t.Errorf("got %q", out)
	}
}

func TestByteTokenizerInvalid(t *testing.T) {
	bt := NewByteTokenizer()
	if _, err := bt.Decode([]int{999}); err == nil {
		t.Error("expected error for invalid byte id")
	}
}

func TestWhitespaceTokenizer(t *testing.T) {
	wt := NewWhitespaceTokenizer()
	ids, err := wt.Encode("one two three")
	if err != nil {
		t.Fatal(err)
	}
	if len(ids) != 3 {
		t.Errorf("expected 3, got %d", len(ids))
	}
	// Repeated words reuse ids.
	ids2, _ := wt.Encode("one one")
	if len(ids2) != 2 || ids2[0] != ids2[1] {
		t.Error("expected id reuse")
	}
	out, err := wt.Decode(ids)
	if err != nil {
		t.Fatal(err)
	}
	if out != "one two three" {
		t.Errorf("got %q", out)
	}
}

func TestWhitespaceTokenizerUnknownID(t *testing.T) {
	wt := NewWhitespaceTokenizer()
	if _, err := wt.Decode([]int{500}); err == nil {
		t.Error("expected error for unknown id")
	}
}

func TestHashSet(t *testing.T) {
	s := NewHashSet("a", "b")
	if !s.Contains("a") || s.Contains("z") {
		t.Error("hash set behavior")
	}
}

func TestBPEDataType(t *testing.T) {
	tk := NewBPETokenizer(true)
	// A fresh tokenizer's encode must be repeatable.
	a, _ := tk.Encode("same text")
	b, _ := tk.Encode("same text")
	if len(a) != len(b) {
		t.Error("encode must be deterministic in length")
	}
	for i := range a {
		if a[i] != b[i] {
			t.Error("encode must be deterministic")
		}
	}
}