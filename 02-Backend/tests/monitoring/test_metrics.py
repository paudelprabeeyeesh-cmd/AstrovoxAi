from unittest.mock import patch



class TestMetricsModule:
    def test_prometheus_available_flag(self):
        from app.metrics import PROMETHEUS_AVAILABLE

        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    def test_get_metrics_returns_bytes(self):
        from app.metrics import get_metrics

        result = get_metrics()
        assert isinstance(result, bytes)

    def test_track_request_noop_when_unavailable(self):
        from app.metrics import track_request

        with patch("app.metrics.PROMETHEUS_AVAILABLE", False):
            track_request("GET", "/test", 200, 0.1)

    def test_track_request_records_when_available(self):
        from app.metrics import track_request, http_requests_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(http_requests_total.labels("GET", "/test", 200), "inc") as mock_inc:
                track_request("GET", "/test", 200, 0.1)
                mock_inc.assert_called_once()

    def test_track_request_records_error_when_5xx(self):
        from app.metrics import track_request, http_errors_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(http_errors_total.labels("GET", "/test", 500), "inc") as mock_inc:
                track_request("GET", "/test", 500, 0.1)
                mock_inc.assert_called_once()

    def test_track_ai_request(self):
        from app.metrics import track_ai_request, ai_requests_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(ai_requests_total.labels("gpt-4", "ok"), "inc") as mock_inc:
                track_ai_request("gpt-4", "ok", tokens=10)
                mock_inc.assert_called_once()

    def test_track_cache_hit(self):
        from app.metrics import track_cache_hit, cache_hits_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(cache_hits_total.labels("redis"), "inc") as mock_inc:
                track_cache_hit("redis")
                mock_inc.assert_called_once()

    def test_track_cache_miss(self):
        from app.metrics import track_cache_miss, cache_misses_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(cache_misses_total.labels("redis"), "inc") as mock_inc:
                track_cache_miss("redis")
                mock_inc.assert_called_once()

    def test_track_db_query(self):
        from app.metrics import track_db_query, db_query_duration

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(db_query_duration.labels("select"), "observe") as mock_obs:
                track_db_query("select", 0.05)
                mock_obs.assert_called_once_with(0.05)

    def test_track_auth_attempt(self):
        from app.metrics import track_auth_attempt, auth_attempts_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(auth_attempts_total.labels("google", "success"), "inc") as mock_inc:
                track_auth_attempt("google", "success")
                mock_inc.assert_called_once()

    def test_inc_connections(self):
        from app.metrics import inc_connections, active_connections

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(active_connections, "inc") as mock_inc:
                inc_connections()
                mock_inc.assert_called_once()

    def test_dec_connections(self):
        from app.metrics import dec_connections, active_connections

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(active_connections, "dec") as mock_dec:
                dec_connections()
                mock_dec.assert_called_once()

    def test_track_websocket_event(self):
        from app.metrics import track_websocket_event, websocket_connections_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(websocket_connections_total.labels("connect"), "inc") as mock_inc:
                track_websocket_event("connect")
                mock_inc.assert_called_once()

    def test_track_error(self):
        from app.metrics import track_error, http_errors_total

        with patch("app.metrics.PROMETHEUS_AVAILABLE", True):
            with patch.object(http_errors_total.labels("POST", "/api", 500), "inc") as mock_inc:
                track_error("POST", "/api", 500)
                mock_inc.assert_called_once()
