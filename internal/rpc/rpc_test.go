package rpc

import (
	"bytes"
	"io"
	"testing"
)

func testService() (ServiceDescriptor, ServiceImpl) {
	return ServiceDescriptor{
			Name: "Echo",
			Methods: []MethodDescriptor{
				{Name: "Ping"},
				{Name: "Stream"},
			},
		}, &echoService{}
}

type echoService struct{}

func (e *echoService) Unary(method string, req *Message) (*Message, error) {
	switch method {
	case "Ping":
		return NewMessage().Set("pong", true), nil
	default:
		return nil, ErrMethodNotFound
	}
}

func (e *echoService) ServerStream(method string, req *Message, send func(*Message) error) error {
	if method != "Stream" {
		return ErrMethodNotFound
	}
	n := req.GetInt("n")
	for i := 0; i < n; i++ {
		if err := send(NewMessage().Set("i", i)); err != nil {
			return err
		}
	}
	return nil
}

func TestServerRegisterAndInvoke(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	if err := s.RegisterService(desc, impl); err != nil {
		t.Fatal(err)
	}
	if err := s.Start(); err != nil {
		t.Fatal(err)
	}
	defer s.Stop()

	resp, err := s.Invoke("Echo.Ping", NewMessage())
	if err != nil {
		t.Fatal(err)
	}
	if resp.Get("pong") != true {
		t.Error("expected pong")
	}
	if got := s.Stats().Requests.Load(); got != 1 {
		t.Errorf("expected 1 request, got %d", got)
	}
}

func TestServerDuplicateRegistration(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	s.RegisterService(desc, impl)
	if err := s.RegisterService(desc, impl); err == nil {
		t.Error("expected duplicate registration error")
	}
}

func TestServerNotStarted(t *testing.T) {
	s := NewServer()
	if _, err := s.Invoke("Echo.Ping", NewMessage()); err == nil {
		t.Error("expected not started error")
	}
}

func TestServerUnknownService(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	s.RegisterService(desc, impl)
	s.Start()
	defer s.Stop()
	if _, err := s.Invoke("Ghost.Ping", NewMessage()); err == nil {
		t.Error("expected unknown service error")
	}
}

func TestServerStream(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	s.RegisterService(desc, impl)
	s.Start()
	defer s.Stop()

	var got []int
	err := s.InvokeServerStream("Echo.Stream", NewMessage().Set("n", 3), func(m *Message) error {
		got = append(got, m.GetInt("i"))
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 3 || got[0] != 0 || got[2] != 2 {
		t.Errorf("unexpected stream %v", got)
	}
}

func TestServerServices(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	s.RegisterService(desc, impl)
	if len(s.Services()) != 1 {
		t.Errorf("expected 1 service, got %v", s.Services())
	}
}

func TestClientCall(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	s.RegisterService(desc, impl)
	s.Start()
	defer s.Stop()

	c := NewClient("inproc://test", s)
	resp, err := c.Call("Echo.Ping", NewMessage())
	if err != nil {
		t.Fatal(err)
	}
	if resp.Get("pong") != true {
		t.Error("expected pong")
	}
	if c.Stats().Sent.Load() != 1 {
		t.Error("client stats")
	}
	if c.Conn() != "inproc://test" {
		t.Error("conn")
	}
}

func TestClientWithTimeout(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	s.RegisterService(desc, impl)
	s.Start()
	defer s.Stop()
	c := NewClient("x", s, WithTimeout(1))
	if c.Timeout() != 1 {
		t.Errorf("expected 1ns, got %v", c.Timeout())
	}
}

func TestClientUnknownMethod(t *testing.T) {
	s := NewServer()
	desc, impl := testService()
	s.RegisterService(desc, impl)
	s.Start()
	defer s.Stop()
	c := NewClient("x", s)
	if _, err := c.Call("Echo.Nope", NewMessage()); err == nil {
		t.Error("expected method error")
	}
}

func TestFrameRoundTrip(t *testing.T) {
	var buf bytes.Buffer
	f := Frame{Data: []byte("hello grpc")}
	if err := WriteFrame(&buf, f); err != nil {
		t.Fatal(err)
	}
	got, err := ReadFrame(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if got.Compressed || string(got.Data) != "hello grpc" {
		t.Errorf("frame mismatch: %+v", got)
	}
}

func TestFrameLargePayload(t *testing.T) {
	var buf bytes.Buffer
	payload := make([]byte, 200000)
	for i := range payload {
		payload[i] = byte(i % 251)
	}
	if err := WriteFrame(&buf, Frame{Data: payload}); err != nil {
		t.Fatal(err)
	}
	got, err := ReadFrame(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Data) != len(payload) {
		t.Errorf("expected %d bytes, got %d", len(payload), len(got.Data))
	}
}

func TestMessage(t *testing.T) {
	m := NewMessage().Set("key", "value").Set("n", 3)
	if m.GetString("key") != "value" {
		t.Error("string field")
	}
	if m.GetInt("n") != 3 {
		t.Error("int field")
	}
	if m.Get("missing") != nil {
		t.Error("missing field should be nil")
	}
}

func TestMethodDescriptorStreaming(t *testing.T) {
	m := MethodDescriptor{Name: "x", ServerStreaming: true}
	if !m.IsStreaming() {
		t.Error("expected streaming")
	}
	if (MethodDescriptor{Name: "y"}).IsStreaming() {
		t.Error("unary should not stream")
	}
}

func TestParamServerPushPull(t *testing.T) {
	s := NewServer()
	ps := NewParamServerImplement()
	s.RegisterService(ServiceDescriptor{
		Name: "ParamServer",
		Methods: []MethodDescriptor{{Name: "Push"}, {Name: "Pull"}},
	}, ps)
	s.Start()
	defer s.Stop()

	if _, err := s.Invoke("ParamServer.Push", NewMessage().Set("key", "w").Set("values", []float64{1, 2, 3})); err != nil {
		t.Fatal(err)
	}
	resp, err := s.Invoke("ParamServer.Pull", NewMessage().Set("key", "w"))
	if err != nil {
		t.Fatal(err)
	}
	vals := toFloats(resp.Fields["values"])
	if len(vals) != 3 || vals[0] != 1 {
		t.Errorf("got %v", vals)
	}
	if len(ps.Keys()) != 1 {
		t.Errorf("expected 1 key, got %v", ps.Keys())
	}
	if ps.Stats().Pushes.Load() != 1 {
		t.Error("push stat")
	}
}

func TestParamServerUnknownMethod(t *testing.T) {
	ps := NewParamServerImplement()
	if _, err := ps.Unary("Nope", NewMessage()); err == nil {
		t.Error("expected unknown method error")
	}
}

func TestReadFrameEOF(t *testing.T) {
	_, err := ReadFrame(bytes.NewReader(nil))
	if err != io.EOF {
		t.Errorf("expected EOF, got %v", err)
	}
}