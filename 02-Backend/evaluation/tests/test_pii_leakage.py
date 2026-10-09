
from app.evaluation.pii_leakage import PIILeakageTester


def test_pii_no_leak():
    tester = PIILeakageTester()
    result = tester.test("The capital of France is Paris.")
    assert result["leaked"] is False
    assert result["pii_found"] == 0
    assert result["score"] == 1.0


def test_pii_email_detected():
    tester = PIILeakageTester()
    result = tester.test("Contact me at user@example.com for details.")
    assert result["leaked"] is True
    assert result["pii_found"] >= 1


def test_pii_ssn_detected():
    tester = PIILeakageTester()
    result = tester.test("My SSN is 123-45-6789.")
    assert result["leaked"] is True
    types = [f["type"] for f in result["findings"]]
    assert "ssn" in types


def test_pii_scan_response():
    tester = PIILeakageTester()
    result = tester.scan_response("Here is your info: user@example.com", "My email is user@example.com")
    assert result["leaked"] is True
    assert result["pii_found"] >= 1
