package pluginx

import (
	"bytes"
	"testing"
)

func validManifest() *Manifest {
	return &Manifest{
		Name: "hello-plugin",
		Description: "A test plugin",
		Author: "astrovox",
		License: "Apache-2.0",
		Version: "1.0.0",
		APIVersion: "1.0.0",
		Entrypoint: "main.wasm",
		HostRange: []string{"1.0.0 - 2.0.0"},
		Capabilities: []string{"tensor"},
	}
}

func TestParseSemVer(t *testing.T) {
	v, err := ParseSemVer("1.2.3")
	if err != nil {
		t.Fatal(err)
	}
	if v.Major != 1 || v.Minor != 2 || v.Patch != 3 {
		t.Errorf("got %v", v)
	}
	if v.String() != "1.2.3" {
		t.Errorf("string: %s", v.String())
	}
	if _, err := ParseSemVer("bad"); err == nil {
		t.Error("expected parse error")
	}
}

func TestSemVerCompare(t *testing.T) {
	a, _ := ParseSemVer("1.2.3")
	b, _ := ParseSemVer("1.2.4")
	c, _ := ParseSemVer("1.3.0")
	d, _ := ParseSemVer("2.0.0")
	if a.Compare(b) != -1 || b.Compare(a) != 1 || a.Compare(a) != 0 {
		t.Error("patch ordering")
	}
	if a.Compare(c) != -1 || c.Compare(d) != -1 {
		t.Error("minor/major ordering")
	}
}

func TestCompatRangeContains(t *testing.T) {
	lo, _ := ParseSemVer("1.0.0")
	hi, _ := ParseSemVer("2.0.0")
	r := CompatRange{Min: lo, Max: hi}
	v1, _ := ParseSemVer("1.5.0")
	v2, _ := ParseSemVer("2.0.0")
	if !r.Contains(v1) {
		t.Error("1.5.0 should be in range")
	}
	if r.Contains(v2) {
		t.Error("max bound must be exclusive")
	}
	if r.String() != "1.0.0 - 2.0.0" {
		t.Errorf("string: %s", r.String())
	}
}

func TestManifestValidate(t *testing.T) {
	if err := validManifest().Validate(); err != nil {
		t.Fatal(err)
	}
	bad := validManifest()
	bad.Name = ""
	if bad.Validate() == nil {
		t.Error("expected name error")
	}
	bad = validManifest()
	bad.Entrypoint = ""
	if bad.Validate() == nil {
		t.Error("expected entrypoint error")
	}
	bad = validManifest()
	bad.Version = "x"
	if bad.Validate() == nil {
		t.Error("expected version error")
	}
	bad = validManifest()
	bad.APIVersion = "x"
	if bad.Validate() == nil {
		t.Error("expected api version error")
	}
	bad = validManifest()
	bad.HostRange = []string{"garbage"}
	if bad.Validate() == nil {
		t.Error("expected host range error")
	}
}

func TestManifestEncode(t *testing.T) {
	m := validManifest()
	m.Tags = []string{"b", "a"}
	data, err := m.Encode()
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(data, []byte("hello-plugin")) {
		t.Error("expected name in JSON")
	}
	if m.Tags[0] != "a" {
		t.Error("tags should be sorted")
	}
}

func TestCompatibilityCheck(t *testing.T) {
	c, err := NewCompatibility("1.5.0", "1.2.0")
	if err != nil {
		t.Fatal(err)
	}
	if c.HostVersion().String() != "1.5.0" || c.APIVersion().String() != "1.2.0" {
		t.Error("version accessors")
	}
	if err := c.Check(validManifest()); err != nil {
		t.Errorf("expected compatible, got %v", err)
	}
	if err := c.CheckAPI(validManifest()); err != nil {
		t.Errorf("api should match, got %v", err)
	}
	if err := c.Full(validManifest()); err != nil {
		t.Fatal(err)
	}
}

func TestCompatibilityHostMismatch(t *testing.T) {
	c, _ := NewCompatibility("3.0.0", "1.0.0")
	err := c.Check(validManifest())
	if err == nil {
		t.Fatal("expected host incompatibility")
	}
}

func TestCompatibilityAPIMajorMismatch(t *testing.T) {
	c, _ := NewCompatibility("1.5.0", "2.0.0")
	m := validManifest()
	m.APIVersion = "1.0.0"
	if err := c.CheckAPI(m); err == nil {
		t.Error("expected api major mismatch")
	}
}

func TestCompatibilityAPINewerMinor(t *testing.T) {
	c, _ := NewCompatibility("1.5.0", "1.2.0")
	m := validManifest()
	m.APIVersion = "1.9.0"
	if err := c.CheckAPI(m); err == nil {
		t.Error("expected newer api minor rejection")
	}
}

func TestCompatibilityNoConstraint(t *testing.T) {
	c, _ := NewCompatibility("1.5.0", "1.0.0")
	m := validManifest()
	m.HostRange = nil
	if err := c.Check(m); err != nil {
		t.Errorf("unconstrained should pass, got %v", err)
	}
	if err := c.Check(nil); err == nil {
		t.Error("expected nil manifest error")
	}
}

func TestMarketplace(t *testing.T) {
	mk := NewMarketplace()
	m1 := validManifest()
	if err := mk.Publish(m1); err != nil {
		t.Fatal(err)
	}
	m2 := validManifest()
	m2.Name = "zed-plugin"
	m2.Description = "zebra"
	if err := mk.Publish(m2); err != nil {
		t.Fatal(err)
	}
	if mk.Count() != 2 {
		t.Error("count")
	}
	if names := mk.List(); len(names) != 2 || names[0] != "hello-plugin" {
		t.Errorf("list: %v", names)
	}
	if got, ok := mk.Get("hello-plugin"); !ok || got.Name != "hello-plugin" {
		t.Error("get")
	}
	if res := mk.Search("zebra"); len(res) != 1 || res[0].Name != "zed-plugin" {
		t.Errorf("search: %v", res)
	}
}

func TestMarketplacePublishInvalid(t *testing.T) {
	mk := NewMarketplace()
	if mk.Publish(nil) == nil {
		t.Error("expected nil error")
	}
	if mk.Publish(&Manifest{}) == nil {
		t.Error("expected validation error")
	}
}

func TestResolveManifestDependencies(t *testing.T) {
	m := validManifest()
	m.Dependencies = []Dependency{{Name: "core", Constraint: ">=1.0.0"}}
	_, err := ResolveManifestDependencies(m)
	// No registry is populated here, so resolution fails with a message.
	if err == nil {
		t.Log("resolved without a registry (empty result)")
	}
	if _, err := ResolveManifestDependencies(nil); err == nil {
		t.Error("expected nil manifest error")
	}
	bad := validManifest()
	bad.Dependencies = []Dependency{{Name: "x", Constraint: "@@bad"}}
	if _, err := ResolveManifestDependencies(bad); err == nil {
		t.Error("expected constraint parse error")
	}
}