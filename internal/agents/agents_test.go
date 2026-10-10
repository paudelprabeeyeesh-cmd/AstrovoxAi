package agents

import (
	"context"
	"testing"
)

type fakeLLM struct {
	replies []string
	i       int
}

func (f *fakeLLM) Complete(ctx context.Context, prompt string) (string, error) {
	if f.i < len(f.replies) {
		r := f.replies[f.i]
		f.i++
		return r, nil
	}
	return "APPROVED: " + prompt, nil
}

func TestToolRegistryRegister(t *testing.T) {
	r := NewToolRegistry()
	err := r.Register(NewToolFunc("t", "d", "s", func(ctx context.Context, args map[string]interface{}) (interface{}, error) {
		return "ok", nil
	}))
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := r.Get("t"); !ok {
		t.Error("expected tool t")
	}
	if r.Register(nil) == nil {
		t.Error("expected error for nil tool")
	}
}

func TestToolExecute(t *testing.T) {
	r := NewToolRegistry()
	r.Register(NewToolFunc("add", "adds", "a,b", func(ctx context.Context, args map[string]interface{}) (interface{}, error) {
		a, _ := args["a"].(float64)
		b, _ := args["b"].(float64)
		return a + b, nil
	}))
	tool, _ := r.Get("add")
	res, err := tool.Execute(context.Background(), map[string]interface{}{"a": 2.0, "b": 3.0})
	if err != nil {
		t.Fatal(err)
	}
	if res != 5.0 {
		t.Errorf("expected 5, got %v", res)
	}
}

func TestToolRegistryList(t *testing.T) {
	r := NewToolRegistry()
	mk := func(n string) Tool { return NewToolFunc(n, "", "", nil) }
	r.Register(mk("b"))
	r.Register(mk("a"))
	names := r.List()
	if len(names) != 2 || names[0] != "a" || names[1] != "b" {
		t.Errorf("expected sorted names, got %v", names)
	}
}

func TestAgentMemoryAdd(t *testing.T) {
	m := NewAgentMemory(3)
	for i := 0; i < 10; i++ {
		m.Add(MemoryEntry{Content: "x", Score: float64(i)})
	}
	if m.Size() != 3 {
		t.Errorf("expected bounded size 3, got %d", m.Size())
	}
}

func TestAgentMemoryRecall(t *testing.T) {
	m := NewAgentMemory(10)
	m.Add(MemoryEntry{Content: "the cat sat"})
	m.Add(MemoryEntry{Content: "a dog ran"})
	got := m.Recall("cat", 5)
	if len(got) != 2 {
		t.Fatalf("expected 2, got %d", len(got))
	}
	if got[0].Content != "the cat sat" {
		t.Errorf("expected best match first, got %q", got[0].Content)
	}
}

func TestAgentMemoryClear(t *testing.T) {
	m := NewAgentMemory(5)
	m.Add(MemoryEntry{Content: "x"})
	m.Clear()
	if m.Size() != 0 {
		t.Error("expected cleared")
	}
}

func TestAgentStep(t *testing.T) {
	a := NewAgent("tester", RoleGeneric, "goal", "sys", &fakeLLM{replies: []string{"think"}}, nil, 5)
	out, err := a.Step(context.Background(), "observation")
	if err != nil {
		t.Fatal(err)
	}
	if out != "think" {
		t.Errorf("expected think, got %s", out)
	}
	stats := a.Stats()
	if stats.Steps.Load() != 1 {
		t.Error("expected 1 step")
	}
}
func TestAgentNoLLM(t *testing.T) {
	a := NewAgent("x", RoleGeneric, "", "", nil, nil, 1)
	if _, err := a.Step(context.Background(), "obs"); err == nil {
		t.Error("expected error without LLM")
	}
}

func TestAgentRunTool(t *testing.T) {
	a := NewAgent("x", RoleGeneric, "", "", &fakeLLM{}, nil, 1)
	a.AddTool(NewToolFunc("echo", "", "", func(ctx context.Context, args map[string]interface{}) (interface{}, error) {
		return args["msg"], nil
	}))
	res, err := a.RunTool(context.Background(), "echo", map[string]interface{}{"msg": "hi"})
	if err != nil {
		t.Fatal(err)
	}
	if res != "hi" {
		t.Errorf("expected hi, got %v", res)
	}
}

func TestAgentRunToolMissing(t *testing.T) {
	a := NewAgent("x", RoleGeneric, "", "", &fakeLLM{}, nil, 1)
	if _, err := a.RunTool(context.Background(), "nope", nil); err == nil {
		t.Error("expected missing tool error")
	}
}

func TestOrchestratorRegisterRun(t *testing.T) {
	o := NewOrchestrator(3)
	planner := NewAgent("planner", RolePlanner, "plan", "sys", &fakeLLM{replies: []string{"step1", "APPROVED plan"}}, nil, 2)
	o.RegisterAgent(planner)
	o.SetWorkflow([]WorkflowStep{{AgentName: "planner"}})
	out, err := o.Run(context.Background(), "build")
	if err != nil {
		t.Fatal(err)
	}
	if out == "" {
		t.Error("expected output")
	}
}

func TestOrchestratorMissingAgent(t *testing.T) {
	o := NewOrchestrator(1)
	o.SetWorkflow([]WorkflowStep{{AgentName: "ghost"}})
	if _, err := o.Run(context.Background(), "x"); err == nil {
		t.Error("expected missing agent error")
	}
}

func TestOrchestratorRunParallel(t *testing.T) {
	o := NewOrchestrator(1)
	o.RegisterAgent(NewAgent("a", RoleGeneric, "", "sys", &fakeLLM{replies: []string{"A"}}, nil, 1))
	o.RegisterAgent(NewAgent("b", RoleGeneric, "", "sys", &fakeLLM{replies: []string{"B"}}, nil, 1))
	res, err := o.RunParallel(context.Background(), "task")
	if err != nil {
		t.Fatal(err)
	}
	if len(res) != 2 {
		t.Errorf("expected 2 results, got %d", len(res))
	}
}

func TestOrchestratorRegisterInvalid(t *testing.T) {
	o := NewOrchestrator(1)
	if o.RegisterAgent(nil) == nil {
		t.Error("expected error for nil agent")
	}
}

func TestOrchestratorAgents(t *testing.T) {
	o := NewOrchestrator(1)
	o.RegisterAgent(NewAgent("b", RoleGeneric, "", "", &fakeLLM{}, nil, 1))
	o.RegisterAgent(NewAgent("a", RoleGeneric, "", "", &fakeLLM{}, nil, 1))
	names := o.Agents()
	if len(names) != 2 || names[0] != "a" {
		t.Errorf("expected sorted names, got %v", names)
	}
}

func TestAgentRoleString(t *testing.T) {
	if RolePlanner.String() != "planner" {
		t.Error("planner")
	}
	if RoleExecutor.String() != "executor" {
		t.Error("executor")
	}
}

func TestAgentMemoryEvictsOldest(t *testing.T) {
	m := NewAgentMemory(2)
	m.Add(MemoryEntry{Content: "keep", Score: 5})
	m.Add(MemoryEntry{Content: "keep2", Score: 5})
	m.Add(MemoryEntry{Content: "low", Score: 1})
	got := m.Recall("keep", 10)
	for _, e := range got {
		if e.Content == "low" {
			t.Error("low-score entry should have been evicted")
		}
	}
}

func TestOrchestratorAddTool(t *testing.T) {
	o := NewOrchestrator(1)
	o.AddTool(NewToolFunc("x", "", "", nil))
	if len(o.tools.List()) != 1 {
		t.Error("expected 1 tool")
	}
}

func TestFakeLLMFallback(t *testing.T) {
	f := &fakeLLM{}
	out, _ := f.Complete(context.Background(), "p")
	if out != "APPROVED: p" {
		t.Errorf("unexpected fallback %q", out)
	}
}
