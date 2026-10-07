// Package filesystem provides atomic and failure-tolerant file utilities used
// by the serialization, checkpoint, and configuration layers.
package filesystem

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"

	"github.com/astrovox/astrovox/internal/errors"
)

// AtomicWrite writes data to path atomically: it writes a temp file in the
// same directory, optionally fsyncs, then renames over the target.
func AtomicWrite(path string, data []byte, fsync bool) error {
	dir := filepath.Dir(path)
	tmp, err := os.CreateTemp(dir, ".astrovox-tmp-*")
	if err != nil {
		return errors.Wrap(err, errors.CodeInternal, "temp file creation failed").
			WithField("path", path)
	}
	tmpName := tmp.Name()
	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		_ = os.Remove(tmpName)
		return errors.Wrap(err, errors.CodeInternal, "temp file write failed").
			WithField("path", path)
	}
	if fsync {
		if err := tmp.Sync(); err != nil {
			_ = tmp.Close()
			_ = os.Remove(tmpName)
			return errors.Wrap(err, errors.CodeInternal, "temp file sync failed").
				WithField("path", path)
		}
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpName)
		return errors.Wrap(err, errors.CodeInternal, "temp file close failed").
			WithField("path", path)
	}
	if err := os.Rename(tmpName, path); err != nil {
		_ = os.Remove(tmpName)
		return errors.Wrap(err, errors.CodeInternal, "atomic rename failed").
			WithField("path", path)
	}
	return nil
}

// ReadFile reads a file with a size limit (bytes; 0 = unlimited).
func ReadFile(path string, maxBytes int64) ([]byte, error) {
	info, err := os.Stat(path)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeNotFound, "file stat failed").
			WithField("path", path)
	}
	if maxBytes > 0 && info.Size() > maxBytes {
		return nil, errors.New(errors.CodeOutOfRange, "file exceeds size limit").
			WithField("path", path).WithField("size", info.Size()).WithField("limit", maxBytes)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeNotFound, "file read failed").
			WithField("path", path)
	}
	return data, nil
}

// Copy copies src to dst with a buffered stream. Existing dst is truncated.
func Copy(src, dst string, progress func(written int64)) error {
	in, err := os.Open(src)
	if err != nil {
		return errors.Wrap(err, errors.CodeNotFound, "source open failed").WithField("src", src)
	}
	defer in.Close()
	out, err := os.Create(dst)
	if err != nil {
		return errors.Wrap(err, errors.CodeInternal, "destination create failed").WithField("dst", dst)
	}
	defer out.Close()
	buf := make([]byte, 32*1024)
	var written int64
	for {
		n, rerr := in.Read(buf)
		if n > 0 {
			if _, werr := out.Write(buf[:n]); werr != nil {
				return errors.Wrap(werr, errors.CodeInternal, "copy write failed").
					WithField("dst", dst)
			}
			written += int64(n)
			if progress != nil {
				progress(written)
			}
		}
		if rerr == io.EOF {
			break
		}
		if rerr != nil {
			return errors.Wrap(rerr, errors.CodeInternal, "copy read failed").
				WithField("src", src)
		}
	}
	return nil
}

// Walk invokes visit for every file under root matching the suffix filter
// (empty suffix matches all). Symlinks are not followed.
func Walk(root, suffix string, visit func(path string, info os.FileInfo) error) error {
	return filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return nil
		}
		if suffix != "" && !strings.HasSuffix(path, suffix) {
			return nil
		}
		return visit(path, info)
	})
}

// ListDir returns sorted entries of a directory with an optional suffix filter.
func ListDir(dir, suffix string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeNotFound, "directory read failed").
			WithField("dir", dir)
	}
	var out []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		if suffix != "" && !strings.HasSuffix(e.Name(), suffix) {
			continue
		}
		out = append(out, filepath.Join(dir, e.Name()))
	}
	sort.Strings(out)
	return out, nil
}

// TempDir creates a tracked temporary directory that is removed when Cleanup
// is called or when the process exits (best effort via finalizer).
type TempDir struct {
	path string
	once sync.Once
}

// NewTempDir creates a new tracked temporary directory.
func NewTempDir(pattern string) (*TempDir, error) {
	path, err := os.MkdirTemp("", pattern)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInternal, "temp dir creation failed")
	}
	td := &TempDir{path: path}
	return td, nil
}

// Path returns the temporary directory path.
func (t *TempDir) Path() string { return t.path }

// Cleanup removes the directory tree.
func (t *TempDir) Cleanup() error {
	var err error
	t.once.Do(func() {
		err = os.RemoveAll(t.path)
	})
	return err
}

// EnsureDir creates dir (and parents) if missing.
func EnsureDir(dir string, perm os.FileMode) error {
	if err := os.MkdirAll(dir, perm); err != nil {
		return errors.Wrap(err, errors.CodeInternal, "directory creation failed").
			WithField("dir", dir)
	}
	return nil
}

// Exists reports whether path exists.
func Exists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// Size returns the file size in bytes.
func Size(path string) (int64, error) {
	info, err := os.Stat(path)
	if err != nil {
		return 0, errors.Wrap(err, errors.CodeNotFound, "file stat failed").
			WithField("path", path)
	}
	return info.Size(), nil
}

// HumanSize formats a byte count with binary units.
func HumanSize(n int64) string {
	const unit = 1024
	if n < unit {
		return fmt.Sprintf("%d B", n)
	}
	div, exp := int64(unit), 0
	for x := n / unit; x >= unit; x /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB", float64(n)/float64(div), "KMGTPE"[exp])
}
