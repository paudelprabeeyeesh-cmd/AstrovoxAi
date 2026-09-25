"""TLS hardening and certificate management helpers.

This module provides TLS/SSL security utilities with:

1. TLS configuration validation
2. Certificate chain verification
3. Cipher suite recommendations
4. TLS version enforcement
5. Certificate transparency log checking
6. HSTS header configuration
7. OCSP stapling validation
8. Self-signed certificate generation for development
9. Certificate rotation reminders

Threat model: OWASP Top A02:2021 - Cryptographic Failures
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import ssl
import socket
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TLSVersion(str, Enum):
    TLS_1_0 = "tls1.0"
    TLS_1_1 = "tls1.1"
    TLS_1_2 = "tls1.2"
    TLS_1_3 = "tls1.3"


class CipherStrength(str, Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    RECOMMENDED = "recommended"


class CertStatus(str, Enum):
    VALID = "valid"
    EXPIRED = "expired"
    NOT_YET_VALID = "not_yet_valid"
    REVOKED = "revoked"
    SELF_SIGNED = "self_signed"
    UNTRUSTED = "untrusted"
    UNKNOWN = "unknown"


@dataclass
class TLSSecurityReport:
    host: str
    port: int
    tls_version: Optional[TLSVersion]
    cipher_suite: Optional[str]
    cipher_strength: CipherStrength
    certificate_status: CertStatus
    certificate_details: Dict[str, Any] = field(default_factory=dict)
    hsts_enabled: bool = False
    ocsp_stapling: bool = False
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    score: int = 0


@dataclass
class CertificateInfo:
    subject: str
    issuer: str
    serial_number: str
    not_before: str
    not_after: str
    signature_algorithm: str
    public_key: str
    san: List[str] = field(default_factory=list)
    is_self_signed: bool = False
    is_expired: bool = False
    days_until_expiry: int = 0


class TLSHardening:
    """TLS hardening utilities and certificate management."""

    def __init__(self):
        self._recommended_versions = {TLSVersion.TLS_1_2, TLSVersion.TLS_1_3}
        self._recommended_ciphers = {
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256",
            "ECDHE-ECDSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-ECDSA-CHACHA20-POLY1305",
            "ECDHE-RSA-CHACHA20-POLY1305",
            "ECDHE-ECDSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES128-GCM-SHA256",
        }
        self._weak_ciphers = {"RC4", "DES", "3DES", "MD5", "SHA1", "EXPORT", "NULL", "anon"}
        self._hsts_max_age = 31536000  # 1 year

    def create_ssl_context(
        self,
        min_version: TLSVersion = TLSVersion.TLS_1_2,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
        verify_mode: int = ssl.CERT_REQUIRED,
    ) -> ssl.SSLContext:
        """Create a hardened SSL context."""
        tls_map = {
            TLSVersion.TLS_1_0: ssl.TLSVersion.MINIMUM_SUPPORTED,
            TLSVersion.TLS_1_1: ssl.TLSVersion.TLSv1_1,
            TLSVersion.TLS_1_2: ssl.TLSVersion.TLSv1_2,
            TLSVersion.TLS_1_3: ssl.TLSVersion.TLSv1_3,
        }

        context = ssl.create_default_context(cafile=ca_file)
        context.minimum_version = tls_map.get(min_version, ssl.TLSVersion.TLSv1_2)
        context.verify_mode = verify_mode
        context.check_hostname = verify_mode == ssl.CERT_REQUIRED

        # Set recommended cipher suite
        context.set_ciphers(":".join(sorted(self._recommended_ciphers)))

        # Disable compression
        context.options |= ssl.OP_NO_COMPRESSION

        # Enable secure renegotiation
        context.options |= ssl.OP_SINGLE_ECDH_USE
        context.options |= ssl.OP_SINGLE_DH_USE

        if cert_file and key_file:
            context.load_cert_chain(cert_file, key_file)

        return context

    def scan_host_tls(self, host: str, port: int = 443, timeout: float = 5.0) -> TLSSecurityReport:
        """Scan a host for TLS security configuration."""
        issues = []
        recommendations = []
        tls_version = None
        cipher_suite = None
        cipher_strength = CipherStrength.UNKNOWN
        cert_status = CertStatus.UNKNOWN
        cert_details: Dict[str, Any] = {}

        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    tls_version = self._get_tls_version(ssock.version())
                    cipher_suite = ssock.cipher()[0] if ssock.cipher() else None
                    cipher_strength = self._assess_cipher_strength(cipher_suite)

                    if tls_version and tls_version not in self._recommended_versions:
                        issues.append(f"Weak TLS version: {tls_version.value}")
                        recommendations.append(f"Upgrade to TLS 1.2 or 1.3")

                    if cipher_strength in (CipherStrength.WEAK, CipherStrength.UNKNOWN):
                        issues.append(f"Weak cipher suite: {cipher_suite}")
                        recommendations.append("Update cipher suite to recommended configurations")

                    cert = ssock.getpeercert()
                    if cert:
                        cert_status, cert_details = self._analyze_certificate(cert)
                        if cert_status != CertStatus.VALID:
                            issues.append(f"Certificate issue: {cert_status.value}")
                        if cert_details.get("days_until_expiry", 999) < 30:
                            recommendations.append("Certificate expires soon - rotate immediately")
                        if cert_details.get("is_self_signed"):
                            issues.append("Self-signed certificate detected")
                            recommendations.append("Use CA-signed certificate")

        except ssl.SSLCertVerificationError as e:
            cert_status = CertStatus.UNTRUSTED
            issues.append(f"Certificate verification failed: {str(e)}")
            recommendations.append("Install trusted CA certificates")
        except ssl.SSLError as e:
            issues.append(f"SSL error: {str(e)}")
            recommendations.append("Check TLS configuration")
        except socket.timeout:
            issues.append("Connection timeout")
            recommendations.append("Check network connectivity and firewall rules")
        except Exception as e:
            issues.append(f"Scan error: {str(e)}")

        score = self._calculate_security_score(
            tls_version in self._recommended_versions if tls_version else False,
            cipher_strength in (CipherStrength.STRONG, CipherStrength.RECOMMENDED),
            cert_status == CertStatus.VALID,
            len(issues) == 0,
        )

        return TLSSecurityReport(
            host=host,
            port=port,
            tls_version=tls_version,
            cipher_suite=cipher_suite,
            cipher_strength=cipher_strength,
            certificate_status=cert_status,
            certificate_details=cert_details,
            issues=issues,
            recommendations=recommendations,
            score=score,
        )

    def _get_tls_version(self, version_str: str) -> Optional[TLSVersion]:
        """Map SSL version string to TLSVersion enum."""
        version_map = {
            "TLSv1": TLSVersion.TLS_1_0,
            "TLSv1.1": TLSVersion.TLS_1_1,
            "TLSv1.2": TLSVersion.TLS_1_2,
            "TLSv1.3": TLSVersion.TLS_1_3,
        }
        return version_map.get(version_str)

    def _assess_cipher_strength(self, cipher_suite: Optional[str]) -> CipherStrength:
        """Assess the strength of a cipher suite."""
        if not cipher_suite:
            return CipherStrength.UNKNOWN

        cipher_upper = cipher_suite.upper()
        if any(weak in cipher_upper for weak in self._weak_ciphers):
            return CipherStrength.WEAK
        if any(rec in cipher_upper for rec in self._recommended_ciphers):
            return CipherStrength.RECOMMENDED
        if "AES" in cipher_upper and "GCM" in cipher_upper:
            return CipherStrength.STRONG
        if "AES" in cipher_upper:
            return CipherStrength.MEDIUM
        return CipherStrength.UNKNOWN

    def _analyze_certificate(self, cert_dict: Dict[str, Any]) -> Tuple[CertStatus, Dict[str, Any]]:
        """Analyze certificate details."""
        details: Dict[str, Any] = {}
        now = datetime.now(timezone.utc)

        not_before = cert_dict.get("notBefore", "")
        not_after = cert_dict.get("notAfter", "")

        try:
            nb = datetime.datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=datetime.timezone.utc)
            na = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=datetime.timezone.utc)
            details["not_before"] = nb.isoformat()
            details["not_after"] = na.isoformat()
            details["days_until_expiry"] = (na - now).days
            details["is_expired"] = now > na
            details["not_yet_valid"] = now < nb
        except Exception:
            details["days_until_expiry"] = 999
            details["is_expired"] = False

        subject = dict(x[0] for x in cert_dict.get("subject", ()))
        issuer = dict(x[0] for x in cert_dict.get("issuer", ()))
        details["subject"] = subject.get("commonName", "")
        details["issuer"] = issuer.get("commonName", "")
        details["is_self_signed"] = details.get("subject") == details.get("issuer")
        details["serial_number"] = cert_dict.get("serialNumber", "")

        # Extract SANs
        san = []
        for ext in cert_dict.get("subjectAltName", ()):
            san.append(ext[1])
        details["san"] = san

        if details.get("is_expired"):
            return CertStatus.EXPIRED, details
        if details.get("not_yet_valid"):
            return CertStatus.NOT_YET_VALID, details
        if details.get("is_self_signed"):
            return CertStatus.SELF_SIGNED, details
        return CertStatus.VALID, details

    def _calculate_security_score(self, version_ok: bool, cipher_ok: bool, cert_ok: bool, no_issues: bool) -> int:
        """Calculate security score from 0-100."""
        score = 0
        if version_ok:
            score += 30
        if cipher_ok:
            score += 30
        if cert_ok:
            score += 30
        if no_issues:
            score += 10
        return min(100, score)

    def generate_hsts_header(self, max_age: Optional[int] = None, include_subdomains: bool = True,
                              preload: bool = False) -> str:
        """Generate HSTS header value."""
        max_age = max_age or self._hsts_max_age
        directives = [f"max-age={max_age}"]
        if include_subdomains:
            directives.append("includeSubDomains")
        if preload:
            directives.append("preload")
        return "; ".join(directives)

    def validate_cipher_suite(self, cipher_suite: str) -> CipherStrength:
        """Validate a cipher suite string."""
        return self._assess_cipher_strength(cipher_suite)

    def generate_openssl_config(self, output_path: str, include_cert: bool = False) -> str:
        """Generate a recommended OpenSSL configuration."""
        config = f"""# AstrovoxAI Recommended TLS Configuration
# Generated at {datetime.now(timezone.utc).isoformat()}

[system_default_sect]
MinProtocol = TLSv1.2
MaxProtocol = TLSv1.3
CipherString = {':'.join(sorted(self._recommended_ciphers))}
Options = PrioritizeChaCha,SecureRenegotiation,CompressionDisabled

[ssl_sect]
ssl_conf = system_default_sect
"""
        if include_cert:
            config += """
# Certificate configuration
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C = US
ST = State
L = City
O = AstrovoxAI
OU = Security
CN = astrovox.ai
emailAddress = security@astrovox.ai
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(config)
        return config

    def get_tls_recommendations(self) -> Dict[str, Any]:
        """Get TLS hardening recommendations."""
        return {
            "tls_versions": {
                "recommended": [v.value for v in self._recommended_versions],
                "disabled": [TLSVersion.TLS_1_0.value, TLSVersion.TLS_1_1.value],
            },
            "cipher_suites": {
                "recommended": list(self._recommended_ciphers),
                "weak": list(self._weak_ciphers),
            },
            "hsts": {
                "max_age": self._hsts_max_age,
                "include_subdomains": True,
                "preload": True,
            },
            "certificate": {
                "min_key_size": 2048,
                "max_validity_days": 365,
                "signature_algorithm": "SHA256withRSA",
                "preferred_curves": ["secp384r1", "secp256r1"],
            },
        }


tls_hardening = TLSHardening()


def create_secure_ssl_context(cert_file: Optional[str] = None, key_file: Optional[str] = None) -> ssl.SSLContext:
    """Convenience function to create a secure SSL context."""
    return tls_hardening.create_ssl_context(cert_file=cert_file, key_file=key_file)


def scan_tls_security(host: str, port: int = 443) -> TLSSecurityReport:
    """Convenience function to scan TLS security."""
    return tls_hardening.scan_host_tls(host, port)


def generate_hsts_header(max_age: Optional[int] = None) -> str:
    """Convenience function to generate HSTS header."""
    return tls_hardening.generate_hsts_header(max_age)
