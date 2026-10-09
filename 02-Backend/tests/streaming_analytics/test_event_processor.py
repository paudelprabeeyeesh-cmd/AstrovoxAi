from streaming_analytics.event_processor import EventProcessor


class TestEventProcessor:
    def test_process_single_handler(self):
        processor = EventProcessor()
        results = []

        def handler(event):
            results.append(event["type"])
            return event["type"]

        processor.add_handler("click", handler)
        output = processor.process({"type": "click", "payload": {}})
        assert output == ["click"]

    def test_process_multiple_handlers(self):
        processor = EventProcessor()
        outputs = []

        def handler_a(event):
            outputs.append("a")

        def handler_b(event):
            outputs.append("b")

        processor.add_handler("page_view", handler_a)
        processor.add_handler("page_view", handler_b)
        processor.process({"type": "page_view", "payload": {}})
        assert outputs == ["a", "b"]

    def test_process_no_handler(self):
        processor = EventProcessor()
        output = processor.process({"type": "unknown", "payload": {}})
        assert output == []

    def test_middleware_transform(self):
        processor = EventProcessor()

        def uppercase_middleware(event):
            event = dict(event)
            event["type"] = event["type"].upper()
            return event

        processor.add_middleware(uppercase_middleware)

        def handler(event):
            return event["type"]

        processor.add_handler("CLICK", handler)
        output = processor.process({"type": "click", "payload": {}})
        assert output == ["CLICK"]

    def test_middleware_drop(self):
        processor = EventProcessor()

        def drop_middleware(event):
            return None

        processor.add_middleware(drop_middleware)

        def handler(event):
            return "should_not_run"

        processor.add_handler("click", handler)
        output = processor.process({"type": "click", "payload": {}})
        assert output == []

    def test_process_batch(self):
        processor = EventProcessor()
        results = []

        def handler(event):
            results.append(event["type"])
            return event["type"]

        processor.add_handler("click", handler)
        events = [
            {"type": "click", "payload": {}},
            {"type": "click", "payload": {}},
            {"type": "click", "payload": {}},
        ]
        processor.process_batch(events)
        assert results == ["click", "click", "click"]

    def test_handlers_for(self):
        processor = EventProcessor()
        handlers = []

        def handler(event):
            handlers.append(event["type"])
            return event["type"]

        processor.add_handler("page_view", handler)
        retrieved = processor.handlers_for("page_view")
        assert len(retrieved) == 1
        retrieved[0]({"type": "page_view", "payload": {}})
        assert handlers == ["page_view"]

    def test_handlers_for_missing_type(self):
        processor = EventProcessor()
        assert processor.handlers_for("missing") == []

    def test_handler_return_none_excluded(self):
        processor = EventProcessor()
        results = []

        def handler(event):
            results.append(event["type"])
            return None

        processor.add_handler("click", handler)
        output = processor.process({"type": "click", "payload": {}})
        assert output == []
        assert results == ["click"]

    def test_multiple_middlewares(self):
        processor = EventProcessor()

        def add_field(event):
            event = dict(event)
            event["extra"] = 1
            return event

        def double_extra(event):
            event = dict(event)
            event["extra"] = event.get("extra", 0) * 2
            return event

        processor.add_middleware(add_field)
        processor.add_middleware(double_extra)

        def handler(event):
            return event["extra"]

        processor.add_handler("click", handler)
        output = processor.process({"type": "click", "payload": {}})
        assert output == [2]

    def test_process_batch_empty(self):
        processor = EventProcessor()
        assert processor.process_batch([]) == []

    def test_middleware_changes_type(self):
        processor = EventProcessor()

        def type_middleware(event):
            event = dict(event)
            event["type"] = "page_view"
            return event

        processor.add_middleware(type_middleware)
        results = []

        def handler(event):
            results.append(event["type"])
            return event["type"]

        processor.add_handler("page_view", handler)
        output = processor.process({"type": "click", "payload": {}})
        assert output == ["page_view"]
        assert results == ["page_view"]
