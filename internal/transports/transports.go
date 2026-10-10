// Package transports provides WebSocket, UDP, and multiplexed stream
// transport primitives on top of the standard library.
package transports

import (
	"bufio"
	"context"
	"crypto/sha1"
	"encoding/base64"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// Transport errors.
var (
	ErrNotConnected = errors.New("not connected")
	ErrHandshake    = errors.New("websocket handshake failed")
	ErrFrameTooBig  = errors.New("frame exceeds maximum size")
)

// WebSocket opcodes.
const (
	OpContinuation byte = 0x0
	OpText         byte = 0x1
	OpBinary       byte = 0x2
	OpClose        byte = 0x8
	OpPing         byte = 0x9
	OpPong         byte = 0xA
)

// WSGUID is the WebSocket handshake GUID from RFC 6455.
const WSGUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

// ComputeAcceptKey returns the server handshake accept key.
func ComputeAcceptKey(key string) string {
	h := sha1.New()
	h.Write([]byte(key + WSGUID))
	return base64.StdEncoding.EncodeToString(h.Sum(nil))
}

// IsValidHandshake checks that a request upgrade looks like WebSocket.
func IsValidHandshake(lines []string) bool {
	hasUpgrade, hasConn, hasKey := false, false, false
	for _, l := range lines {
		l = strings.ToLower(l)
		switch {
		case strings.HasPrefix(l, "upgrade:") && strings.Contains(l, "websocket"):
			hasUpgrade = true
		case strings.HasPrefix(l, "connection:") && strings.Contains(l, "upgrade"):
			hasConn = true
		case strings.HasPrefix(l, "sec-websocket-key:"):
			hasKey = true
		}
	}
	return hasUpgrade && hasConn && hasKey
}

// HandshakeResponse builds the server handshake response bytes.
func HandshakeResponse(key string) []byte {
	accept := ComputeAcceptKey(strings.TrimSpace(key))
	return []byte("HTTP/1.1 101 Switching Protocols\r\n" +
		"Upgrade: websocket\r\n" +
		"Connection: Upgrade\r\n" +
		"Sec-WebSocket-Accept: " + accept + "\r\n\r\n")
}

// HandshakeRequest builds a client handshake request.
func HandshakeRequest(host, path, key string) []byte {
	return []byte(fmt.Sprintf("GET %s HTTP/1.1\r\n"+
		"Host: %s\r\n"+
		"Upgrade: websocket\r\n"+
		"Connection: Upgrade\r\n"+
		"Sec-WebSocket-Key: %s\r\n"+
		"Sec-WebSocket-Version: 13\r\n\r\n", path, host, key))
}

// WSFrame is a decoded WebSocket frame.
type WSFrame struct {
	Fin     bool
	Opcode  byte
	Payload []byte
	Masked  bool
}

// MaxFrameSize bounds frame payloads.
var MaxFrameSize = 16 * 1024 * 1024

// WriteWFrame writes a frame to a writer.
func WriteWFrame(w io.Writer, f WSFrame) error {
	var b0 byte
	if f.Fin {
		b0 |= 0x80
	}
	b0 |= f.Opcode & 0x0F
	var b1 byte
	if f.Masked {
		b1 |= 0x80
	}
	n := len(f.Payload)
	switch {
	case n < 126:
		b1 |= byte(n)
	case n <= 0xFFFF:
		b1 |= 126
	default:
		b1 |= 127
	}
	hdr := []byte{b0, b1}
	if n >= 126 && n <= 0xFFFF {
		ext := make([]byte, 2)
		binary.BigEndian.PutUint16(ext, uint16(n))
		hdr = append(hdr, ext...)
	} else if n > 0xFFFF {
		ext := make([]byte, 8)
		binary.BigEndian.PutUint64(ext, uint64(n))
		hdr = append(hdr, ext...)
	}
	if _, err := w.Write(hdr); err != nil {
		return err
	}
	if f.Masked && len(f.Payload) > 0 {
		mask := []byte{0, 0, 0, 0}
		masked := make([]byte, len(f.Payload))
		for i, b := range f.Payload {
			masked[i] = b ^ mask[i%4]
		}
		if _, err := w.Write(mask); err != nil {
			return err
		}
		_, err := w.Write(masked)
		return err
	}
	if len(f.Payload) > 0 {
		if _, err := w.Write(f.Payload); err != nil {
			return err
		}
	}
	return nil
}

// ReadWFrame reads a frame from a reader.
func ReadWFrame(r io.Reader) (WSFrame, error) {
	var f WSFrame
	var hdr [2]byte
	if _, err := io.ReadFull(r, hdr[:]); err != nil {
		return f, err
	}
	f.Fin = hdr[0]&0x80 != 0
	f.Opcode = hdr[0] & 0x0F
	masked := hdr[1]&0x80 != 0
	n := int(hdr[1] & 0x7F)
	switch n {
	case 126:
		var ext [2]byte
		if _, err := io.ReadFull(r, ext[:]); err != nil {
			return f, err
		}
		n = int(binary.BigEndian.Uint16(ext[:]))
	case 127:
		var ext [8]byte
		if _, err := io.ReadFull(r, ext[:]); err != nil {
			return f, err
		}
		n = int(binary.BigEndian.Uint64(ext[:]))
	}
	if n > MaxFrameSize {
		return f, ErrFrameTooBig
	}
	f.Payload = make([]byte, n)
	if _, err := io.ReadFull(r, f.Payload); err != nil {
		return f, err
	}
	if masked {
		var mask [4]byte
		if _, err := io.ReadFull(r, mask[:]); err != nil {
			return f, err
		}
		for i := range f.Payload {
			f.Payload[i] ^= mask[i%4]
		}
	}
	f.Masked = masked
	return f, nil
}

// WSConn is a minimal WebSocket connection over a net.Conn.
type WSConn struct {
	conn     net.Conn
	br       *bufio.Reader
	bw       *bufio.Writer
	mu       sync.Mutex
	isServer bool
	closed   atomic.Bool
	stats    WSStats
}

// WSStats tracks WebSocket statistics.
type WSStats struct {
	FramesSent atomic.Int64
	FramesRecv atomic.Int64
	BytesSent  atomic.Int64
	BytesRecv  atomic.Int64
}

// UpgradeWServer performs the server-side handshake on a raw connection.
func UpgradeWServer(conn net.Conn, key string) (*WSConn, error) {
	if _, err := conn.Write(HandshakeResponse(key)); err != nil {
		return nil, err
	}
	return &WSConn{conn: conn, br: bufio.NewReader(conn), bw: bufio.NewWriter(conn), isServer: true}, nil
}

// DialWS performs the client-side handshake.
func DialWS(ctx context.Context, addr, path, key string) (*WSConn, error) {
	var d net.Dialer
	conn, err := d.DialContext(ctx, "tcp", addr)
	if err != nil {
		return nil, err
	}
	if _, err := conn.Write(HandshakeRequest(addr, path, key)); err != nil {
		conn.Close()
		return nil, err
	}
	br := bufio.NewReader(conn)
	status, err := br.ReadString('\n')
	if err != nil {
		conn.Close()
		return nil, err
	}
	if !strings.Contains(status, "101") {
		conn.Close()
		return nil, fmt.Errorf("%w: %s", ErrHandshake, strings.TrimSpace(status))
	}
	// Consume remaining headers until blank line.
	for {
		line, err := br.ReadString('\n')
		if err != nil {
			conn.Close()
			return nil, err
		}
		if strings.TrimSpace(line) == "" {
			break
		}
	}
	return &WSConn{conn: conn, br: br, bw: bufio.NewWriter(conn)}, nil
}

// Send writes a binary frame.
func (c *WSConn) Send(data []byte, opcode byte) error {
	if c.closed.Load() {
		return ErrNotConnected
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	if err := WriteWFrame(c.bw, WSFrame{Fin: true, Opcode: opcode, Payload: data}); err != nil {
		return err
	}
	if err := c.bw.Flush(); err != nil {
		return err
	}
	c.stats.FramesSent.Add(1)
	c.stats.BytesSent.Add(int64(len(data)))
	return nil
}

// SendText writes a text frame.
func (c *WSConn) SendText(s string) error { return c.Send([]byte(s), OpText) }

// Recv reads the next frame.
func (c *WSConn) Recv() (WSFrame, error) {
	if c.closed.Load() {
		return WSFrame{}, ErrNotConnected
	}
	f, err := ReadWFrame(c.br)
	if err != nil {
		return f, err
	}
	c.stats.FramesRecv.Add(1)
	c.stats.BytesRecv.Add(int64(len(f.Payload)))
	return f, nil
}

// Close closes the connection.
func (c *WSConn) Close() error {
	if c.closed.Swap(true) {
		return nil
	}
	return c.conn.Close()
}

// Stats returns WebSocket statistics.
func (c *WSConn) Stats() *WSStats { return &c.stats }

// UDPEndpoint sends and receives datagrams.
type UDPEndpoint struct {
	conn     *net.UDPConn
	maxDgram int
	stats    UDPStats
	closed   atomic.Bool
}

// UDPStats tracks UDP statistics.
type UDPStats struct {
	Sent   atomic.Int64
	Recv   atomic.Int64
	Errors atomic.Int64
}

// ListenUDP creates a UDP listener.
func ListenUDP(addr string, maxDgram int) (*UDPEndpoint, error) {
	if maxDgram <= 0 {
		maxDgram = 64 * 1024
	}
	la, err := net.ResolveUDPAddr("udp", addr)
	if err != nil {
		return nil, err
	}
	c, err := net.ListenUDP("udp", la)
	if err != nil {
		return nil, err
	}
	return &UDPEndpoint{conn: c, maxDgram: maxDgram}, nil
}

// SendTo writes a datagram to an address.
func (u *UDPEndpoint) SendTo(data []byte, addr string) error {
	if u.closed.Load() {
		return ErrNotConnected
	}
	if len(data) > u.maxDgram {
		return ErrFrameTooBig
	}
	a, err := net.ResolveUDPAddr("udp", addr)
	if err != nil {
		return err
	}
	if _, err := u.conn.WriteToUDP(data, a); err != nil {
		u.stats.Errors.Add(1)
		return err
	}
	u.stats.Sent.Add(1)
	return nil
}

// RecvFrom reads a datagram, returning payload and sender address.
func (u *UDPEndpoint) RecvFrom() ([]byte, string, error) {
	if u.closed.Load() {
		return nil, "", ErrNotConnected
	}
	buf := make([]byte, u.maxDgram)
	n, addr, err := u.conn.ReadFromUDP(buf)
	if err != nil {
		u.stats.Errors.Add(1)
		return nil, "", err
	}
	u.stats.Recv.Add(1)
	return buf[:n], addr.String(), nil
}

// Close closes the endpoint.
func (u *UDPEndpoint) Close() error {
	if u.closed.Swap(true) {
		return nil
	}
	return u.conn.Close()
}

// Stats returns UDP statistics.
func (u *UDPEndpoint) Stats() *UDPStats { return &u.stats }

// MuxStream multiplexes logical streams over one connection using a
// 4-byte stream id + 4-byte length framing.
type MuxStream struct {
	conn   net.Conn
	mu     sync.Mutex
	nextID atomic.Uint32
	stats  MuxStats
	closed atomic.Bool
}

// MuxStats tracks multiplexer statistics.
type MuxStats struct {
	FramesSent atomic.Int64
	Frames     atomic.Int64
}

// NewMuxStream creates a multiplexer over conn.
func NewMuxStream(conn net.Conn) *MuxStream {
	return &MuxStream{conn: conn}
}

// Send writes a payload to a logical stream.
func (m *MuxStream) Send(streamID uint32, payload []byte) error {
	if m.closed.Load() {
		return ErrNotConnected
	}
	hdr := make([]byte, 8)
	binary.BigEndian.PutUint32(hdr[0:4], streamID)
	binary.BigEndian.PutUint32(hdr[4:8], uint32(len(payload)))
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, err := m.conn.Write(hdr); err != nil {
		return err
	}
	if len(payload) > 0 {
		if _, err := m.conn.Write(payload); err != nil {
			return err
		}
	}
	m.stats.FramesSent.Add(1)
	return nil
}

// Recv reads the next frame, returning stream id and payload.
func (m *MuxStream) Recv() (uint32, []byte, error) {
	if m.closed.Load() {
		return 0, nil, ErrNotConnected
	}
	var hdr [8]byte
	if _, err := io.ReadFull(m.conn, hdr[:]); err != nil {
		return 0, nil, err
	}
	id := binary.BigEndian.Uint32(hdr[0:4])
	n := binary.BigEndian.Uint32(hdr[4:8])
	buf := make([]byte, n)
	if _, err := io.ReadFull(m.conn, buf); err != nil {
		return id, nil, err
	}
	m.stats.Frames.Add(1)
	return id, buf, nil
}

// NextStreamID returns the next logical stream id.
func (m *MuxStream) NextStreamID() uint32 { return m.nextID.Add(1) }

// Close closes the underlying connection.
func (m *MuxStream) Close() error {
	if m.closed.Swap(true) {
		return nil
	}
	return m.conn.Close()
}

// Stats returns multiplexer statistics.
func (m *MuxStream) Stats() *MuxStats { return &m.stats }

// QUICPacket is a minimal QUIC long-header packet representation for
// connection establishment bookkeeping.
type QUICPacket struct {
	Version    uint32
	DestConnID []byte
	SrcConnID  []byte
	Token      []byte
	Payload    []byte
}

// EncodeQUICPacket encodes a short QUIC packet.
func EncodeQUICPacket(p QUICPacket) []byte {
	out := []byte{0xC0} // long header + type
	out = append(out, byte(p.Version>>24), byte(p.Version>>16), byte(p.Version>>8), byte(p.Version))
	out = append(out, byte(len(p.DestConnID)))
	out = append(out, p.DestConnID...)
	out = append(out, byte(len(p.SrcConnID)))
	out = append(out, p.SrcConnID...)
	out = append(out, byte(len(p.Token)))
	out = append(out, p.Token...)
	out = append(out, byte(len(p.Payload)>>8), byte(len(p.Payload)))
	return append(out, p.Payload...)
}

// DecodeQUICPacket decodes a short QUIC packet.
func DecodeQUICPacket(b []byte) (QUICPacket, error) {
	if len(b) < 9 || b[0]&0x80 == 0 {
		return QUICPacket{}, errors.New("not a long-header packet")
	}
	p := QUICPacket{}
	p.Version = uint32(b[1])<<24 | uint32(b[2])<<16 | uint32(b[3])<<8 | uint32(b[4])
	pos := 5
	n := int(b[pos])
	pos++
	p.DestConnID = append([]byte(nil), b[pos:pos+n]...)
	pos += n
	n = int(b[pos])
	pos++
	p.SrcConnID = append([]byte(nil), b[pos:pos+n]...)
	pos += n
	n = int(b[pos])
	pos++
	p.Token = append([]byte(nil), b[pos:pos+n]...)
	pos += n
	if pos+2 > len(b) {
		return QUICPacket{}, errors.New("truncated packet")
	}
	ln := int(b[pos])<<8 | int(b[pos+1])
	pos += 2
	if pos+ln > len(b) {
		return QUICPacket{}, errors.New("payload length exceeds buffer")
	}
	p.Payload = append([]byte(nil), b[pos:pos+ln]...)
	return p, nil
}

// NowFunc is swappable for tests.
var NowFunc = time.Now
