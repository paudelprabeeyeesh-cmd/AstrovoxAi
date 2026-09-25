#!/usr/bin/env python3
"""
Changelog validation tool.
Validates CHANGELOG.md format and structure.
"""

import re
import sys
from datetime import datetime


class ChangelogValidator:
    """Validates CHANGELOG.md format and structure."""

    def __init__(self, filepath="CHANGELOG.md"):
        self.filepath = filepath
        self.errors = []
        self.warnings = []

    def validate(self):
        """Run all validations."""
        with open(self.filepath, "r") as f:
            content = f.read()

        self._check_header(content)
        self._check_versions(content)
        self._check_links(content)
        self._check_dates(content)
        self._check_structure(content)
        self._check_conventional_commits(content)

        return self.errors, self.warnings

    def _check_header(self, content):
        """Check that the changelog has a proper header."""
        if not content.startswith("# Changelog"):
            self.errors.append("Changelog must start with '# Changelog' header")
        if "All notable changes" not in content:
            self.errors.append("Changelog must contain introductory text about notable changes")

    def _check_versions(self, content):
        """Check that versions follow semantic versioning."""
        pattern = r"^## \[(\d+\.\d+\.\d+)\]"
        versions = re.findall(pattern, content, re.MULTILINE)

        if not versions:
            self.errors.append("Changelog must contain at least one version entry")
            return

        for i, version in enumerate(versions):
            parts = version.split(".")
            if len(parts) != 3:
                self.errors.append(f"Version {version} is not valid semver (must be X.Y.Z)")
                continue

            for part in parts:
                if not part.isdigit():
                    self.errors.append(f"Version {version} contains non-numeric parts")
                    break

    def _check_links(self, content):
        """Check that versions have proper anchor links."""
        pattern = r"^## \[(\d+\.\d+\.\d+)\]"
        versions = re.findall(pattern, content, re.MULTILINE)

        for version in versions:
            anchor = f"[{version}]"
            link_pattern = f"\\[unreleased\\]:.*\n.*{version}"
            if not re.search(link_pattern, content):
                self.warnings.append(f"Version {version} should have an anchor link")

    def _check_dates(self, content):
        """Check that versions have dates."""
        pattern = r"^## \[(\d+\.\d+\.\d+)\] — ([^\(]+)"
        entries = re.findall(pattern, content, re.MULTILINE)

        for version, date_str in entries:
            date_str = date_str.strip()
            if not date_str:
                self.errors.append(f"Version {version} is missing a date")
                continue

            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                self.warnings.append(f"Version {version} has an unusual date format: {date_str}")

    def _check_structure(self, content):
        """Check that versions have proper subsections."""
        required_sections = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]

        pattern = r"^## \[(\d+\.\d+\.\d+)\]"
        versions = re.findall(pattern, content, re.MULTILINE)

        for version in versions:
            version_section = re.search(rf"## \[{re.escape(version)}\].*?(?=## \[|\Z)", content, re.DOTALL)
            if version_section:
                section_content = version_section.group(0)
                for section in required_sections:
                    if section in section_content:
                        # Check that sections have content
                        section_pattern = rf"### {section}\n(.*?)(?=### |\Z)"
                        section_match = re.search(section_pattern, section_content, re.DOTALL)
                        if section_match:
                            section_text = section_match.group(1).strip()
                            if not section_text:
                                self.warnings.append(f"Version {version} has empty '{section}' section")

    def _check_conventional_commits(self, content):
        """Check that entries follow conventional commit format."""
        pattern = r"^## \[(\d+\.\d+\.\d+)\]"
        versions = re.findall(pattern, content, re.MULTILINE)

        for version in versions:
            version_section = re.search(rf"## \[{re.escape(version)}\].*?(?=## \[|\Z)", content, re.DOTALL)
            if version_section:
                section_content = version_section.group(0)
                # Check for proper section headers
                if "### Added" not in section_content and "### Fixed" not in section_content:
                    self.warnings.append(f"Version {version} should have at least 'Added' or 'Fixed' sections")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate CHANGELOG.md format")
    parser.add_argument("file", nargs="?", default="CHANGELOG.md", help="Path to changelog file")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    validator = ChangelogValidator(args.file)
    errors, warnings = validator.validate()

    if errors:
        print("❌ Changelog validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    if warnings:
        print("⚠️ Changelog validation warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        if args.strict:
            sys.exit(1)

    print("✅ Changelog is valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
