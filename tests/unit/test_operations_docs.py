from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = [
    ROOT / "docs/migration/hamvoip-to-asl3.md",
    ROOT / "docs/operations/vultr-cutover.md",
    ROOT / "docs/operations/backup-restore.md",
    ROOT / "docs/profiles/vultr-radioless-hub.md",
    ROOT / "docs/security/secrets.md",
]
PROMPT = ROOT / "prompts/inventory-legacy-node.md"
SKILL = ROOT / "skills/allstar-node-operations/SKILL.md"
COMMAND_REQUIRED = (
    "-i ../allstar-node-inventory/inventory/hosts.yml",
    "--limit cloud-hub",
    "--vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key",
    "--extra-vars @../allstar-node-inventory/topology/permanent-links.yml",
    "--extra-vars @../allstar-node-inventory/vault/production.yml",
)


def test_operator_documents_exist_and_have_copy_paste_commands() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    commands = re.findall(r"```bash\n(.*?ansible-playbook.*?)\n```", text, re.DOTALL)

    assert commands
    for command in commands:
        for required in COMMAND_REQUIRED:
            assert required in command
    assert "playbooks/vultr-hub.yml" in text
    assert "playbooks/validate.yml" in text
    assert "playbooks/backup.yml" in text
    assert "Expected:" in text


def test_migration_matrix_is_complete_and_forbids_wholesale_copy() -> None:
    text = DOCS[0].read_text(encoding="utf-8")

    assert "| Legacy evidence | ASL3 destination | Secret | Activation gate | Verified |" in text
    for item in (
        "node/server identity",
        "ports/codecs",
        "DTMF/functions/macros",
        "EchoLink",
        "Broadcastify",
        "permanent-link ownership",
        "custom sounds",
        "cron/systemd",
        "sockets/firewall",
    ):
        assert item.lower() in text.lower()
    assert "do not copy" in text.lower()
    assert "wholesale" in text.lower()


def test_cutover_rollback_names_every_identity_bearing_service() -> None:
    text = (ROOT / "docs/operations/vultr-cutover.md").read_text(encoding="utf-8")

    for service in ("Asterisk", "EchoLink", "Broadcastify"):
        assert service in text
    assert "production_services_enabled: false" in text
    assert "production_services_enabled: true" in text
    assert "stop the new" in text.lower()
    assert "start the old" in text.lower()
    assert "do not delete" in text.lower()


def test_inventory_prompt_is_read_only_and_evidence_bounded() -> None:
    text = PROMPT.read_text(encoding="utf-8")

    assert "read-only" in text.lower()
    assert "Do not restart" in text
    assert "Do not display secrets" in text
    assert "captured" in text
    assert "not used" in text
    assert "not present" in text


def test_project_skill_metadata_and_sections() -> None:
    text = SKILL.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.+)$", text, re.DOTALL)
    assert match
    metadata = yaml.safe_load(match.group(1))
    body = match.group(2).strip()

    assert metadata["name"] == "allstar-node-operations"
    assert len(metadata["description"]) <= 60
    assert metadata["version"] == "0.1.0"
    assert metadata["author"] == "Jim Gatwood, Hermes Agent"
    assert metadata["license"] == "MIT"
    assert metadata["platforms"] == ["linux"]
    assert metadata["metadata"]["hermes"]["tags"]
    assert body
    for section in (
        "## When to Use",
        "## Prerequisites",
        "## How to Run",
        "## Procedure",
        "## Pitfalls",
        "## Verification",
    ):
        assert section in body
    assert "fixture-only-123" not in body
    assert not re.search(r"\b[0-9]{4,6}\b", body)
