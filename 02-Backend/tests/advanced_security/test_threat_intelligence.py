from advanced_security.threat_intelligence import TLP, ThreatIntelligence


def test_threat_intelligence_init() -> None:
    ti = ThreatIntelligence()
    assert ti is not None


def test_add_ioc() -> None:
    ti = ThreatIntelligence()
    ti.add_ioc("malicious.example.com", "domain", TLP.AMBER)
    assert len(ti._iocs) == 1


def test_analyze_ipv4() -> None:
    ti = ThreatIntelligence()
    result = ti.analyze_ip("198.51.100.1")
    assert result["malicious"] is True


def test_analyze_ipv6() -> None:
    ti = ThreatIntelligence()
    result = ti.analyze_ip("2001:db8::1")
    assert result["malicious"] is False


def test_analyze_file() -> None:
    ti = ThreatIntelligence()
    result = ti.analyze_file({"sha256": "f0e4c2f7"})
    assert result["malicious"] is True


def test_extract_iocs() -> None:
    ti = ThreatIntelligence()
    result = ti.extract_iocs("Text with 1.2.3.4 and example.com")
    assert "ips" in result
    assert "domains" in result


def test_match_iocs() -> None:
    ti = ThreatIntelligence()
    ti.add_ioc("evil.example.com", "domain", TLP.RED)
    matched = ti.match_iocs("Visit evil.example.com for more")
    assert len(matched) == 1
    assert matched[0]["value"] == "evil.example.com"


def test_enrich_ip() -> None:
    ti = ThreatIntelligence()
    result = ti.enrich_ip("203.0.113.1")
    assert result["ip"] == "203.0.113.1"
    assert "geo" in result


def test_enrich_domain() -> None:
    ti = ThreatIntelligence()
    result = ti.enrich_domain("example.com")
    assert result["domain"] == "example.com"


def test_stix_report() -> None:
    ti = ThreatIntelligence()
    iocs = [{"value": "1.2.3.4", "type": "ip"}]
    report = ti.stix_report(iocs)
    assert "report" in report


def test_mitre_technique() -> None:
    ti = ThreatIntelligence()
    result = ti.mitre_technique("T1566")
    assert result["id"] == "T1566"


def test_ioc_vault() -> None:
    ti = ThreatIntelligence()
    ti.add_ioc("vault.test", "domain")
    vault = ti.ioc_vault()
    assert len(vault) == 1
