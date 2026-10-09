import unittest

from data_pipeline.pii_scrubbing import NERScrubber, PIIRegexScrubber


class TestPIIRegexScrubber(unittest.TestCase):
    def test_find_email(self):
        scrubber = PIIRegexScrubber()
        result = scrubber.find("Contact me at test@example.com")
        self.assertIn("email", result)
        self.assertEqual(result["email"], ["test@example.com"])

    def test_find_phone(self):
        scrubber = PIIRegexScrubber()
        result = scrubber.find("Call 555-123-4567")
        self.assertIn("phone", result)

    def test_find_ssn(self):
        scrubber = PIIRegexScrubber()
        result = scrubber.find("SSN: 123-45-6789")
        self.assertIn("ssn", result)
        self.assertEqual(result["ssn"], ["123-45-6789"])

    def test_redact_email(self):
        scrubber = PIIRegexScrubber()
        result = scrubber.redact("Email test@example.com here")
        self.assertIn("[REDACTED]", result)
        self.assertNotIn("test@example.com", result)

    def test_redact_phone(self):
        scrubber = PIIRegexScrubber()
        result = scrubber.redact("Phone 555-123-4567")
        self.assertIn("[REDACTED]", result)

    def test_redact_ssn(self):
        scrubber = PIIRegexScrubber()
        result = scrubber.redact("SSN 123-45-6789")
        self.assertIn("[REDACTED]", result)

    def test_find_no_pii(self):
        scrubber = PIIRegexScrubber()
        result = scrubber.find("No PII here")
        self.assertEqual(result, {})


class TestNERScrubber(unittest.TestCase):
    def test_find_email(self):
        scrubber = NERScrubber()
        result = scrubber.find("Email test@example.com")
        emails = [e for e in result if e["label"] == "EMAIL"]
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["text"], "test@example.com")

    def test_find_phone(self):
        scrubber = NERScrubber()
        result = scrubber.find("Phone 555-123-4567")
        phones = [e for e in result if e["label"] == "PHONE"]
        self.assertEqual(len(phones), 1)

    def test_find_ssn(self):
        scrubber = NERScrubber()
        result = scrubber.find("SSN 123-45-6789")
        ssns = [e for e in result if e["label"] == "SSN"]
        self.assertEqual(len(ssns), 1)
        self.assertEqual(ssns[0]["text"], "123-45-6789")

    def test_find_no_pii(self):
        scrubber = NERScrubber()
        result = scrubber.find("No PII here")
        self.assertEqual(result, [])
