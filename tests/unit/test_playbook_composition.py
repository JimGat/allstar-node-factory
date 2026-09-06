from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS = ROOT / "playbooks"
EXPECTED = [
    "backup",
    "asl3_core",
    "permanent_link",
    "echolink",
    "broadcastify",
    "allmon3",
    "allscan",
    "firewall",
    "validation",
]
EXPECTED_TAGS = {
    "backup",
    "core",
    "links",
    "echolink",
    "broadcastify",
    "web",
    "firewall",
    "validate",
}


def load_playbook(name: str) -> list[dict]:
    return yaml.safe_load((PLAYBOOKS / name).read_text(encoding="utf-8"))


def role_name(entry: str | dict) -> str:
    return entry if isinstance(entry, str) else entry["role"]


def test_vultr_hub_composes_roles_in_safe_order() -> None:
    plays = load_playbook("vultr-hub.yml")

    assert len(plays) == 1
    play = plays[0]
    assert [role_name(role) for role in play["roles"]] == EXPECTED
    assert play["hosts"] == "allstar_nodes"
    assert play["become"] is True
    assert play["gather_facts"] is True
    assert play["serial"] == 1
    assert play["any_errors_fatal"] is True


def test_vultr_hub_has_explicit_activation_gate_and_role_tags() -> None:
    play = load_playbook("vultr-hub.yml")[0]
    pre_tasks = play["pre_tasks"]
    rendered = yaml.safe_dump(pre_tasks)
    tags: set[str] = set()
    for role in play["roles"]:
        tags.update(role.get("tags", []))

    assert "production_services_enabled is defined" in rendered
    assert "production_services_enabled is boolean" in rendered
    assert tags == EXPECTED_TAGS


def test_validation_entry_point_runs_only_validation_read_only_role() -> None:
    play = load_playbook("validate.yml")[0]

    assert [role_name(role) for role in play["roles"]] == ["validation"]
    assert play["hosts"] == "allstar_nodes"
    assert play["become"] is True
    assert play["serial"] == 1
    assert play["any_errors_fatal"] is True
    assert "handlers" not in play


def test_backup_entry_point_runs_only_backup_role() -> None:
    play = load_playbook("backup.yml")[0]

    assert [role_name(role) for role in play["roles"]] == ["backup"]
    assert play["hosts"] == "allstar_nodes"
    assert play["become"] is True
    assert play["serial"] == 1
    assert play["any_errors_fatal"] is True
