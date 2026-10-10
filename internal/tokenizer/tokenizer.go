// Package tokenizer provides BPE and byte-level tokenizers for the
// inference engine.
package tokenizer

import (
	"errors"
	"fmt"
	"sort"
	"strings"
)

// Special tokens used by the tokenizer vocabulary.
const (
	TokPad   = "<pad>"
	TokUnk   = "<unk>"
	TokBos   = "<s>"
	TokEos   = "</s>"
	TokMask  = "<mask>"
)

// Tokenizer converts text to token ids and back.
type Tokenizer interface {
	// Encode converts text to token ids.
	Encode(text string) ([]int, error)
	// Decode converts token ids back to text.
	Decode(ids []int) (string, error)
	// VocabSize returns the vocabulary size.
	VocabSize() int
	// TokenToID returns the id of a token, or -1.
	TokenToID(tok string) int
	// IDToToken returns the token for an id, or "".
	IDToToken(id int) string
}

// Vocabulary maps tokens to ids and back.
type Vocabulary struct {
	idToToken []string
	tokenToID map[string]int
}

// NewVocabulary creates an empty vocabulary.
func NewVocabulary() *Vocabulary {
	return &Vocabulary{tokenToID: make(map[string]int)}
}

// Add adds a token and returns its id.
func (v *Vocabulary) Add(tok string) int {
	if id, ok := v.tokenToID[tok]; ok {
		return id
	}
	id := len(v.idToToken)
	v.idToToken = append(v.idToToken, tok)
	v.tokenToID[tok] = id
	return id
}

// Get returns the id of a token and whether it exists.
func (v *Vocabulary) Get(tok string) (int, bool) {
	id, ok := v.tokenToID[tok]
	return id, ok
}

// Lookup returns the id of a token, or -1.
func (v *Vocabulary) Lookup(tok string) int {
	if id, ok := v.tokenToID[tok]; ok {
		return id
	}
	return -1
}

// GetByID returns the token for an id, or "".
func (v *Vocabulary) GetByID(id int) string {
	if id < 0 || id >= len(v.idToToken) {
		return ""
	}
	return v.idToToken[id]
}

// Len returns the number of tokens.
func (v *Vocabulary) Len() int { return len(v.idToToken) }

// Tokens returns all tokens in id order.
func (v *Vocabulary) Tokens() []string {
	return append([]string(nil), v.idToToken...)
}

// Merge is a BPE merge rule.
type Merge struct {
	Pair  [2]string
	Rank  int
	Merged string
}

// BPETokenizer implements byte-pair-encoding tokenization.
type BPETokenizer struct {
	vocab       *Vocabulary
	merges      []Merge
	mergeIndex  map[[2]string]int
	unkID       int
	bosID       int
	eosID       int
	padID       int
	byteFallback bool
}

// NewBPETokenizer creates an empty BPE tokenizer with special tokens.
func NewBPETokenizer(byteFallback bool) *BPETokenizer {
	v := NewVocabulary()
	t := &BPETokenizer{
		vocab:        v,
		mergeIndex:   make(map[[2]string]int),
		unkID:        v.Add(TokUnk),
		bosID:        v.Add(TokBos),
		eosID:        v.Add(TokEos),
		padID:        v.Add(TokPad),
		byteFallback: byteFallback,
	}
	if byteFallback {
		// Reserve 256 byte tokens (Ù-style visible representation).
		for b := 0; b < 256; b++ {
			v.Add(fmt.Sprintf("<0x%02X>", b))
		}
	}
	return t
}

// AddToken adds a token to the vocabulary and trains adds a merge rule.
func (t *BPETokenizer) AddToken(tok string) int {
	return t.vocab.Add(tok)
}

// AddMerge registers a merge rule for a pair of existing tokens.
func (t *BPETokenizer) AddMerge(a, b, merged string) {
	pair := [2]string{a, b}
	if _, ok := t.mergeIndex[pair]; ok {
		return
	}
	t.mergeIndex[pair] = len(t.merges)
	t.merges = append(t.merges, Merge{Pair: pair, Rank: len(t.merges), Merged: merged})
	t.vocab.Add(merged)
}

// Train learns merges from a corpus using BPE training.
func (t *BPETokenizer) Train(corpus []string, numMerges, maxVocab int) {
	if numMerges <= 0 {
		return
	}

	// Start with the base vocabulary: byte fallback or characters.
	if t.byteFallback {
		for b := 0; b < 256; b++ {
			t.vocab.Add(fmt.Sprintf("<0x%02X>", b))
		}
	}

	// Represent the corpus as sequences of single characters.
	var words []string
	for _, line := range corpus {
		for _, w := range strings.Fields(line) {
			words = append(words, w)
		}
	}

	seqs := make([][]string, len(words))
	for i, w := range words {
		seqs[i] = strings.Split(w, "")
		for _, ch := range seqs[i] {
			t.vocab.Add(ch)
		}
	}

	for n := 0; n < numMerges; n++ {
		// Count adjacent pair frequencies.
		counts := make(map[[2]string]int)
		for _, s := range seqs {
			for i := 0; i+1 < len(s); i++ {
				counts[[2]string{s[i], s[i+1]}]++
			}
		}
		if len(counts) == 0 {
			return
		}
		type pc struct {
			pair [2]string
			n    int
		}
		pairs := make([]pc, 0, len(counts))
		for p, c := range counts {
			pairs = append(pairs, pc{p, c})
		}
		sort.Slice(pairs, func(i, j int) bool {
			if pairs[i].n != pairs[j].n {
				return pairs[i].n > pairs[j].n
			}
			return pairs[i].pair[0] < pairs[j].pair[0]
		})
		best := pairs[0]
		merged := best.pair[0] + best.pair[1]
		t.AddMerge(best.pair[0], best.pair[1], merged)

		// Apply the merge to every sequence.
		for i, s := range seqs {
			seqs[i] = applyMerge(s, best.pair, merged)
		}
		if t.vocab.Len() >= maxVocab {
			return
		}
	}
}

func applyMerge(seq []string, pair [2]string, merged string) []string {
	out := make([]string, 0, len(seq))
	for i := 0; i < len(seq); {
		if i+1 < len(seq) && seq[i] == pair[0] && seq[i+1] == pair[1] {
			out = append(out, merged)
			i += 2
			continue
		}
		out = append(out, seq[i])
		i++
	}
	return out
}

// Encode applies BPE merges to the input text.
func (t *BPETokenizer) Encode(text string) ([]int, error) {
	if text == "" {
		return []int{}, nil
	}
	var ids []int
	for _, word := range strings.Fields(text) {
		seq := strings.Split(word, "")
		// Apply merges in learned rank order.
		for {
			bestIdx := -1
			bestRank := len(t.merges) + 1
			for i := 0; i+1 < len(seq); i++ {
				if r, ok := t.mergeIndex[[2]string{seq[i], seq[i+1]}]; ok && r < bestRank {
					bestRank = r
					bestIdx = i
				}
			}
			if bestIdx < 0 {
				break
			}
			seq = applyMerge(seq, [2]string{seq[bestIdx], seq[bestIdx+1]}, t.merges[bestRank].Merged)
		}
		for _, tok := range seq {
			id := t.vocab.Lookup(tok)
			if id < 0 {
				id = t.unkID
			}
			ids = append(ids, id)
		}
	}
	return ids, nil
}

// Decode joins tokens back into text.
func (t *BPETokenizer) Decode(ids []int) (string, error) {
	var sb strings.Builder
	for _, id := range ids {
		if id == t.bosID || id == t.eosID || id == t.padID {
			continue
		}
		sb.WriteString(t.vocab.GetByID(id))
	}
	return sb.String(), nil
}

// VocabSize returns the vocabulary size.
func (t *BPETokenizer) VocabSize() int { return t.vocab.Len() }

// TokenToID returns a token id or -1.
func (t *BPETokenizer) TokenToID(tok string) int { return t.vocab.Lookup(tok) }

// IDToToken returns the token for an id.
func (t *BPETokenizer) IDToToken(id int) string { return t.vocab.GetByID(id) }

// BosID returns the beginning-of-sequence token id.
func (t *BPETokenizer) BosID() int { return t.bosID }

// EosID returns the end-of-sequence token id.
func (t *BPETokenizer) EosID() int { return t.eosID }

// PadID returns the padding token id.
func (t *BPETokenizer) PadID() int { return t.padID }

// ByteTokenizer is a simple byte-level tokenizer.
type ByteTokenizer struct {
	vocab *Vocabulary
}

// NewByteTokenizer creates a byte-level tokenizer (256 byte tokens).
func NewByteTokenizer() *ByteTokenizer {
	v := NewVocabulary()
	for b := 0; b < 256; b++ {
		v.Add(string(rune(b)))
	}
	return &ByteTokenizer{vocab: v}
}

// Encode converts bytes to ids.
func (b *ByteTokenizer) Encode(text string) ([]int, error) {
	ids := make([]int, 0, len(text))
	for i := 0; i < len(text); i++ {
		ids = append(ids, int(text[i]))
	}
	return ids, nil
}

// Decode converts ids back to bytes.
func (b *ByteTokenizer) Decode(ids []int) (string, error) {
	var sb strings.Builder
	for _, id := range ids {
		if id < 0 || id > 255 {
			return "", fmt.Errorf("invalid byte id %d", id)
		}
		sb.WriteByte(byte(id))
	}
	return sb.String(), nil
}

// VocabSize returns 256.
func (b *ByteTokenizer) VocabSize() int { return b.vocab.Len() }

// TokenToID returns a token id or -1.
func (b *ByteTokenizer) TokenToID(tok string) int { return b.vocab.Lookup(tok) }

// IDToToken returns the token for an id.
func (b *ByteTokenizer) IDToToken(id int) string { return b.vocab.GetByID(id) }

// HashSet is a simple token presence filter.
type HashSet map[string]bool

// NewHashSet creates a set from strings.
func NewHashSet(items ...string) HashSet {
	s := make(HashSet, len(items))
	for _, i := range items {
		s[i] = true
	}
	return s
}

// Contains reports whether the set has the item.
func (s HashSet) Contains(x string) bool { return s[x] }

// WhitespaceTokenizer splits on whitespace.
type WhitespaceTokenizer struct {
	vocab *Vocabulary
}

// NewWhitespaceTokenizer creates a whitespace tokenizer.
func NewWhitespaceTokenizer() *WhitespaceTokenizer {
	return &WhitespaceTokenizer{vocab: NewVocabulary()}
}

// Encode splits on whitespace and maps to ids, growing the vocabulary.
func (w *WhitespaceTokenizer) Encode(text string) ([]int, error) {
	fields := strings.Fields(text)
	ids := make([]int, 0, len(fields))
	for _, f := range fields {
		id, ok := w.vocab.Get(f)
		if !ok {
			id = w.vocab.Add(f)
		}
		ids = append(ids, id)
	}
	return ids, nil
}

// Decode joins ids with spaces.
func (w *WhitespaceTokenizer) Decode(ids []int) (string, error) {
	parts := make([]string, 0, len(ids))
	for _, id := range ids {
		tok := w.vocab.GetByID(id)
		if tok == "" {
			return "", errors.New("unknown token id")
		}
		parts = append(parts, tok)
	}
	return strings.Join(parts, " "), nil
}

// VocabSize returns the vocabulary size.
func (w *WhitespaceTokenizer) VocabSize() int { return w.vocab.Len() }

// TokenToID returns a token id or -1.
func (w *WhitespaceTokenizer) TokenToID(tok string) int { return w.vocab.Lookup(tok) }

// IDToToken returns the token for an id.
func (w *WhitespaceTokenizer) IDToToken(id int) string { return w.vocab.GetByID(id) }