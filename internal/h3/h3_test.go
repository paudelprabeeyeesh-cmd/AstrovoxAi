package h3

import (
	"testing"
)

func TestVarintRoundTrip(t *testing.T) {
	cases := []uint64{0, 1, 63, 64, 16383, 16384, 1073741823, 1073741824, 1 << 40}
	for _, v := range cases {
		b := varint(v)
		got, n, err := DecodeVarint(b)
		if err != nil {
			t.Fatalf("v=%d: %v", v, err)
		}
		if got != v || n != len(b) {
			t.Errorf("v=%d: got %d (%d bytes, want %d)", v, got, n, len(b))
		}
	}
}

func TestDecodeVarintTruncated(t *testing.T) {
	if _, _, err := DecodeVarint(nil); err != ErrTruncatedVarint {
		t.Errorf("expected truncated, got %v", err)
	}
	// Two-byte prefix but only one byte present.
	if _, _, err := DecodeVarint([]byte{0x40}); err != ErrTruncatedVarint {
		t.Errorf("expected truncated, got %v", err)
	}
}

func TestFrameEncodeDecode(t *testing.T) {
	f := DataFrame([]byte("payload"))
	b := f.Encode()
	got, n, err := DecodeFrame(b)
	if err != nil {
		t.Fatal(err)
	}
	if n != len(b) || got.Type != FrameData || string(got.Data) != "payload" {
		t.Errorf("frame: %+v (%d/%d)", got, n, len(b))
	}
}

func TestFrameMultiple(t *testing.T) {
	f1 := HeadersFrame([]byte{1, 2})
	f2 := DataFrame([]byte("body"))
	b := append(f1.Encode(), f2.Encode()...)

	got1, n1, err := DecodeFrame(b)
	if err != nil {
		t.Fatal(err)
	}
	if got1.Type != FrameHeaders {
		t.Error("first frame should be HEADERS")
	}
	got2, _, err := DecodeFrame(b[n1:])
	if err != nil {
		t.Fatal(err)
	}
	if got2.Type != FrameData {
		t.Error("second frame should be DATA")
	}
}

func TestDecodeFrameInvalid(t *testing.T) {
	if _, _, err := DecodeFrame(nil); err != ErrTruncatedVarint {
		t.Errorf("expected truncated, got %v", err)
	}
	// Type ok, length says 10 but only 2 bytes follow.
	bad := append(varint(FrameData), varint(10)...)
	bad = append(bad, 1, 2)
	if _, _, err := DecodeFrame(bad); err != ErrInvalidFrame {
		t.Errorf("expected invalid frame, got %v", err)
	}
}

func TestFrameTypeNames(t *testing.T) {
	if FrameTypeName(FrameData) != "DATA" || FrameTypeName(FrameSettings) != "SETTINGS" {
		t.Error("frame type names")
	}
	if FrameTypeName(0xFF) != "UNKNOWN(0xff)" {
		t.Errorf("got %s", FrameTypeName(0xFF))
	}
}

func TestSettingsFrames(t *testing.T) {
	f := SettingsFrame(DefaultSettings())
	if f.Type != FrameSettings {
		t.Error("type")
	}
	// Two varints per setting.
	if len(f.Data) == 0 {
		t.Error("expected settings payload")
	}
}

func TestGoAwayFrame(t *testing.T) {
	f := GoAwayFrame(7)
	got, n, err := DecodeFrame(f.Encode())
	if err != nil {
		t.Fatal(err)
	}
	if n == 0 || got.Type != FrameGoAway {
		t.Error("goaway frame")
	}
}

func TestQPACKEncodeDecodeLiteral(t *testing.T) {
	enc := &QPACKEncoder{}
	// A non-static header must use the literal form.
	out := enc.Encode([]HeaderField{{"x-custom", "value"}})
	if len(out) == 0 {
		t.Fatal("expected encoded output")
	}
	if out[0] != 0x20 {
		t.Errorf("expected literal field line 0x20, got %#x", out[0])
	}
}

func TestQPACKStaticIndexing(t *testing.T) {
	enc := &QPACKEncoder{}
	out := enc.Encode([]HeaderField{{MethodPseudo, "GET"}})
	// Indexed field line: one byte 0x80|17 == 0x91.
	if len(out) != 1 || out[0] != 0x91 {
		t.Errorf("expected static index byte, got %#x (%d bytes)", out, len(out))
	}
}

func TestQPACKStaticIndexValues(t *testing.T) {
	for _, tc := range []struct{ name, value string }{
		{MethodPseudo, "GET"}, {MethodPseudo, "POST"},
		{PathPseudo, "/"}, {SchemePseudo, "https"},
		{StatusPseudo, "200"}, {StatusPseudo, "404"},
	} {
		if _, ok := staticIndex(tc.name, tc.value); !ok {
			t.Errorf("%s: %s should be in the static subset", tc.name, tc.value)
		}
	}
	if _, ok := staticIndex(MethodPseudo, "DELETE"); ok {
		t.Error("DELETE is not in the subset")
	}
}

func TestRequestEncode(t *testing.T) {
	req := &Request{
		Method: "POST", Scheme: "https", Authority: "api.example.com", Path: "/v1/predict",
		Headers:  []HeaderField{{"content-type", "application/json"}},
		Body:     []byte(`{"x":1}`),
		StreamID: 4,
	}
	frames := req.Encode()
	if len(frames) != 2 {
		t.Fatalf("expected HEADERS + DATA, got %d frames", len(frames))
	}
	if frames[0].Type != FrameHeaders || frames[1].Type != FrameData {
		t.Error("frame order")
	}
}

func TestRequestFields(t *testing.T) {
	r := &Request{Method: "GET", Scheme: "https", Authority: "h", Path: "/p"}
	r.Headers = []HeaderField{{"a", "b"}}
	fields := r.Fields()
	if len(fields) != 5 || fields[0].Name != MethodPseudo || fields[4].Name != "a" {
		t.Errorf("fields: %+v", fields)
	}
}

func TestResponseEncode(t *testing.T) {
	res := &Response{Status: "200", Body: []byte("hi"), StreamID: 8}
	frames := res.Encode()
	if len(frames) != 2 || frames[0].Type != FrameHeaders {
		t.Fatal("response frames")
	}
}

func TestClientSend(t *testing.T) {
	fw := &fakeWriter{}
	c, err := NewClient(fw)
	if err != nil {
		t.Fatal(err)
	}
	if err := c.Send(&Request{Method: "GET", Scheme: "https", Authority: "h", Path: "/", StreamID: 0}); err != nil {
		t.Log("stream id 0 accepted")
	}
	if err := c.Send(&Request{Method: "GET", Scheme: "https", Authority: "h", Path: "/", StreamID: 2}); err != nil {
		t.Fatal(err)
	}
	if fw.frames != 1 {
		t.Errorf("expected 1 frame written, got %d", fw.frames)
	}
	if c.Send(nil) == nil {
		t.Error("expected nil request error")
	}
}

func TestNewClientNilWriter(t *testing.T) {
	if _, err := NewClient(nil); err == nil {
		t.Error("expected nil writer error")
	}
}

type fakeWriter struct {
	frames int
	last   Frame
}

func (f *fakeWriter) WriteFrame(streamID uint64, frame Frame) error {
	f.frames++
	f.last = frame
	return nil
}
