package pkg

import "testing"

func mustPublish(t *testing.T, r *Registry, p Package) {
	t.Helper()
	if err := r.Publish(Release{Package: p}); err != nil {
		t.Fatal(err)
	}
}

func constraint(op, v string) Constraint {
	c, err := ParseConstraint(op + v)
	if err != nil {
		panic(err)
	}
	return c
}

func TestParseVersion(t *testing.T) {
	v, err := ParseVersion("1.2.3")
	if err != nil {
		t.Fatal(err)
	}
	if v.Major != 1 || v.Minor != 2 || v.Patch != 3 {
		t.Errorf("bad version %v", v)
	}
	if _, err := ParseVersion("x.y.z"); err == nil {
		t.Error("expected parse error")
	}
}

func TestVersionString(t *testing.T) {
	v, _ := ParseVersion("1.2.3-beta")
	if v.String() != "1.2.3-beta" {
		t.Errorf("got %s", v.String())
	}
	v2, _ := ParseVersion("1.0.0")
	if v2.String() != "1.0.0" {
		t.Errorf("got %s", v2.String())
	}
}

func TestVersionCompare(t *testing.T) {
	a, _ := ParseVersion("1.2.3")
	b, _ := ParseVersion("1.2.4")
	if a.Compare(b) != -1 {
		t.Error("1.2.3 < 1.2.4")
	}
	if b.Compare(a) != 1 {
		t.Error("1.2.4 > 1.2.3")
	}
	if a.Compare(a) != 0 {
		t.Error("equal")
	}
	c, _ := ParseVersion("2.0.0")
	if a.Compare(c) != -1 {
		t.Error("major ordering")
	}
}

func TestPrereleaseCompare(t *testing.T) {
	rel, _ := ParseVersion("1.0.0")
	pre, _ := ParseVersion("1.0.0-alpha")
	if rel.Compare(pre) != 1 {
		t.Error("release should be greater than prerelease")
	}
}

func TestConstraintMatches(t *testing.T) {
	v, _ := ParseVersion("1.5.0")
	if !constraint(">=", "1.0.0").Matches(v) {
		t.Error(">= 1.0.0 should match 1.5.0")
	}
	if constraint("<", "1.0.0").Matches(v) {
		t.Error("< 1.0.0 should not match 1.5.0")
	}
	if !constraint("^", "1.2.0").Matches(v) {
		t.Error("^ 1.2.0 should match 1.5.0")
	}
	if !constraint("~", "1.5.0").Matches(v) {
		t.Error("~ 1.5.0 should match 1.5.0")
	}
}

func TestConstraintParse(t *testing.T) {
	if _, err := ParseConstraint("bogus"); err == nil {
		t.Error("expected parse error")
	}
	c := constraint("==", "1.0.0")
	if c.Op != "==" {
		t.Errorf("got %s", c.Op)
	}
	if c.String() != "==1.0.0" {
		t.Errorf("got %s", c.String())
	}
}

func TestRegistryPublish(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{Name: "lib", Version: mustVersion(t, "1.0.0")})
	if r.Count() != 1 {
		t.Errorf("expected 1 package, got %d", r.Count())
	}
	if err := r.Publish(Release{Package: Package{Name: "lib", Version: mustVersion(t, "1.0.0")}}); err == nil {
		t.Error("expected duplicate version error")
	}
	if r.Publish(Release{}) == nil {
		t.Error("expected empty name error")
	}
}

func mustVersion(t *testing.T, s string) SemanticVersion {
	v, err := ParseVersion(s)
	if err != nil {
		t.Fatal(err)
	}
	return v
}

func TestRegistryVersionsSorted(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{Name: "lib", Version: mustVersion(t, "1.0.0")})
	mustPublish(t, r, Package{Name: "lib", Version: mustVersion(t, "2.0.0")})
	mustPublish(t, r, Package{Name: "lib", Version: mustVersion(t, "1.5.0")})
	vs := r.Versions("lib")
	if len(vs) != 3 || vs[0].String() != "2.0.0" {
		t.Errorf("expected newest first, got %v", vs)
	}
}

func TestRegistryGet(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{Name: "lib", Version: mustVersion(t, "1.0.0")})
	mustPublish(t, r, Package{Name: "lib", Version: mustVersion(t, "1.2.0")})
	rel, err := r.Get("lib", constraint(">=", "1.1.0"))
	if err != nil {
		t.Fatal(err)
	}
	if rel.Package.Version.String() != "1.2.0" {
		t.Errorf("got %s", rel.Package.Version)
	}
	if _, err := r.Get("lib", constraint(">=", "9.0.0")); err == nil {
		t.Error("expected no match")
	}
}

func TestRegistrySearch(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{Name: "json", Description: "JSON utilities"})
	res := r.Search("json")
	if len(res) != 1 {
		t.Errorf("expected 1 result, got %d", len(res))
	}
}

func TestResolve(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{
		Name: "app", Version: mustVersion(t, "1.0.0"),
		Dependencies: []Dependency{{Name: "core", Constraint: constraint(">=", "1.0.0")}},
	})
	mustPublish(t, r, Package{Name: "core", Version: mustVersion(t, "1.0.0")})
	mustPublish(t, r, Package{Name: "core", Version: mustVersion(t, "1.4.0")})

	res, err := r.Resolve([]Dependency{{Name: "app", Constraint: constraint("==", "1.0.0")}})
	if err != nil {
		t.Fatal(err)
	}
	if res["core"].String() != "1.4.0" {
		t.Errorf("expected newest core, got %s", res["core"])
	}
}

func TestManagerInstall(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{Name: "x", Version: mustVersion(t, "1.0.0")})
	m := NewManager(r, "/tmp")
	if err := m.Install("x", constraint("==", "1.0.0")); err != nil {
		t.Fatal(err)
	}
	if len(m.Installed()) != 1 {
		t.Error("expected 1 installed")
	}
}

func TestManagerInstallMissing(t *testing.T) {
	m := NewManager(NewRegistry(), "/tmp")
	if err := m.Install("nope", constraint("==", "1.0.0")); err == nil {
		t.Error("expected error")
	}
}

func TestManagerUninstall(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{Name: "x", Version: mustVersion(t, "1.0.0")})
	m := NewManager(r, "/tmp")
	m.Install("x", constraint("==", "1.0.0"))
	if err := m.Uninstall("x"); err != nil {
		t.Fatal(err)
	}
	if err := m.Uninstall("x"); err == nil {
		t.Error("expected not-installed error")
	}
}

func TestManagerLockfile(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{Name: "x", Version: mustVersion(t, "1.0.0")})
	m := NewManager(r, "/tmp")
	m.Install("x", constraint("==", "1.0.0"))
	lf := m.LockfileData()
	if lf.Packages["x"].String() != "1.0.0" {
		t.Errorf("lockfile: %v", lf.Packages)
	}
}

func TestChecksum(t *testing.T) {
	a := computeChecksum(map[string][]byte{"f": {1, 2, 3}})
	b := computeChecksum(map[string][]byte{"f": {1, 2, 4}})
	if a == b {
		t.Error("different content should differ")
	}
	if a != computeChecksum(map[string][]byte{"f": {1, 2, 3}}) {
		t.Error("checksum must be deterministic")
	}
}

func TestVerify(t *testing.T) {
	r := NewRegistry()
	mustPublish(t, r, Package{
		Name: "x", Version: mustVersion(t, "1.0.0"),
		Checksum: "deadbeef",
	})
	m := NewManager(r, "/tmp")
	m.Install("x", constraint("==", "1.0.0"))
	bad := m.Verify()
	if len(bad) != 1 {
		t.Errorf("expected 1 bad package, got %v", bad)
	}
}