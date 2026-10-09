from unittest.mock import MagicMock



class TestObservability:
    def test_get_logger_returns_logger(self):
        from app.observability import get_logger

        logger = get_logger("test")
        assert logger is not None

    def test_new_correlation_id(self):
        from app.observability import new_correlation_id, get_correlation_id

        cid = new_correlation_id()
        assert isinstance(cid, str)
        assert len(cid) > 0
        assert get_correlation_id() == cid

    def test_set_correlation_id(self):
        from app.observability import set_correlation_id, get_correlation_id

        set_correlation_id("abc-123")
        assert get_correlation_id() == "abc-123"

    def test_log_event_with_extra(self):
        from app.observability import log_event

        mock_logger = MagicMock()
        log_event(mock_logger, "test_event", level="info", foo="bar")
        mock_logger.info.assert_called_once()

    def test_span_context_manager(self):
        from app.observability import Span

        mock_logger = MagicMock()
        with Span(name="test_op", logger=mock_logger) as span:
            assert span.name == "test_op"
            assert span.span_id != ""
            assert span.trace_id != ""
        assert mock_logger.debug.call_count == 2

    def test_request_logger_log_request(self):
        from app.observability import RequestLogger

        mock_logger = MagicMock()
        rl = RequestLogger(logger=mock_logger)
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/health"
        request.client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        rl.log_request(request, response, 0.05)
        mock_logger.info.assert_called_once()

    def test_request_logger_log_error(self):
        from app.observability import RequestLogger

        mock_logger = MagicMock()
        rl = RequestLogger(logger=mock_logger)
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api"
        exc = RuntimeError("boom")
        rl.log_error(request, exc, 0.1)
        mock_logger.error.assert_called_once()
