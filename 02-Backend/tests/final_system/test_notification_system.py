import pytest
from final_system.notification_system import Notification, NotificationSystem


def test_send_to_channel():
    ns = NotificationSystem()
    received = []
    ns.register_channel("email", lambda n: received.append(n.subject))
    ns.send(Notification(channel="email", subject="hello", body="body"))
    assert received == ["hello"]


def test_subscribe_and_forward():
    ns = NotificationSystem()
    received = []
    ns.register_channel("log", lambda n: received.append(n.subject))
    ns.subscribe("log", "log")
    ns.send(Notification(channel="log", subject="alert", body="msg"))
    assert received == ["alert"]


def test_list_channels():
    ns = NotificationSystem()
    ns.register_channel("email", lambda n: None)
    ns.register_channel("sms", lambda n: None)
    assert set(ns.list_channels()) == {"email", "sms"}


def test_severity_in_notification():
    ns = NotificationSystem()
    captured = []
    ns.register_channel("ops", lambda n: captured.append(n.severity))
    ns.send(Notification(channel="ops", subject="s", body="b", severity="critical"))
    assert captured == ["critical"]
