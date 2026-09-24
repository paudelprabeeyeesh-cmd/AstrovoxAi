"""Tests for report_generator module."""

import json
import pytest

from security_audit.report_generator import Finding, ReportGenerator, ReportMetadata, ReportSection, SecurityReport


@pytest.fixture
def metadata():
    return ReportMetadata(title="Security Audit", author="Tester", created_at=1000.0, version="1.0")


@pytest.fixture
def generator(metadata):
    return ReportGenerator(metadata=metadata)


class TestFinding:
    def test_finding_creation(self):
        f = Finding(title="SQL Injection", severity="critical", description="Test", recommendation="Patch")
        assert f.title == "SQL Injection"
        assert f.severity == "critical"

    def test_finding_defaults(self):
        f = Finding(title="XSS", severity="high", description="Desc", recommendation="Fix")
        assert f.title == "XSS"


class TestReportSection:
    def test_section_creation(self):
        s = ReportSection(title="Findings", content="Details here")
        assert s.title == "Findings"
        assert s.findings == []


class TestReportMetadata:
    def test_metadata_creation(self):
        m = ReportMetadata(title="R", author="A", created_at=500.0, version="1")
        assert m.title == "R"
        assert m.version == "1"


class TestReportGenerator:
    def test_add_section(self, generator):
        generator.add_section("Summary", "All clear")
        assert len(generator.sections) == 1
        assert generator.sections[0].title == "Summary"

    def test_add_finding(self, generator):
        generator.add_section("Findings", "")
        generator.add_finding("SQLi", "critical", "Description", "Patch now")
        assert len(generator.findings) == 1
        assert generator.findings[0].title == "SQLi"

    def test_add_executive_summary(self, generator):
        generator.add_executive_summary("We are safe")
        assert generator.sections[0].title == "Executive Summary"

    def test_to_text_contains_title(self, generator):
        generator.add_section("Intro", "Hello")
        text = generator.to_text()
        assert "Security Audit" in text

    def test_to_text_contains_section(self, generator):
        generator.add_section("Intro", "Hello")
        text = generator.to_text()
        assert "## Intro" in text

    def test_to_text_contains_finding(self, generator):
        generator.add_section("Findings", "")
        generator.add_finding("Bug", "high", "Desc", "Fix")
        text = generator.to_text()
        assert "Bug" in text
        assert "HIGH" in text

    def test_to_json_contains_title(self, generator):
        generator.add_section("S", "C")
        data = json.loads(generator.to_json())
        assert data["metadata"]["title"] == "Security Audit"

    def test_to_json_contains_sections(self, generator):
        generator.add_section("S1", "C1")
        data = json.loads(generator.to_json())
        assert len(data["sections"]) == 1
        assert data["sections"][0]["title"] == "S1"

    def test_to_json_contains_findings(self, generator):
        generator.add_section("F", "")
        generator.add_finding("Bug", "high", "Desc", "Fix")
        data = json.loads(generator.to_json())
        assert len(data["findings"]) == 1
        assert data["findings"][0]["title"] == "Bug"

    def test_to_html_contains_title(self, generator):
        generator.add_section("S", "C")
        html = generator.to_html()
        assert "<h1>Security Audit</h1>" in html

    def test_to_html_contains_section(self, generator):
        generator.add_section("Intro", "Hello")
        html = generator.to_html()
        assert "<h2>Intro</h2>" in html

    def test_to_html_contains_finding(self, generator):
        generator.add_section("F", "")
        generator.add_finding("Bug", "high", "Desc", "Fix")
        html = generator.to_html()
        assert "Bug" in html
        assert "HIGH" in html

    def test_get_findings_by_severity(self, generator):
        generator.add_section("F", "")
        generator.add_finding("F1", "critical", "D1", "R1")
        generator.add_finding("F2", "high", "D2", "R2")
        generator.add_finding("F3", "critical", "D3", "R3")
        critical = generator.get_findings_by_severity("critical")
        assert len(critical) == 2

    def test_get_findings_by_severity_empty(self, generator):
        result = generator.get_findings_by_severity("critical")
        assert result == []

    def test_multiple_sections(self, generator):
        generator.add_section("S1", "C1")
        generator.add_section("S2", "C2")
        assert len(generator.sections) == 2

    def test_finding_added_to_current_section(self, generator):
        generator.add_section("S1", "C1")
        generator.add_finding("F1", "low", "D", "R")
        assert len(generator.sections[0].findings) == 1

    def test_to_json_is_valid_json(self, generator):
        generator.add_section("S", "C")
        data = json.loads(generator.to_json())
        assert isinstance(data, dict)

    def test_to_html_structure(self, generator):
        generator.add_section("S", "C")
        html = generator.to_html()
        assert html.startswith("<html>")
        assert html.endswith("</html>")
