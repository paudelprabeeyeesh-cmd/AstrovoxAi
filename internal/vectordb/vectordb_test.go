package vectordb

import "testing"

func vec(vals ...float64) Vector { return Vector(vals) }

func TestVectorNorm(t *testing.T) {
	v := vec(3, 4)
	if v.Norm() != 5 {
		t.Errorf("expected norm 5, got %f", v.Norm())
	}
}

func TestVectorNormalize(t *testing.T) {
	v := vec(3, 4)
	n := v.Normalize()
	if n.Norm() < 0.999 || n.Norm() > 1.001 {
		t.Errorf("expected unit norm, got %f", n.Norm())
	}
	if v.Norm() != 5 {
		t.Error("Normalize must not mutate the original")
	}
}

func TestCosineSimilarity(t *testing.T) {
	a := vec(1, 0)
	b := vec(1, 0)
	if s := CosineSimilarity(a, b); s < 0.999 || s > 1.001 {
		t.Errorf("expected similarity 1.0, got %f", s)
	}
	c := vec(0, 1)
	if s := CosineSimilarity(a, c); s != 0 {
		t.Errorf("expected similarity 0, got %f", s)
	}
}

func TestDotProduct(t *testing.T) {
	a := vec(1, 2, 3)
	b := vec(4, 5, 6)
	if DotProduct(a, b) != 32 {
		t.Errorf("expected 32, got %f", DotProduct(a, b))
	}
}

func TestEuclideanDistance(t *testing.T) {
	a := vec(0, 0)
	b := vec(3, 4)
	if EuclideanDistance(a, b) != 5 {
		t.Errorf("expected 5, got %f", EuclideanDistance(a, b))
	}
}

func TestVectorDBInsertSearch(t *testing.T) {
	db := NewVectorDB(MetricCosine, 2)
	db.Insert(&Document{ID: "a", Vector: vec(1, 0)})
	db.Insert(&Document{ID: "b", Vector: vec(0, 1)})
	db.Insert(&Document{ID: "c", Vector: vec(0.9, 0.1)})

	res, err := db.Search(vec(1, 0), 2)
	if err != nil {
		t.Fatal(err)
	}
	if len(res) != 2 {
		t.Fatalf("expected 2 results, got %d", len(res))
	}
	if res[0].ID != "a" {
		t.Errorf("expected closest a, got %s", res[0].ID)
	}
}

func TestVectorDBDimensionMismatch(t *testing.T) {
	db := NewVectorDB(MetricCosine, 3)
	err := db.Insert(&Document{ID: "a", Vector: vec(1, 0)})
	if err == nil {
		t.Error("expected dimension mismatch error")
	}
	if _, err := db.Search(vec(1, 0), 1); err == nil {
		t.Error("expected search dimension error")
	}
}

func TestVectorDBGetDelete(t *testing.T) {
	db := NewVectorDB(MetricCosine, 2)
	db.Insert(&Document{ID: "a", Vector: vec(1, 0)})
	if _, ok := db.Get("a"); !ok {
		t.Error("expected to find a")
	}
	if !db.Delete("a") {
		t.Error("expected delete true")
	}
	if db.Delete("a") {
		t.Error("expected delete false for missing")
	}
	if db.Len() != 0 {
		t.Errorf("expected 0 docs, got %d", db.Len())
	}
}

func TestVectorDBUpdate(t *testing.T) {
	db := NewVectorDB(MetricCosine, 2)
	db.Insert(&Document{ID: "a", Vector: vec(1, 0)})
	if err := db.Update(&Document{ID: "a", Vector: vec(0, 1)}); err != nil {
		t.Fatal(err)
	}
	if err := db.Update(&Document{ID: "missing", Vector: vec(0, 1)}); err == nil {
		t.Error("expected error updating missing doc")
	}
}

func TestVectorDBFilteredSearch(t *testing.T) {
	db := NewVectorDB(MetricCosine, 2)
	db.Insert(&Document{ID: "a", Vector: vec(1, 0), Payload: map[string]interface{}{"keep": true}})
	db.Insert(&Document{ID: "b", Vector: vec(1, 0), Payload: map[string]interface{}{"keep": false}})
	res, err := db.SearchWithFilter(vec(1, 0), 5, func(p map[string]interface{}) bool {
		v, _ := p["keep"].(bool)
		return v
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(res) != 1 || res[0].ID != "a" {
		t.Error("filtered search returned wrong results")
	}
}

func TestVectorDBBatchInsert(t *testing.T) {
	db := NewVectorDB(MetricCosine, 2)
	n, err := db.InsertBatch([]*Document{
		{ID: "a", Vector: vec(1, 0)},
		{ID: "b", Vector: vec(0, 1)},
	})
	if err != nil {
		t.Fatal(err)
	}
	if n != 2 || db.Len() != 2 {
		t.Errorf("expected 2 inserted, got %d (len %d)", n, db.Len())
	}
}

func TestHNSWIndexAddSearch(t *testing.T) {
	idx := NewHNSWIndex(MetricCosine)
	for i := 0; i < 50; i++ {
		v := make(Vector, 2)
		v[0] = float64(i) / 50
		v[1] = 1.0 - float64(i)/50
		idx.Add(&Document{ID: "d", Vector: v})
	}
	if idx.Size() != 50 {
		t.Errorf("expected 50 nodes, got %d", idx.Size())
	}
	res := idx.Search(vec(1, 0), 3)
	if len(res) == 0 {
		t.Fatal("expected results")
	}
	if res[0].ID != "d" {
		t.Errorf("expected d, got %s", res[0].ID)
	}
}

func TestHNSWParams(t *testing.T) {
	p := DefaultHNSWParams()
	if p.M != 16 {
		t.Errorf("expected M 16, got %d", p.M)
	}
	if p.EfConstruction != 200 {
		t.Errorf("expected ef 200, got %d", p.EfConstruction)
	}
}

func TestNewVectorDBWithIndex(t *testing.T) {
	db := NewVectorDBWithIndex(MetricCosine, 2)
	db.Insert(&Document{ID: "a", Vector: vec(1, 0)})
	db.Insert(&Document{ID: "b", Vector: vec(0, 1)})
	res, err := db.Search(vec(0, 1), 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(res) != 1 || res[0].ID != "b" {
		t.Error("expected b as nearest")
	}
}

func TestDBStats(t *testing.T) {
	db := NewVectorDB(MetricDotProduct, 4)
	db.Insert(&Document{ID: "a", Vector: vec(1, 2, 3, 4)})
	st := db.Stats()
	if st.Documents != 1 || st.Dimension != 4 || st.Indexed {
		t.Errorf("unexpected stats: %+v", st)
	}
}

func TestMetricString(t *testing.T) {
	if MetricCosine.String() != "cosine" {
		t.Error("cosine")
	}
	if MetricEuclidean.String() != "euclidean" {
		t.Error("euclidean")
	}
}

func TestMetricDistance(t *testing.T) {
	// Euclidean negated so higher is better
	d := MetricEuclidean.Distance(vec(0, 0), vec(1, 0))
	if d != -1 {
		t.Errorf("expected -1, got %f", d)
	}
}

func TestVectorDimension(t *testing.T) {
	if vec(1, 2, 3).Dimension() != 3 {
		t.Error("expected dimension 3")
	}
}
