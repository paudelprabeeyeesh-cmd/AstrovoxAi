package distributed

import (
	"context"
	"testing"
	"time"

	"github.com/astrovox/astrovox/tensor"
)

func newStore() *TCPStore {
	return NewTCPStore("inproc://test", 4, 5*time.Second)
}

func passThroughTensor(vals ...float64) *tensor.Tensor {
	t, _ := tensor.New(tensor.Float64, []int{len(vals)})
	copy(t.Float64(), vals)
	return t
}

func newTestTensors(n int) []*tensor.Tensor {
	out := make([]*tensor.Tensor, n)
	for i := range out {
		out[i] = passThroughTensor(1, 2)
	}
	return out
}

func TestTCPStoreSetGet(t *testing.T) {
	s := newStore()
	if err := s.Set("k", []byte("v")); err != nil {
		t.Fatal(err)
	}
	v, err := s.Get("k")
	if err != nil {
		t.Fatal(err)
	}
	if string(v) != "v" {
		t.Errorf("got %s", v)
	}
}

func TestTCPStoreWait(t *testing.T) {
	s := newStore()
	s.Set("a", []byte("1"))
	s.Set("b", []byte("2"))
	if err := s.Wait([]string{"a", "b"}, time.Second); err != nil {
		t.Fatal(err)
	}
}

func TestProcessGroupRank(t *testing.T) {
	pg := NewProcessGroup(2, 4, BackendGloo, newStore())
	if pg.Rank() != 2 {
		t.Errorf("expected rank 2, got %d", pg.Rank())
	}
	if pg.WorldSize() != 4 {
		t.Errorf("expected world 4, got %d", pg.WorldSize())
	}
}

func TestProcessGroupCollectivesSingle(t *testing.T) {
	pg := NewProcessGroup(0, 1, BackendGloo, newStore())
	ctx := context.Background()
	// With worldSize 1 the collectives pass through unchanged.
	t1 := passThroughTensor(1, 2)
	out, err := pg.AllReduce(ctx, t1, ReduceOpSum)
	if err != nil {
		t.Fatal(err)
	}
	if out.NumElements() != 2 || out.Float64()[0] != 1 {
		t.Error("expected passthrough")
	}
	if _, err := pg.Broadcast(ctx, t1, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := pg.Reduce(ctx, t1, 0, ReduceOpAvg); err != nil {
		t.Fatal(err)
	}
	if err := pg.Barrier(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := pg.AllGather(ctx, t1); err == nil {
		t.Error("expected not-implemented error for AllGather")
	}
}

func TestInitDistributedContext(t *testing.T) {
	if IsInitialized() {
		t.Skip("already initialized by another test")
	}
	if err := Init(BackendGloo, "inproc://init", 1, 0, 5*time.Second); err != nil {
		t.Fatal(err)
	}
	if Rank() != 0 || WorldSize() != 1 {
		t.Error("expected rank 0, world 1")
	}
	if GetDefaultGroup() == nil {
		t.Error("expected default group")
	}
	// Create a named group and look it up by the name we assigned.
	grp, err := NewGroup([]int{0}, BackendGloo)
	if err != nil {
		t.Fatal(err)
	}
	if grp.Rank() != 0 {
		t.Error("expected rank 0 in subgroup")
	}
	found, err := GetGroup("default")
	if err != nil || found == nil {
		t.Fatal(err)
	}
	if _, err := GetGroup("nope"); err == nil {
		t.Error("expected group not found error")
	}
	ctx := context.Background()
	if err := Barrier(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := AllReduce(ctx, passThroughTensor(1), ReduceOpSum); err != nil {
		t.Fatal(err)
	}
}

func TestDistributedNotInitialized(t *testing.T) {
	if IsInitialized() {
		t.Skip("already initialized")
	}
	if _, err := AllReduce(context.Background(), passThroughTensor(1), ReduceOpSum); err == nil {
		t.Error("expected not initialized error")
	}
	if err := Barrier(context.Background()); err == nil {
		t.Error("expected not initialized error")
	}
	if _, err := NewGroup([]int{0}, BackendGloo); err == nil {
		t.Error("expected not initialized error for groups")
	}
}

func TestNewGroupInvalidRanks(t *testing.T) {
	Init(BackendGloo, "inproc://init2", 4, 0, 5*time.Second)
	if _, err := NewGroup([]int{99}, BackendGloo); err == nil {
		t.Error("expected rank out of range error")
	}
}

func TestTensorParallelCreation(t *testing.T) {
	pg := NewProcessGroup(0, 4, BackendGloo, newStore())
	tp, err := NewTensorParallel(&TensorParallelConfig{TPSize: 4, GatherOutput: true}, pg)
	if err != nil {
		t.Fatal(err)
	}
	if tp.rank != 0 || tp.worldSize != 4 {
		t.Error("bad tp setup")
	}
}

func TestTensorParallelInvalid(t *testing.T) {
	pg := NewProcessGroup(0, 4, BackendGloo, newStore())
	if _, err := NewTensorParallel(&TensorParallelConfig{TPSize: 2}, pg); err == nil {
		t.Error("expected size mismatch error")
	}
}

func TestColumnParallelLinear(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	tp, _ := NewTensorParallel(&TensorParallelConfig{TPSize: 2}, pg)
	l, err := NewColumnParallelLinear(tp, 8, 16, true)
	if err != nil {
		t.Fatal(err)
	}
	if l.outputDim != 16 || l.bias == nil {
		t.Error("layer setup")
	}
}

func TestRowParallelLinear(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	tp, _ := NewTensorParallel(&TensorParallelConfig{TPSize: 2}, pg)
	l, err := NewRowParallelLinear(tp, 8, 16, true, true)
	if err != nil {
		t.Fatal(err)
	}
	if l.inputDim != 8 {
		t.Error("setup")
	}
}

func TestParallelEmbedding(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	tp, _ := NewTensorParallel(&TensorParallelConfig{TPSize: 2}, pg)
	pe, err := NewParallelEmbedding(tp, 100, 16)
	if err != nil {
		t.Fatal(err)
	}
	if pe.vocabSize != 100 {
		t.Error("vocab")
	}
}

func TestParallelAttention(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	tp, _ := NewTensorParallel(&TensorParallelConfig{TPSize: 2}, pg)
	pa, err := NewParallelAttention(tp, &ParallelAttentionConfig{
		HiddenDim: 64, NumHeads: 4, HeadDim: 16,
	})
	if err != nil {
		t.Fatal(err)
	}
	if pa.qProj == nil || pa.oProj == nil {
		t.Error("attention projections")
	}
}

func TestParallelAttentionInvalid(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	tp, _ := NewTensorParallel(&TensorParallelConfig{TPSize: 2}, pg)
	if _, err := NewParallelAttention(tp, &ParallelAttentionConfig{
		HiddenDim: 64, NumHeads: 3, HeadDim: 16,
	}); err == nil {
		t.Error("expected head divisibility error")
	}
}

func TestPipelineCreation(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	pp, err := NewPipelineParallel(&PipelineParallelConfig{
		NumStages: 2, NumMicrobatches: 4, Schedule: Schedule1F1B,
	}, pg)
	if err != nil {
		t.Fatal(err)
	}
	if pp.numStages != 2 {
		t.Error("stages")
	}
	if _, err := NewPipelineParallel(&PipelineParallelConfig{NumStages: 1, NumMicrobatches: 4}, pg); err == nil {
		t.Error("expected stage error")
	}
	if _, err := NewPipelineParallel(&PipelineParallelConfig{NumStages: 2, NumMicrobatches: 0}, pg); err == nil {
		t.Error("expected microbatch error")
	}
}

func TestScheduleTypes(t *testing.T) {
	if ScheduleGPipe != 0 || Schedule1F1B != 1 {
		t.Error("schedule constants")
	}
}

func TestDDPCreation(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	model := NewDistributedModel(newTestTensors(3), nil, nil)
	ddp, err := NewDDP(model, &DDPConfig{GradBucketCapMB: 1}, pg)
	if err != nil {
		t.Fatal(err)
	}
	if len(ddp.params) != 3 {
		t.Errorf("expected 3 params, got %d", len(ddp.params))
	}
	if len(ddp.buckets) == 0 {
		t.Error("expected gradient buckets")
	}
}

func TestDDPInvalidModel(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	if _, err := NewDDP(nil, nil, pg); err == nil {
		t.Error("expected nil model error")
	}
	model := NewDistributedModel(newTestTensors(1), nil, nil)
	if _, err := NewDDP(model, nil, nil); err == nil {
		t.Error("expected nil group error")
	}
}

func TestDDPBucketStats(t *testing.T) {
	pg := NewProcessGroup(0, 2, BackendGloo, newStore())
	model := NewDistributedModel(newTestTensors(5), nil, nil)
	ddp, _ := NewDDP(model, &DDPConfig{GradBucketCapMB: 1}, pg)
	stats := ddp.BucketStats()
	if len(stats) == 0 {
		t.Fatal("expected buckets")
	}
	total := 0
	for _, c := range stats {
		total += c
	}
	if total != 5 {
		t.Errorf("expected 5 params across buckets, got %d", total)
	}
}

func TestDDPTrainStep(t *testing.T) {
	// Use a single-rank group so the pass-through all-reduce works.
	pg := NewProcessGroup(0, 1, BackendGloo, newStore())
	forward := func(ctx context.Context, in *tensor.Tensor) (*tensor.Tensor, error) {
		return in, nil
	}
	model := NewDistributedModel(newTestTensors(2), forward, func(ctx context.Context, grad *tensor.Tensor) error {
		return nil
	})
	ddp, _ := NewDDP(model, &DDPConfig{GradBucketCapMB: 1}, pg)
	if err := ddp.TrainStep(context.Background(), passThroughTensor(1, 2), passThroughTensor(2)); err != nil {
		t.Fatal(err)
	}
	if ddp.syncStep.Load() < 1 {
		t.Error("expected a sync step")
	}
	if ddp.stats.TotalAllReduce.Load() < 1 {
		t.Error("expected at least one all-reduce")
	}
}

func TestRPCManager(t *testing.T) {
	m, err := NewRPCManager(nil, 0, 2)
	if err != nil {
		t.Fatal(err)
	}
	if err := m.Init(context.Background()); err != nil {
		t.Fatal(err)
	}
	defer m.Shutdown(context.Background())
	if err := m.RegisterMethod("ping", func(ctx context.Context, args ...interface{}) (interface{}, error) {
		return "pong", nil
	}); err != nil {
		t.Fatal(err)
	}
	if _, ok := m.GetMethod("ping"); !ok {
		t.Error("expected ping method")
	}
	m.RegisterEndpoint("w0", "localhost:9000", 0, "default")
	if _, err := m.GetEndpoint("w0"); err != nil {
		t.Fatal(err)
	}
	if _, err := m.GetEndpoint("missing"); err == nil {
		t.Error("expected endpoint error")
	}
}

func TestRPCCall(t *testing.T) {
	m, _ := NewRPCManager(nil, 0, 2)
	m.Init(context.Background())
	defer m.Shutdown(context.Background())
	m.RegisterMethod("ping", func(ctx context.Context, args ...interface{}) (interface{}, error) {
		return "pong", nil
	})
	m.RegisterEndpoint("self", "localhost:0", 0, "default")
	res, err := m.client.Call(context.Background(), "self", "ping")
	if err != nil {
		t.Fatal(err)
	}
	if res != "pong" {
		t.Errorf("got %v", res)
	}
}

func TestRPCTensorSerialize(t *testing.T) {
	rt := &RPCTensor{Data: []float64{1, 2, 3, 4}, Shape: []int{2, 2}}
	t2, err := rt.ToTensor()
	if err != nil {
		t.Fatal(err)
	}
	if len(t2.Shape().Dims()) != 2 {
		t.Error("shape")
	}
	data, err := SerializeTensor(t2)
	if err != nil {
		t.Fatal(err)
	}
	back, err := DeserializeTensor(data)
	if err != nil {
		t.Fatal(err)
	}
	if len(back.Float64()) != 4 {
		t.Error("roundtrip")
	}
}

func TestElasticAgent(t *testing.T) {
	pg := NewProcessGroup(0, 1, BackendGloo, newStore())
	model := NewDistributedModel(newTestTensors(1), nil, nil)
	ddp, err := NewDDP(model, nil, pg)
	if err != nil {
		t.Fatal(err)
	}
	ea := NewElasticAgent(ddp, 1, 4)
	if ea.minWorldSize != 1 {
		t.Error("elastic setup")
	}
	if err := ea.HandleFailure(context.Background(), 99); err != nil {
		t.Log("handle failure:", err)
	}
}

func TestFailureDetector(t *testing.T) {
	fd := NewFailureDetector(50 * time.Millisecond)
	fd.Heartbeat(0)
	fd.Heartbeat(1)
	if f := fd.CheckFailures(); len(f) != 0 {
		t.Errorf("expected no failures, got %v", f)
	}
	time.Sleep(60 * time.Millisecond)
	if len(fd.CheckFailures()) != 2 {
		t.Error("expected 2 failures after timeout")
	}
}
