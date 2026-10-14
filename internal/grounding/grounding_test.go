package grounding

import (
	"strings"
	"testing"
)

func fixtureChunks() map[string]Chunk {
	return map[string]Chunk{
		"c1": {
			ID:    "c1",
			Owner: "tenant-a",
			Text:  "credential rotation procedure for postgres requires a new password and a restart",
		},
		"c2": {
			ID:    "c2",
			Owner: "tenant-a",
			Text:  "the quarterly revenue target for apac grew by twelve percent year over year",
		},
		"c3": {
			ID:    "c3",
			Owner: "tenant-b",
			Text:  "emea quarterly revenue target grew by eight percent year over year",
		},
	}
}

func TestAFullySupportedClaimIsSupported(t *testing.T) {
	verdict := Check(
		Claim{Text: "credential rotation for postgres requires a new password", ChunkID: "c1"},
		fixtureChunks(), "tenant-a",
	)
	if !verdict.Supported {
		t.Fatalf("verdict = %+v, want supported", verdict)
	}
	if verdict.Support < Threshold {
		t.Fatalf("support %.2f is below the threshold", verdict.Support)
	}
}

func TestAnUncitedClaimIsReportedAsUncited(t *testing.T) {
	// The interesting failure is a claim with no citation at all. It is neither
	// a missing chunk nor a permission problem, and conflating the two makes
	// the report unreadable.
	verdict := Check(Claim{Text: "apac revenue grew twelve percent", ChunkID: ""}, fixtureChunks(), "tenant-a")
	if !verdict.Uncited {
		t.Fatal("a claim with no citation was not reported as uncited")
	}
	if verdict.Supported {
		t.Fatal("an uncited claim was reported as supported")
	}
}

func TestAMissingCitationIsReportedSeparately(t *testing.T) {
	verdict := Check(
		Claim{Text: "credential rotation for postgres", ChunkID: "no-such-chunk"},
		fixtureChunks(), "tenant-a",
	)
	if !verdict.MissingChunk {
		t.Fatal("a citation to a nonexistent chunk was not reported as missing")
	}
	if verdict.Uncited {
		t.Fatal("a missing chunk was reported as uncited; the two are different failures")
	}
}

func TestAClaimCitingAnotherTenantIsNotPermitted(t *testing.T) {
	// The cross-tenant case. It must be its own category: a paraphrase against
	// another tenant's text still "supports" the claim, and reporting it as
	// merely unsupported would hide a breach behind a quality metric.
	verdict := Check(
		Claim{Text: "emea quarterly revenue target grew eight percent", ChunkID: "c3"},
		fixtureChunks(), "tenant-a",
	)
	if !verdict.NotPermitted {
		t.Fatal("a citation to another tenant's chunk was not reported as not permitted")
	}
	if verdict.Supported {
		t.Fatal("a claim supported only by another tenant's text was reported as supported")
	}
}

func TestAnUnsupportedClaimScoresBelowThreshold(t *testing.T) {
	// "credential rotation happens every tuesday" shares two of its five terms
	// with c1, so support is below threshold but above zero - the diagnosable
	// middle case where a model may believe the citation backs it.
	verdict := Check(
		Claim{Text: "credential rotation happens every tuesday", ChunkID: "c1"},
		fixtureChunks(), "tenant-a",
	)
	if verdict.Supported {
		t.Fatal("a claim whose terms are absent from the chunk was reported as supported")
	}
	if !verdict.Weak {
		t.Fatalf("support %.2f was not reported as weak", verdict.Support)
	}
	if verdict.Support <= 0 {
		t.Fatal("this claim shares terms, so support must be above zero for the weak label")
	}
}

func TestAClaimWithNoSharedTermsIsNotWeak(t *testing.T) {
	// The other side: a claim sharing nothing is fully unsupported, and
	// labelling it "weak" would put a total mismatch in the same bucket as a
	// near miss.
	verdict := Check(
		Claim{Text: "kubernetes eviction thresholds are measured in bytes", ChunkID: "c1"},
		fixtureChunks(), "tenant-a",
	)
	if verdict.Weak {
		t.Fatalf("a zero-overlap claim was reported as weak (support %.2f)", verdict.Support)
	}
}

func TestAOneWordOverlapDoesNotPassTheThreshold(t *testing.T) {
	// A single shared word against a long chunk must not count as grounded.
	// This is what a low threshold buys, and it is how groundedness becomes
	// decorative.
	verdict := Check(
		Claim{Text: "the sky is blue over the pacific ocean today", ChunkID: "c1"},
		fixtureChunks(), "tenant-a",
	)
	if verdict.Supported {
		t.Fatalf("support %.2f passed the threshold on one shared word", verdict.Support)
	}
}

func TestStopwordsDoNotInflateSupport(t *testing.T) {
	// Two sentences sharing only function words share nothing, semantically.
	// If stopwords counted, any two English sentences would overlap and the
	// threshold would mean nothing.
	verdict := Check(
		Claim{Text: "the of and to in is it", ChunkID: "c1"},
		fixtureChunks(), "tenant-a",
	)
	if verdict.Support > 0 {
		t.Fatalf("function words alone scored %.2f support", verdict.Support)
	}
}

func TestAClaimWithNoSignificantTermsIsWeakNotSupported(t *testing.T) {
	// "It is true" has no checkable content. Treating it as supported lets any
	// empty statement through.
	verdict := Check(Claim{Text: "it is the of", ChunkID: "c1"}, fixtureChunks(), "tenant-a")
	if verdict.Supported {
		t.Fatal("a claim with no significant terms was reported as supported")
	}
	if !verdict.Weak {
		t.Fatal("a termless claim was not flagged")
	}
}

func TestTheReportCategorisesEveryClaim(t *testing.T) {
	report := Evaluate("answer", []Claim{
		{Text: "credential rotation for postgres requires a new password", ChunkID: "c1"},
		{Text: "apac revenue grew twelve percent", ChunkID: ""},
		{Text: "credential rotation", ChunkID: "missing"},
		{Text: "emea revenue grew eight percent", ChunkID: "c3"},
	}, fixtureChunks(), "tenant-a")

	if report.Claims != 4 {
		t.Fatalf("claims = %d", report.Claims)
	}
	if report.Supported != 1 {
		t.Fatalf("supported = %d, want 1", report.Supported)
	}
	if report.Uncited != 1 {
		t.Fatalf("uncited = %d, want 1", report.Uncited)
	}
	if report.MissingChunk != 1 {
		t.Fatalf("missing = %d, want 1", report.MissingChunk)
	}
	if report.NotPermitted != 1 {
		t.Fatalf("not_permitted = %d, want 1", report.NotPermitted)
	}
	if report.Accuracy != 0.25 {
		t.Fatalf("accuracy = %.3f, want 0.25", report.Accuracy)
	}
}

func TestTheOwnerBlankDoesNotRestrict(t *testing.T) {
	// An empty owner means the caller is not identified, so the permission
	// check cannot fire. That is a caller that has no access control to
	// enforce, not a bug to paper over.
	verdict := Check(Claim{Text: "emea revenue grew eight percent", ChunkID: "c3"}, fixtureChunks(), "")
	if verdict.NotPermitted {
		t.Fatal("an unidentified caller was scoped out")
	}
}

func TestTheSummaryShowsEveryCategory(t *testing.T) {
	report := Evaluate("", []Claim{{Text: "x", ChunkID: ""}}, fixtureChunks(), "tenant-a")
	text := report.String()
	for _, category := range []string{"uncited", "missing", "not_permitted", "weak"} {
		if !strings.Contains(text, category) {
			t.Fatalf("the summary omits %s: %s", category, text)
		}
	}
}

func TestNonAsciiClaimsAreNotEmptied(t *testing.T) {
	// A claim in another script must still be checkable, or the checker is
	// silently English-only and reports everything else as unsupported.
	terms := tokenize("les informations de connexion sont chiffrées au repos")
	found := false
	for _, t := range terms {
		if t == "chiffrées" {
			found = true
		}
	}
	if !found {
		t.Fatalf("accented terms were dropped: %v", terms)
	}
}

func TestMeanSupportIgnoresTheFailures(t *testing.T) {
	// Mean support is over claims that were actually checkable. Including the
	// uncited and cross-tenant ones would drag it down for reasons that are
	// not support quality.
	report := Evaluate("", []Claim{
		{Text: "credential rotation for postgres requires a new password", ChunkID: "c1"},
		{Text: "no citation at all here", ChunkID: ""},
	}, fixtureChunks(), "tenant-a")
	if report.MeanSupport <= 0 {
		t.Fatal("mean support was zeroed by an uncited claim")
	}
}
