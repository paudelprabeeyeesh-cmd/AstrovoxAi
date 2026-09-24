import numpy as np
import zlib


def compute_checksum(data):
    arr = np.asarray(data)
    return zlib.crc32(arr.tobytes()) & 0xFFFFFFFF


class SilentCorruptionDetector:
    def __init__(self):
        self.checksums = {}

    def register(self, name, data):
        self.checksums[name] = compute_checksum(data)

    def verify(self, name, data):
        current = compute_checksum(data)
        expected = self.checksums.get(name)
        if expected is None:
            self.checksums[name] = current
            return True
        match = current == expected
        if not match:
            self.checksums[name] = current
        return match
