import pytest
from final_system.integration_hub import ConnectionConfig, Connector, IntegrationHub


class FakeConnector(Connector):
    def connect(self) -> None:
        self._connected = True
    def disconnect(self) -> None:
        self._connected = False
    def send(self, data): return ("sent", data)
    def receive(self): return "received"


def test_register_and_create_connector():
    hub = IntegrationHub()
    config = ConnectionConfig(name="svc", endpoint="http://localhost")
    hub.register_config(config)
    connector = hub.create_connector("svc", FakeConnector, config)
    assert connector is not None


def test_connect_disconnect():
    hub = IntegrationHub()
    config = ConnectionConfig(name="svc", endpoint="http://localhost")
    hub.register_config(config)
    connector = hub.create_connector("svc", FakeConnector, config)
    hub.connect("svc")
    assert connector.connected is True
    hub.disconnect("svc")
    assert connector.connected is False


def test_send_receive():
    hub = IntegrationHub()
    config = ConnectionConfig(name="svc", endpoint="http://localhost")
    hub.register_config(config)
    hub.create_connector("svc", FakeConnector, config)
    hub.connect("svc")
    assert hub.send("svc", {"x": 1}) == ("sent", {"x": 1})
    assert hub.receive("svc") == "received"


def test_list_connectors():
    hub = IntegrationHub()
    config = ConnectionConfig(name="svc1", endpoint="http://localhost")
    hub.register_config(config)
    hub.create_connector("svc1", FakeConnector, config)
    assert "svc1" in hub.list_connectors()


def test_missing_connector():
    hub = IntegrationHub()
    with pytest.raises(KeyError):
        hub.send("missing", None)
