// Package h3 implements HTTP/3 semantics on top of a QUIC-style transport:
// frame types, QPACK-style header encoding, and request/response messages.
package h3

import (
	"errors"
	"fmt"
	"strings"
)

// HTTP/3 unidirectional stream types.
const (
	StreamTypeControl      uint64 = 0x00
	StreamTypePush         uint64 = 0x01
	StreamTypeQPACKEncoder uint64 = 0x02
	// StreamTypeQPACKDecoder names the QPACK decoder stream.
	StreamTypeQPACKDecoder uint64 = 0x03
)

// HTTP/3 frame types (RFC 9114).
const (
	FrameData        uint64 = 0x00
	FrameHeaders     uint64 = 0x01
	FrameCancelPush  uint64 = 0x03
	FrameSettings    uint64 = 0x04
	FramePushPromise uint64 = 0x05
	FrameGoAway      uint64 = 0x07
	FrameMaxPushID   uint64 = 0x0D
)

// FrameTypeName renders a frame type.
func FrameTypeName(t uint64) string {
	switch t {
	case FrameData:
		return "DATA"
	case FrameHeaders:
		return "HEADERS"
	case FrameCancelPush:
		return "CANCEL_PUSH"
	case FrameSettings:
		return "SETTINGS"
	case FramePushPromise:
		return "PUSH_PROMISE"
	case FrameGoAway:
		return "GOAWAY"
	case FrameMaxPushID:
		return "MAX_PUSH_ID"
	default:
		return fmt.Sprintf("UNKNOWN(0x%x)", t)
	}
}

// HTTP/3 settings identifiers (RFC 9114).
const (
	SettingQPACKMaxTableCapacity uint64 = 0x01
	SettingMaxFieldSectionSize   uint64 = 0x06
	SettingQPACKBlockedStreams   uint64 = 0x07
)

// Setting is an HTTP/3 setting.
type Setting struct {
	ID    uint64
	Value uint64
}

// DefaultSettings returns the default HTTP/3 settings.
func DefaultSettings() []Setting {
	return []Setting{
		{SettingQPACKMaxTableCapacity, 4096},
		{SettingMaxFieldSectionSize, 16384},
		{SettingQPACKBlockedStreams, 100},
	}
}

// Frame is an HTTP/3 frame.
type Frame struct {
	Type uint64
	Data []byte
}

// Encode writes a frame to bytes.
func (f Frame) Encode() []byte {
	out := varint(f.Type)
	out = append(out, varint(uint64(len(f.Data)))...)
	return append(out, f.Data...)
}

// HeadersFrame builds a HEADERS frame from encoded header fields.
func HeadersFrame(encoded []byte) Frame {
	return Frame{Type: FrameHeaders, Data: encoded}
}

// DataFrame builds a DATA frame.
func DataFrame(p []byte) Frame { return Frame{Type: FrameData, Data: p} }

// SettingsFrame builds a SETTINGS frame.
func SettingsFrame(settings []Setting) Frame {
	var d []byte
	for _, s := range settings {
		d = append(d, varint(s.ID)...)
		d = append(d, varint(s.Value)...)
	}
	return Frame{Type: FrameSettings, Data: d}
}

// GoAwayFrame builds a GOAWAY frame carrying a stream id.
func GoAwayFrame(streamID uint64) Frame {
	return Frame{Type: FrameGoAway, Data: varint(streamID)}
}

// HeaderField is one name/value header pair.
type HeaderField struct {
	Name  string
	Value string
}

// PseudoHeaders are mandatory HTTP/3 request pseudo-headers.
const (
	MethodPseudo    = ":method"
	SchemePseudo    = ":scheme"
	AuthorityPseudo = ":authority"
	PathPseudo      = ":path"
	StatusPseudo    = ":status"
)

// QPACKEncoder performs literal-only header encoding (a valid subset of
// QPACK: no dynamic table, always indexed=0).
type QPACKEncoder struct{}

// EncodeField writes a literal header field with a literal name.
func (e *QPACKEncoder) EncodeField(name, value string) []byte {
	var out []byte
	// 0x20 = literal field line, literal name, no Huffman.
	out = append(out, 0x20)
	out = append(out, lenPrefixed(name)...)
	out = append(out, lenPrefixed(value)...)
	return out
}

// Encode encodes a full header field list.
func (e *QPACKEncoder) Encode(fields []HeaderField) []byte {
	var out []byte
	for _, f := range fields {
		if strings.HasPrefix(f.Name, ":") {
			// Common pseudo-headers use the static-table indexed form.
			if idx, ok := staticIndex(f.Name, f.Value); ok {
				out = append(out, indexedFieldLine(idx)...)
				continue
			}
		}
		out = append(out, e.EncodeField(f.Name, f.Value)...)
	}
	return out
}

// lenPrefixed encodes a string with a 7-bit-prefixed length.
func lenPrefixed(s string) []byte {
	n := len(s)
	if n < 127 {
		return append([]byte{byte(n)}, s...)
	}
	out := []byte{0x7F, byte(n >> 24), byte(n >> 16), byte(n >> 8), byte(n)}
	return append(out, s...)
}

// staticIndex maps common header pairs to a small hand-picked subset of the
// QPACK static table.
func staticIndex(name, value string) (uint64, bool) {
	switch name {
	case MethodPseudo:
		switch value {
		case "GET":
			return 17, true
		case "POST":
			return 20, true
		}
	case PathPseudo:
		if value == "/" {
			return 1, true
		}
	case SchemePseudo:
		if value == "https" {
			return 23, true
		}
	case StatusPseudo:
		switch value {
		case "200":
			return 63, true
		case "404":
			return 67, true
		}
	}
	return 0, false
}

// Request is an HTTP/3 request.
type Request struct {
	Method    string
	Scheme    string
	Authority string
	Path      string
	Headers   []HeaderField
	Body      []byte
	StreamID  uint64
}

// Fields returns the full ordered header field list.
func (r *Request) Fields() []HeaderField {
	fields := []HeaderField{
		{MethodPseudo, r.Method},
		{SchemePseudo, r.Scheme},
		{AuthorityPseudo, r.Authority},
		{PathPseudo, r.Path},
	}
	return append(fields, r.Headers...)
}

// Encode writes the request as HEADERS + DATA frames.
func (r *Request) Encode() []Frame {
	enc := &QPACKEncoder{}
	frames := []Frame{HeadersFrame(enc.Encode(r.Fields()))}
	if len(r.Body) > 0 {
		frames = append(frames, DataFrame(r.Body))
	}
	return frames
}

// Response is an HTTP/3 response.
type Response struct {
	Status   string
	Headers  []HeaderField
	Body     []byte
	StreamID uint64
}

// Fields returns the response header fields.
func (r *Response) Fields() []HeaderField {
	fields := []HeaderField{{StatusPseudo, r.Status}}
	return append(fields, r.Headers...)
}

// Encode writes the response as HEADERS + DATA frames.
func (r *Response) Encode() []Frame {
	enc := &QPACKEncoder{}
	frames := []Frame{HeadersFrame(enc.Encode(r.Fields()))}
	if len(r.Body) > 0 {
		frames = append(frames, DataFrame(r.Body))
	}
	return frames
}

// Errors.
var (
	ErrTruncatedVarint = errors.New("truncated varint")
	ErrInvalidFrame    = errors.New("invalid http/3 frame")
)

// varint encodes a QUIC variable-length integer (RFC 9000 14.1).
func varint(v uint64) []byte {
	switch {
	case v <= 63:
		return []byte{byte(v)}
	case v <= 16383:
		return []byte{byte(v>>8) | 0x40, byte(v)}
	case v <= 1073741823:
		return []byte{byte(v>>24) | 0x80, byte(v >> 16), byte(v >> 8), byte(v)}
	default:
		return []byte{
			0xC0 | byte(v>>56),
			byte(v >> 48), byte(v >> 40), byte(v >> 32),
			byte(v >> 24), byte(v >> 16), byte(v >> 8), byte(v),
		}
	}
}

// DecodeVarint decodes a variable-length integer, returning the value and
// the number of bytes consumed.
func DecodeVarint(b []byte) (uint64, int, error) {
	if len(b) == 0 {
		return 0, 0, ErrTruncatedVarint
	}
	prefix := b[0] >> 6
	switch prefix {
	case 0:
		return uint64(b[0] & 0x3F), 1, nil
	case 1:
		if len(b) < 2 {
			return 0, 0, ErrTruncatedVarint
		}
		return uint64(b[0]&0x3F)<<8 | uint64(b[1]), 2, nil
	case 2:
		if len(b) < 4 {
			return 0, 0, ErrTruncatedVarint
		}
		return uint64(b[0]&0x3F)<<24 | uint64(b[1])<<16 | uint64(b[2])<<8 | uint64(b[3]), 4, nil
	default:
		if len(b) < 8 {
			return 0, 0, ErrTruncatedVarint
		}
		v := uint64(b[0]&0x3F) << 56
		for i := 1; i < 8; i++ {
			v = v<<8 | uint64(b[i])
		}
		return v, 8, nil
	}
}

// indexedFieldLine encodes a QPACK indexed field line (the "1" prefix bit
// followed by a 7-bit-prefixed index), per RFC 9204 4.5.4.
func indexedFieldLine(idx uint64) []byte {
	if idx < 127 {
		return []byte{0x80 | byte(idx)}
	}
	// Long form: 1NNNNNNN with the remaining index in the continuation bytes.
	out := []byte{0xFF}
	v := idx - 127
	for v >= 128 {
		out = append(out, byte(v)|0x80)
		v >>= 7
	}
	return append(out, byte(v))
}

// DecodeFrame decodes one frame from a byte slice.
func DecodeFrame(b []byte) (Frame, int, error) {
	typ, n1, err := DecodeVarint(b)
	if err != nil {
		return Frame{}, 0, err
	}
	b = b[n1:]
	length, n2, err := DecodeVarint(b)
	if err != nil {
		return Frame{}, 0, err
	}
	b = b[n2:]
	if uint64(len(b)) < length {
		return Frame{}, 0, ErrInvalidFrame
	}
	return Frame{Type: typ, Data: b[:length]}, n1 + n2 + int(length), nil
}

// StreamWriter is the sink a transport provides for HTTP/3 frames.
type StreamWriter interface {
	WriteFrame(streamID uint64, f Frame) error
}

// Client sends HTTP/3 requests over a StreamWriter.
type Client struct {
	writer StreamWriter
}

// NewClient creates an HTTP/3 client over writer.
func NewClient(w StreamWriter) (*Client, error) {
	if w == nil {
		return nil, errors.New("nil stream writer")
	}
	return &Client{writer: w}, nil
}

// Send encodes and writes a request's frames.
func (c *Client) Send(r *Request) error {
	if r == nil {
		return errors.New("nil request")
	}
	if r.StreamID == 0 {
		return errors.New("request stream id must be set")
	}
	for _, f := range r.Encode() {
		if err := c.writer.WriteFrame(r.StreamID, f); err != nil {
			return err
		}
	}
	return nil
}

// SendResponse encodes and writes a response's frames.
func (c *Client) SendResponse(r *Response) error {
	if r == nil {
		return errors.New("nil response")
	}
	for _, f := range r.Encode() {
		if err := c.writer.WriteFrame(r.StreamID, f); err != nil {
			return err
		}
	}
	return nil
}
