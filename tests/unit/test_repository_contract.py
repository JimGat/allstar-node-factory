from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = {
    ".gitignore",
    ".python-version",
    ".ansible-lint",
    ".yamllint.yml",
    "LICENSE",
    "CHANGELOG.md",
    "ansible.cfg",
    "requirements.yml",
    "requirements-dev.txt",
}


def test_required_repository_files_exist() -> None:
    missing = sorted(path for path in REQUIRED if not (ROOT / path).exists())
    assert missing == []


def test_ansible_cfg_never_names_private_inventory() -> None:
    text = (ROOT / "ansible.cfg").read_text(encoding="utf-8")
    assert "allstar-node-inventory" not in text
    assert "vault-production.key" not in text
