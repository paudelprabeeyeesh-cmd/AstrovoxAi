import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class TestResult:
    test_name: str
    status: TestStatus
    endpoint: str
    details: str = ""
    evidence: Optional[dict] = None
    duration_ms: float = 0.0


@dataclass
class TestReport:
    base_url: str
    results: list[TestResult]
    summary: dict = None

    def __post_init__(self) -> None:
        if self.summary is None:
            self.summary = self._compute_summary()

    def _compute_summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total else "0.0%",
        }


class PenTestSuite:
    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "AstrovoxAi-PenTest/1.0"})

    def test_sql_injection(self, endpoint: str) -> TestResult:
        test_name = "sql_injection"
        start = time.perf_counter()
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT NULL,NULL,NULL--",
            "admin'--",
            "' OR EXISTS(SELECT * FROM users) --",
        ]
        vulnerable = False
        evidence = {"payloads_tested": payloads, "reflections": []}

        for payload in payloads:
            try:
                url = f"{endpoint}?q={payload}"
                resp = self.session.get(url, timeout=10)
                duration = (time.perf_counter() - start) * 1000

                if resp.status_code == 500 and ("sql" in resp.text.lower() or "syntax" in resp.text.lower()):
                    vulnerable = True
                    evidence["reflections"].append({"payload": payload, "status": resp.status_code, "snippet": resp.text[:200]})
                    break
            except requests.RequestException as exc:
                duration = (time.perf_counter() - start) * 1000
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    endpoint=endpoint,
                    details=f"Request failed: {exc}",
                    duration_ms=duration,
                )

        duration = (time.perf_counter() - start) * 1000
        status = TestStatus.FAIL if vulnerable else TestStatus.PASS
        details = "SQL injection vulnerability detected" if vulnerable else "No SQL injection vulnerabilities detected"
        return TestResult(
            test_name=test_name,
            status=status,
            endpoint=endpoint,
            details=details,
            evidence=evidence,
            duration_ms=duration,
        )

    def test_xss(self, endpoint: str) -> TestResult:
        test_name = "xss"
        start = time.perf_counter()
        payloads = [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "\"'><script>alert(1)</script>",
        ]
        reflected = False
        evidence = {"payloads_tested": payloads, "reflections": []}

        for payload in payloads:
            try:
                url = f"{endpoint}?input={payload}"
                resp = self.session.get(url, timeout=10)
                duration = (time.perf_counter() - start) * 1000

                if payload in resp.text:
                    reflected = True
                    evidence["reflections"].append({"payload": payload, "status": resp.status_code})
                    break
            except requests.RequestException as exc:
                duration = (time.perf_counter() - start) * 1000
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    endpoint=endpoint,
                    details=f"Request failed: {exc}",
                    duration_ms=duration,
                )

        duration = (time.perf_counter() - start) * 1000
        status = TestStatus.FAIL if reflected else TestStatus.PASS
        details = "Reflected XSS vulnerability detected" if reflected else "No reflected XSS vulnerabilities detected"
        return TestResult(
            test_name=test_name,
            status=status,
            endpoint=endpoint,
            details=details,
            evidence=evidence,
            duration_ms=duration,
        )

    def test_auth_bypass(self, endpoint: str) -> TestResult:
        test_name = "auth_bypass"
        start = time.perf_counter()
        bypassed = False
        evidence = {"attempts": []}

        bypass_attempts = [
            {"headers": {"Authorization": "Bearer "}},
            {"headers": {"Authorization": "Bearer invalid"}},
            {"cookies": {"session": "admin"}},
            {"params": {"token": "null"}},
        ]

        for attempt in bypass_attempts:
            try:
                resp = self.session.get(endpoint, timeout=10, **attempt)
                duration = (time.perf_counter() - start) * 1000

                if resp.status_code == 200:
                    bypassed = True
                    evidence["attempts"].append({"attempt": attempt, "status": resp.status_code})
                    break
            except requests.RequestException as exc:
                duration = (time.perf_counter() - start) * 1000
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    endpoint=endpoint,
                    details=f"Request failed: {exc}",
                    duration_ms=duration,
                )

        duration = (time.perf_counter() - start) * 1000
        status = TestStatus.FAIL if bypassed else TestStatus.PASS
        details = "Authentication bypass detected" if bypassed else "No authentication bypass detected"
        return TestResult(
            test_name=test_name,
            status=status,
            endpoint=endpoint,
            details=details,
            evidence=evidence,
            duration_ms=duration,
        )

    def test_rate_limit(self, endpoint: str) -> TestResult:
        test_name = "rate_limit"
        start = time.perf_counter()
        requests_sent = 20
        status_codes: list[int] = []
        evidence = {"requests_sent": requests_sent, "rate_limited_at": None}

        for _ in range(requests_sent):
            try:
                resp = self.session.get(endpoint, timeout=10)
                status_codes.append(resp.status_code)
                if resp.status_code == 429:
                    evidence["rate_limited_at"] = len(status_codes)
                    break
            except requests.RequestException:
                continue

        duration = (time.perf_counter() - start) * 1000
        has_rate_limit = 429 in status_codes
        status = TestStatus.PASS if has_rate_limit else TestStatus.FAIL
        details = "Rate limiting is enforced" if has_rate_limit else "No rate limiting detected after multiple requests"
        return TestResult(
            test_name=test_name,
            status=status,
            endpoint=endpoint,
            details=details,
            evidence=evidence,
            duration_ms=duration,
        )

    def run_full_scan(self, base_url: str) -> TestReport:
        endpoints = [
            f"{base_url}/auth/login",
            f"{base_url}/auth/register",
            f"{base_url}/solve",
            f"{base_url}/api/v1/query",
        ]
        results: list[TestResult] = []

        for endpoint in endpoints:
            logger.info("Testing endpoint: %s", endpoint)
            results.append(self.test_sql_injection(endpoint))
            results.append(self.test_xss(endpoint))
            results.append(self.test_auth_bypass(endpoint))
            results.append(self.test_rate_limit(endpoint))

        report = TestReport(base_url=base_url, results=results)
        logger.info("Penetration test summary: %s", report.summary)
        return report
