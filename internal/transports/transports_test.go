package transports

import (
	"bytes"
	"net"
	"testing"
)

func TestWSFrameRoundTrip(t *testing.T) {
	var buf bytes.Buffer
	f := WSFrame{Fin: true, Opcode: OpText, Payload: []byte("hello")}
	if err := WriteWFrame(&buf, f); err != nil {
		t.Fatal(err)
	}
	got, err := ReadWFrame(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if !got.Fin || got.Opcode != OpText || string(got.Payload) != "hello" {
		t.Errorf("frame: %+v", got)
	}
}

func TestWSFrameLargePayload(t *testing.T) {
	var buf bytes.Buffer
	payload := make([]byte, 70000)
	for i := range payload {
		payload[i] = byte(i % 251)
	}
	if err := WriteWFrame(&buf, WSFrame{Fin: true, Payload: payload}); err != nil {
		t.Fatal(err)
	}
	got, err := ReadWFrame(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got.Payload, payload) {
		t.Error("large payload mismatch")
	}
}

func TestWSFrameEmpty(t *testing.T) {
	var buf bytes.Buffer
	if err := WriteWFrame(&buf, WSFrame{Fin: true, Opcode: OpPing}); err != nil {
		t.Fatal(err)
	}
	got, err := ReadWFrame(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Payload) != 0 || got.Opcode != OpPing {
		t.Errorf("frame: %+v", got)
	}
}

func TestWSFrameOpcodes(t *testing.T) {
	if OpText != 0x1 || OpBinary != 0x2 || OpClose != 0x8 || OpPing != 0x9 || OpPong != 0xA {
		t.Error("opcode values")
	}
}

func TestComputeAcceptKey(t *testing.T) {
	// RFC 6455 example key.
	got := ComputeAcceptKey("dGhlIHNhbXBsZSBub25jZQ==")
	want := "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
	if got != want {
		t.Errorf("got %s, want %s", got, want)
	}
}

func TestIsValidHandshake(t *testing.T) {
	ok := []string{
		"GET /chat HTTP/1.1",
		"Host: x",
		"Upgrade: websocket",
		"Connection: Upgrade",
		"Sec-WebSocket-Key: abc",
	}
	if !IsValidHandshake(ok) {
		t.Error("expected valid handshake")
	}
	if IsValidHandshake([]string{"Upgrade: h2c"}) {
		t.Error("non-websocket upgrade should be invalid")
	}
}

func TestHandshakeMessages(t *testing.T) {
	req := HandshakeRequest("host", "/path", "key123")
	if !bytes.Contains(req, []byte("Upgrade: websocket")) {
		t.Error("request should upgrade")
	}
	resp := HandshakeResponse("key123")
	if !bytes.Contains(resp, []byte("101 Switching Protocols")) {
		t.Error("response should switch protocols")
	}
}

func TestMaxFrameSizeGuard(t *testing.T) {
	old := MaxFrameSize
	MaxFrameSize = 10
	defer func() { MaxFrameSize = old }()
	var buf bytes.Buffer
	buf.Write([]byte{0x81, 20}) // fin+text, unmasked length 20
	if _, err := ReadWFrame(&buf); err != ErrFrameTooBig {
		t.Errorf("expected frame too big, got %v", err)
	}
}

func TestMuxStreamRoundTrip(t *testing.T) {
	c1, c2 := net.Pipe()
	defer c1.Close()
	defer c2.Close()

	m := NewMuxStream(c1)
	receiver := NewMuxStream(c2)

	// Send from a goroutine, then verify the frame arrives and stats update.
	done := make(chan error, 1)
	go func() {
		err := m.Send(7, []byte("ping"))
		done <- err
	}()

	id, payload, err := receiver.Recv()
	if err != nil {
		t.Fatal(err)
	}
	if id != 7 || string(payload) != "ping" {
		t.Errorf("got id=%d payload=%q", id, payload)
	}
	if err := <-done; err != nil {
		t.Fatal(err)
	}
	if m.Stats().FramesSent.Load() != 1 {
		t.Error("send stat")
	}
	if receiver.Stats().Frames.Load() != 1 {
		t.Error("recv stat")
	}
}

func TestMuxStreamIDs(t *testing.T) {
	c1, _ := net.Pipe()
	defer c1.Close()
	m := NewMuxStream(c1)
	if a, b := m.NextStreamID(), m.NextStreamID(); a == b {
		t.Error("stream ids must be unique")
	}
}

func TestMuxStreamClosed(t *testing.T) {
	c1, _ := net.Pipe()
	c1.Close()
	m := NewMuxStream(c1)
	if _, _, err := m.Recv(); err == nil {
		t.Error("expected error on closed connection")
	}
}

func TestQUICPacketRoundTrip(t *testing.T) {
	p := QUICPacket{
		Version:    0x00000001,
		DestConnID: []byte{1, 2, 3, 4},
		SrcConnID:  []byte{5, 6},
		Token:      []byte{0xAA},
		Payload:    []byte("hello quic"),
	}
	b := EncodeQUICPacket(p)
	got, err := DecodeQUICPacket(b)
	if err != nil {
		t.Fatal(err)
	}
	if got.Version != p.Version || string(got.Payload) != "hello quic" {
		t.Errorf("packet: %+v", got)
	}
	if len(got.DestConnID) != 4 || len(got.Token) != 1 {
		t.Error("connection ids")
	}
}

func TestQUICPacketTruncated(t *testing.T) {
	if _, err := DecodeQUICPacket([]byte{0x00}); err == nil {
		t.Error("expected not-long-header error")
	}
	if _, err := DecodeQUICPacket([]byte{0xC0, 0, 0, 0, 1, 1}); err == nil {
		t.Error("expected truncation error")
	}
}

func TestUDPEndpoint(t *testing.T) {
	// Bind two loopback UDP sockets and exchange a datagram.
	pc, err := net.ListenPacket("udp", "127.0.0.1:0")
	if err != nil {
		t.Skip("udp unavailable")
	}
	defer pc.Close()
	addr := pc.LocalAddr().String()

	sender, err := net.Dial("udp", addr)
	if err != nil {
		t.Skip("udp unavailable")
	}
	defer sender.Close()

	if _, err := sender.Write([]byte("hello udp")); err != nil {
		t.Fatal(err)
	}
	buf := make([]byte, 64)
	n, _, err := pc.ReadFrom(buf)
	if err != nil {
		t.Fatal(err)
	}
	if string(buf[:n]) != "hello udp" {
		t.Errorf("got %q", string(buf[:n]))
	}
}

func TestUDPStatsAndClose(t *testing.T) {
	e, err := ListenUDP("127.0.0.1:0", 1024)
	if err != nil {
		t.Skip("udp unavailable")
	}
	if err := e.Close(); err != nil {
		t.Fatal(err)
	}
	// Double close is a no-op.
	if err := e.Close(); err != nil {
		t.Errorf("double close: %v", err)
	}
	if err := e.SendTo([]byte("x"), "127.0.0.1:1"); err != ErrNotConnected {
		t.Errorf("expected not connected, got %v", err)
	}
	if _, _, err := e.RecvFrom(); err != ErrNotConnected {
		t.Errorf("expected not connected, got %v", err)
	}
}

func TestUDPOversized(t *testing.T) {
	e, err := ListenUDP("127.0.0.1:0", 8)
	if err != nil {
		t.Skip("udp unavailable")
	}
	defer e.Close()
	if err := e.SendTo(make([]byte, 100), "127.0.0.1:1"); err != ErrFrameTooBig {
		t.Errorf("expected frame too big, got %v", err)
	}
}
