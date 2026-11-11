#!/usr/bin/env python3
"""Verify that a framework checkout exactly matches its private lock file."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import yaml

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def validate_pin(lock: dict[str, Any], head: str, dirty: bool) -> list[str]:
    """Return lock errors without exposing repository contents or secrets."""
    if not isinstance(lock, dict):
        return ["framework lock must be a YAML mapping"]

    errors: list[str] = []
    for key in ("repository", "ref", "commit"):
        if not isinstance(lock.get(key), str) or not lock[key].strip():
            errors.append(f"framework lock {key} is required")

    expected = lock.get("commit")
    if isinstance(expected, str) and not FULL_SHA.fullmatch(expected):
        errors.append("expected commit must be a full lowercase 40-character SHA")
    elif isinstance(expected, str) and head.strip() != expected:
        errors.append(f"framework HEAD mismatch: expected {expected}, actual {head.strip()}")

    if dirty:
        errors.append("framework checkout is dirty")
    return errors


def _git(framework: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(framework), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        lock = yaml.safe_load(args.lock.read_text(encoding="utf-8"))
        head = _git(args.framework, "rev-parse", "HEAD").strip()
        dirty = bool(_git(args.framework, "status", "--porcelain").strip())
    except (OSError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print(f"framework pin check unavailable: {type(exc).__name__}", file=sys.stderr)
        return 1

    errors = validate_pin(lock, head, dirty)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"framework pin: OK ({head}, clean)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
