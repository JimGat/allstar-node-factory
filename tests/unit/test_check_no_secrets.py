import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / "scripts/check_no_secrets.py"


def load_scanner():
    spec = importlib.util.spec_from_file_location("check_no_secrets", SCANNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_clean_fixtures_documentation_ranges_and_vault_are_allowed(tmp_path: Path) -> None:
    scanner = load_scanner()
    write(tmp_path, "roles/example/defaults/main.yml", "password: fixture-only-123\n")
    write(
        tmp_path,
        "inventories/example/hosts.yml",
        "nets: [192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24]\n",
    )
    write(
        tmp_path,
        "vault/production.yml",
        "$ANSIBLE_VAULT;1.2;AES256;production\n"
        "663132616239386238303932336466616461\n",
    )

    assert scanner.scan_tree(tmp_path) == []


@pytest.mark.parametrize(
    ("content", "rule"),
    [
        ("-----BEGIN OPENSSH PRIVATE KEY-----\n", "private-key"),
        ("ANSIBLE_VAULT_PASSWORD=realvalue\n", "vault-password"),
        ("ICECAST_PASSWORD=not-a-fixture\n", "plaintext-password"),
        ("target: 192.168.50.5\n", "private-topology"),
        ("token: ghp_abcdefghijklmnopqrstuvwxyz123456\n", "token"),
    ],
)
def test_secret_patterns_are_rejected_without_echoing_values(
    tmp_path: Path, content: str, rule: str
) -> None:
    scanner = load_scanner()
    write(tmp_path, "unsafe.yml", content)

    findings = scanner.scan_tree(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == rule
    rendered = findings[0].render()
    assert rendered == f"unsafe.yml:1:{rule}"
    assert content.strip() not in rendered


def test_scanner_skips_git_venv_cache_and_approved_plan_sources(tmp_path: Path) -> None:
    scanner = load_scanner()
    for relative in (
        ".git/config",
        ".venv/secret.yml",
        ".pytest_cache/secret.yml",
        "docs/superpowers/plans/reference.md",
        "docs/superpowers/specs/reference.md",
    ):
        write(tmp_path, relative, "target: 192.168.50.5\n")

    assert scanner.scan_tree(tmp_path) == []


def test_cli_returns_nonzero_and_only_path_line_rule(tmp_path: Path) -> None:
    write(tmp_path, "bad.env", "ANSIBLE_VAULT_PASSWORD=do-not-print-me\n")

    result = subprocess.run(
        [sys.executable, str(SCANNER), str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout.strip() == "bad.env:1:vault-password"
    assert "do-not-print-me" not in result.stdout + result.stderr
