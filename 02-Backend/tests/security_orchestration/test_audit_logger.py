from security_orchestration.audit_logger import AuditLogger


def test_log_entry() -> None:
    logger = AuditLogger()
    entry = logger.log("auth", "login", "user-1", "success")
    assert entry["category"] == "auth"
    assert entry["event"] == "login"
    assert entry["actor"] == "user-1"
    assert entry["outcome"] == "success"
    assert "signature" in entry
    assert "timestamp" in entry


def test_chain() -> None:
    logger = AuditLogger()
    logger.log("a", "e1", "u1", "ok")
    logger.log("b", "e2", "u2", "fail")
    chain = logger.chain()
    assert len(chain) == 2
    assert chain[0]["event"] == "e1"
    assert chain[1]["event"] == "e2"


def test_verify_integrity_valid() -> None:
    logger = AuditLogger()
    logger.log("auth", "login", "u1", "success")
    logger.log("auth", "logout", "u1", "success")
    assert logger.verify_integrity() is True


def test_verify_integrity_tampered() -> None:
    logger = AuditLogger()
    logger.log("auth", "login", "u1", "success")
    logger._chain[0]["actor"] = "u2"
    assert logger.verify_integrity() is False


def test_entries_filtered() -> None:
    logger = AuditLogger()
    logger.log("auth", "login", "u1", "success")
    logger.log("api", "request", "u1", "ok")
    logger.log("auth", "logout", "u1", "success")
    auth_entries = logger.entries("auth")
    assert len(auth_entries) == 2
    assert all(e["category"] == "auth" for e in auth_entries)


def test_entries_all() -> None:
    logger = AuditLogger()
    logger.log("a", "e1", "u1", "ok")
    logger.log("b", "e2", "u2", "ok")
    assert len(logger.entries()) == 2


def test_log_with_metadata() -> None:
    logger = AuditLogger()
    entry = logger.log("api", "call", "svc", "ok", {"endpoint": "/health"})
    assert entry["metadata"] == {"endpoint": "/health"}


def test_verify_empty_chain() -> None:
    logger = AuditLogger()
    assert logger.verify_integrity() is True
