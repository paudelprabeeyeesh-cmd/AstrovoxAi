import time
import pytest
from system_integration.api_integration import (
    APIGateway,
    APIProvider,
    CircuitBreaker,
    CircuitState,
    Request,
    Response,
)


def make_gateway() -> APIGateway:
    gateway = APIGateway()

    def transport(req: Request) -> Response:
        return Response(status=200, body={"ok": True}, headers={})

    provider = APIProvider(name="svc", base_url="http://example.com")
    gateway.register_provider(provider, transport)
    return gateway


def test_circuit_breaker_closed():
    provider = APIProvider(name="p", base_url="http://x")
    breaker = CircuitBreaker(provider)
    assert breaker.allow_request() is True


def test_circuit_breaker_opens_on_failures():
    provider = APIProvider(name="p", base_url="http://x", failure_threshold=3)
    breaker = CircuitBreaker(provider)
    for _ in range(3):
        breaker.record_failure()
    assert breaker.allow_request() is False
    assert provider.circuit == CircuitState.OPEN


def test_circuit_breaker_half_open():
    provider = APIProvider(name="p", base_url="http://x", failure_threshold=2)
    breaker = CircuitBreaker(provider)
    for _ in range(2):
        breaker.record_failure()
    assert provider.circuit == CircuitState.OPEN
    provider.last_failure = time.time() - 20
    assert breaker.allow_request() is True


def test_request_transform():
    req = Request(method="GET", path="/x", headers={"auth": "TOKEN"}, params={}, json_body=None)
    mapping = {"auth": ("X-Auth", "TOKEN")}
    out = req.transform(mapping)
    assert out.headers["X-Auth"] == "TOKEN"


def test_gateway_request_success():
    gateway = make_gateway()
    req = Request(method="GET", path="/", headers={}, params={}, json_body=None)
    res = gateway.request("svc", req)
    assert res.status == 200
    assert res.body["ok"] is True


def test_gateway_circuit_open_raises():
    provider = APIProvider(name="p", base_url="http://x", failure_threshold=2, retries=0)
    gateway = APIGateway()

    def transport(req: Request) -> Response:
        raise RuntimeError("boom")

    gateway.register_provider(provider, transport)
    req = Request(method="GET", path="/", headers={}, params={}, json_body=None)
    for _ in range(2):
        try:
            gateway.request("p", req)
        except Exception as _e:  # noqa: BLE001
            pass
    with pytest.raises(Exception):
        gateway.request("p", req)


def test_gateway_fan_out():
    gateway = APIGateway()
    provider = APIProvider(name="s1", base_url="http://x")
    gateway.register_provider(provider, lambda req: Response(status=200, body={}))
    results = gateway.fan_out({"s1": Request(method="GET", path="/", headers={}, params={}, json_body=None)})
    assert "s1" in results
    assert results["s1"].status == 200
