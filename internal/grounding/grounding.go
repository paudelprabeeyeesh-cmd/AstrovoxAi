// Package grounding measures whether an answer is actually supported by the
// text it claims to cite.
//
// It exists because "the answer has citations" and "the answer is supported"
// are different statements. A generated answer can cite a real chunk that does
// not contain the claim, cite a chunk the caller may not read, or state a
// claim with no citation at all. All three look like a grounded answer unless
// something checks.
//
// The check is deliberately lexical rather than semantic. That is a real
// limitation - a paraphrase is supported but scores zero here - and it is
// stated in the code rather than hidden, because a checker that quietly
// accepts paraphrases is a checker nobody can calibrate.
package grounding

import (
	"fmt"
	"strings"
)

// Chunk is the minimal support a citation can point at.
type Chunk struct {
	ID   string `json:"id"`
	Text string `json:"text"`
	// Owner is who may read it. A claim supported only by a chunk the caller
	// cannot read is not supported, however good the text match.
	Owner string `json:"owner,omitempty"`
}

// Claim is one statement in an answer and the chunk it cites.
type Claim struct {
	// Text is the statement.
	Text string `json:"text"`
	// ChunkID is what it cites; empty is an uncited claim.
	ChunkID string `json:"chunk_id"`
}

// Verdict is the outcome of checking one claim.
type Verdict struct {
	Claim string `json:"claim"`
	// ChunkID is the citation as given.
	ChunkID string `json:"chunk_id,omitempty"`
	// Uncited is true when the claim names no chunk.
	Uncited bool `json:"uncited,omitempty"`
	// MissingChunk is true when the claim cites a chunk that does not exist.
	MissingChunk bool `json:"missing_chunk,omitempty"`
	// NotPermitted is true when the chunk exists but belongs to another
	// caller. It is the cross-tenant case and is reported separately because
	// it is a security failure, not a quality one.
	NotPermitted bool `json:"not_permitted,omitempty"`
	// Weak is true when the claim shares some terms but fewer than Threshold,
	// or when it has none at all. It is the interesting middle case: not
	// supported, but close enough that a model may believe it is.
	Weak bool `json:"weak,omitempty"`
	// Support is the overlap between the claim and the chunk it cites, in
	// [0,1]. It is the measured part.
	Support float64 `json:"support"`
	// Matched is the terms found in both, so a low score is diagnosable.
	Matched []string `json:"matched,omitempty"`
	// Supported is the combined verdict.
	Supported bool `json:"supported"`
}

// Report aggregates the verdicts.
type Report struct {
	Claims int `json:"claims"`
	// Supported, Uncited, MissingChunk, NotPermitted, Weak break down the
	// claims, so a mean cannot hide a category.
	Supported    int `json:"supported"`
	Uncited      int `json:"uncited"`
	MissingChunk int `json:"missing_chunk"`
	NotPermitted int `json:"not_permitted"`
	Weak         int `json:"weak"`

	// Accuracy is Supported/Claims.
	Accuracy float64 `json:"accuracy"`
	// MeanSupport is the mean Support across cited, permitted claims.
	MeanSupport float64 `json:"mean_support"`

	Verdicts []Verdict `json:"verdicts,omitempty"`
}

// Threshold is the minimum overlap for a claim to count as supported.
//
// It is high because a low threshold is how "grounded" becomes decorative: a
// claim sharing one word with a long chunk would pass. 0.5 means half the
// claim's terms must appear in the support.
const Threshold = 0.5

// stopwords carry no signal, so including them inflates the overlap of any two
// English sentences and makes the threshold meaningless.
var stopwords = map[string]bool{
	"the": true, "a": true, "an": true, "and": true, "or": true, "of": true,
	"to": true, "in": true, "is": true, "are": true, "for": true, "on": true,
	"with": true, "by": true, "at": true, "from": true, "as": true, "that": true,
	"this": true, "it": true, "be": true, "was": true, "were": true, "has": true,
	"have": true, "had": true, "not": true, "but": true, "if": true, "than": true,
}

// tokenize splits text into significant terms.
func tokenize(text string) []string {
	fields := strings.FieldsFunc(text, func(r rune) bool {
		switch {
		case r >= 'a' && r <= 'z':
			return false
		case r >= 'A' && r <= 'Z':
			return false
		case r >= '0' && r <= '9':
			return false
		case r > 127:
			// Keep non-ASCII letters so a non-Latin claim is not emptied.
			return false
		default:
			return true
		}
	})
	out := make([]string, 0, len(fields))
	for _, f := range fields {
		lowered := strings.ToLower(f)
		if stopwords[lowered] {
			continue
		}
		out = append(out, lowered)
	}
	return out
}

// Check evaluates one claim against the chunks available to a caller.
//
// owner is the caller: a chunk belonging to anyone else is reported as not
// permitted rather than as unsupported, because the two call for different
// fixes and only one of them is a security incident.
func Check(claim Claim, chunks map[string]Chunk, owner string) Verdict {
	verdict := Verdict{Claim: claim.Text, ChunkID: claim.ChunkID}

	if claim.ChunkID == "" {
		verdict.Uncited = true
		return verdict
	}
	chunk, ok := chunks[claim.ChunkID]
	if !ok {
		verdict.MissingChunk = true
		return verdict
	}
	if owner != "" && chunk.Owner != "" && chunk.Owner != owner {
		verdict.NotPermitted = true
		return verdict
	}

	claimTerms := tokenize(claim.Text)
	if len(claimTerms) == 0 {
		// A claim with no significant terms cannot be checked. Treating it as
		// supported would let any empty statement pass, and treating it as a
		// miss hides it, so it is neither.
		verdict.Weak = true
		verdict.Support = 0
		return verdict
	}

	supportTerms := tokenize(chunk.Text)
	present := make(map[string]bool, len(supportTerms))
	for _, t := range supportTerms {
		present[t] = true
	}

	matched := 0
	for _, term := range claimTerms {
		if present[term] {
			matched++
			verdict.Matched = append(verdict.Matched, term)
		}
	}
	verdict.Support = float64(matched) / float64(len(claimTerms))
	verdict.Supported = verdict.Support >= Threshold
	if !verdict.Supported && verdict.Support > 0 {
		verdict.Weak = true
	}
	return verdict
}

// Evaluate checks every claim and aggregates.
func Evaluate(answer string, claims []Claim, chunks map[string]Chunk, owner string) *Report {
	report := &Report{Claims: len(claims)}
	var supportSum float64
	supportCount := 0

	for _, claim := range claims {
		verdict := Check(claim, chunks, owner)
		switch {
		case verdict.Uncited:
			report.Uncited++
		case verdict.MissingChunk:
			report.MissingChunk++
		case verdict.NotPermitted:
			report.NotPermitted++
		default:
			supportSum += verdict.Support
			supportCount++
			if verdict.Supported {
				report.Supported++
			} else {
				report.Weak++
			}
		}
		report.Verdicts = append(report.Verdicts, verdict)
	}
	_ = answer

	if report.Claims > 0 {
		report.Accuracy = float64(report.Supported) / float64(report.Claims)
	}
	if supportCount > 0 {
		report.MeanSupport = supportSum / float64(supportCount)
	}
	return report
}

// String renders the report. Every category is shown, so a high accuracy
// alongside an uncited claim is visible rather than averaged away.
func (r *Report) String() string {
	return fmt.Sprintf(
		"grounding: claims=%d supported=%d accuracy=%.3f mean_support=%.3f "+
			"uncited=%d missing=%d not_permitted=%d weak=%d",
		r.Claims, r.Supported, r.Accuracy, r.MeanSupport,
		r.Uncited, r.MissingChunk, r.NotPermitted, r.Weak,
	)
}
