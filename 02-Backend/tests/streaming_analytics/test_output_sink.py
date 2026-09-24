from streaming_analytics.output_sink import OutputSink, OutputRecord


class TestOutputSink:
    def test_write_single_record(self):
        sink = OutputSink()
        result = sink.write("key1", 42, 1.0)
        assert result is True
        assert sink.buffer_size() == 1

    def test_write_returns_false_when_full(self):
        sink = OutputSink(max_buffer_size=2)
        sink.write("k1", 1, 1.0)
        sink.write("k2", 2, 2.0)
        result = sink.write("k3", 3, 3.0)
        assert result is False
        assert sink.buffer_size() == 2

    def test_flush_clears_buffer(self):
        sink = OutputSink()
        sink.write("k1", 1, 1.0)
        records = sink.flush()
        assert len(records) == 1
        assert sink.buffer_size() == 0

    def test_flush_invokes_callback(self):
        sink = OutputSink()
        flushed = []

        def callback(records):
            flushed.extend(records)

        sink.on_flush(callback)
        sink.write("k1", 1, 1.0)
        sink.flush()
        assert len(flushed) == 1
        assert flushed[0].key == "k1"

    def test_write_batch(self):
        sink = OutputSink()
        records = [
            {"key": "k1", "value": 1, "timestamp": 1.0},
            {"key": "k2", "value": 2, "timestamp": 2.0},
        ]
        written = sink.write_batch(records)
        assert written == 2
        assert sink.buffer_size() == 2

    def test_peek_without_n(self):
        sink = OutputSink()
        sink.write("k1", 1, 1.0)
        sink.write("k2", 2, 2.0)
        peeked = sink.peek()
        assert len(peeked) == 2

    def test_peek_with_n(self):
        sink = OutputSink()
        sink.write("k1", 1, 1.0)
        sink.write("k2", 2, 2.0)
        peeked = sink.peek(n=1)
        assert len(peeked) == 1
        assert peeked[0].key == "k1"

    def test_drain(self):
        sink = OutputSink()
        sink.write("k1", 1, 1.0)
        drained = sink.drain()
        assert len(drained) == 1
        assert sink.buffer_size() == 0

    def test_output_record_metadata(self):
        sink = OutputSink()
        sink.write("k1", 1, 1.0, source="sensor_a")
        records = sink.flush()
        assert records[0].metadata == {"source": "sensor_a"}

    def test_thread_safety(self):
        import threading

        sink = OutputSink(max_buffer_size=1000)

        def writer():
            for i in range(100):
                sink.write(f"k{i}", i, float(i))

        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sink.buffer_size() <= 1000
