#!/usr/bin/env python3
"""Detect secrets and private topology without echoing matches."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import NamedTuple


class Finding(NamedTuple):
    path: str
    line: int
    rule: str

    def render(self) -> str:
        return f"{self.path}:{self.line}:{self.rule}"


TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".conf",
    ".env",
    ".ini",
    ".j2",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".bash",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
}
SKIP_PARTS = {".git", ".venv", ".pytest_cache", "__pycache__"}
SKIP_PATHS = {
    Path("scripts/check_no_secrets.py"),
    Path("tests/unit/test_check_no_secrets.py"),
}
SKIP_PREFIXES = (
    Path("docs/superpowers/plans"),
    Path("docs/superpowers/specs"),
)
VAULT_HEADER = re.compile(r"^\$ANSIBLE_VAULT;1\.2;AES256;production$")
RULES = (
    ("private-key", re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----")),
    ("vault-password", re.compile(r"(?i)\bANSIBLE_VAULT_PASSWORD\s*=")),
    ("token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b")),
    (
        "private-topology",
        re.compile(
            r"(?<![0-9])(?:10(?:\.[0-9]{1,3}){3}|"
            r"172\.(?:1[6-9]|2[0-9]|3[01])(?:\.[0-9]{1,3}){2}|"
            r"192\.168(?:\.[0-9]{1,3}){2})(?![0-9])"
        ),
    ),
)
PLAINTEXT_CREDENTIAL = re.compile(
    r"^\s*(?:"
    r"(?:export\s+)?(?!VAULT_)[A-Z][A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET)\s*=|"
    r"(?!vault_)[A-Za-z][A-Za-z0-9_]*(?:password|passwd|secret)\s*:"
    r")\s*(?P<value>[^\s#,'\"}\]]+)"
)


def _is_skipped(relative: Path) -> bool:
    if any(part in SKIP_PARTS for part in relative.parts):
        return True
    if relative in SKIP_PATHS:
        return True
    return any(relative == prefix or prefix in relative.parents for prefix in SKIP_PREFIXES)


def _text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if _is_skipped(relative) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path, relative


def scan_tree(root: Path | str) -> list[Finding]:
    root = Path(root).resolve()
    findings: list[Finding] = []
    for path, relative in _text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        if lines and VAULT_HEADER.fullmatch(lines[0]):
            continue
        for line_number, line in enumerate(lines, start=1):
            matched_rules: set[str] = set()
            for rule, pattern in RULES:
                if pattern.search(line):
                    findings.append(Finding(relative.as_posix(), line_number, rule))
                    matched_rules.add(rule)
            credential = PLAINTEXT_CREDENTIAL.search(line)
            if credential and "vault-password" not in matched_rules:
                value = credential.group("value")
                if not (
                    value.startswith("fixture-only-")
                    or value.startswith("{{")
                    or value in {"null", "none", "false", "true"}
                ):
                    findings.append(
                        Finding(relative.as_posix(), line_number, "plaintext-password")
                    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    findings = scan_tree(args.root)
    for finding in findings:
        print(finding.render())
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
