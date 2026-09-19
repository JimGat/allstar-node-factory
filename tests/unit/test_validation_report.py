import json
from pathlib import Path

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[2]
REPORT_TEMPLATE = ROOT / "roles/validation/templates/report.json.j2"
BACKUP_DEFAULTS = ROOT / "roles/backup/defaults/main.yml"
BACKUP_TASKS = ROOT / "roles/backup/tasks/main.yml"
VALIDATION_DEFAULTS = ROOT / "roles/validation/defaults/main.yml"
VALIDATION_TASKS = ROOT / "roles/validation/tasks/main.yml"
ALLOWED = {"PASS", "FAIL", "NOT_APPLICABLE", "INIT_REQUIRED"}


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def task_by_name(tasks: list[dict], name: str) -> dict:
    for task in tasks:
        if task.get("name") == name:
            return task
    raise LookupError(name)


def test_report_is_valid_redacted_status_only_json() -> None:
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPORT_TEMPLATE.parent)),
        undefined=jinja2.StrictUndefined,
    )
    environment.filters["to_json"] = json.dumps
    rendered = environment.get_template(REPORT_TEMPLATE.name).render(
        asl_node_number="1998",
        validation_generated_at="2026-09-06T12:00:00Z",
        validation_overall_status="FAIL",
        validation_checks={
            "asterisk": "PASS",
            "allscan": "INIT_REQUIRED",
            "broadcastify": "NOT_APPLICABLE",
            "backup": "FAIL",
        },
        validation_backup_metadata={
            "path": "/var/backups/allstar-node-factory/node-1998-20260906T120000Z.tar.gz",
            "timestamp": "2026-09-06T12:00:00Z",
            "size": 1234,
            "checksum": "a" * 64,
        },
        vault_asl_node_password="fixture-only-123",
        asterisk_stdout="fixture-only-123",
        process_environment="fixture-only-123",
    )
    report = json.loads(rendered)

    assert report["node"] == "1998"
    assert report["checks"]["asterisk"] == "PASS"
    assert set(report["checks"].values()) <= ALLOWED
    assert set(report["backup"]) == {"path", "timestamp", "size", "checksum"}
    assert "fixture-only-123" not in rendered
    assert "stdout" not in rendered
    assert "environment" not in rendered


def test_backup_defaults_are_restricted_and_retain_five() -> None:
    defaults = load_yaml(BACKUP_DEFAULTS)

    assert defaults["backup_root"] == "/var/backups/allstar-node-factory"
    assert defaults["backup_retain_count"] == 5
    assert defaults["backup_paths"] == [
        "/etc/asterisk",
        "/etc/allmon3",
        "/etc/allscan",
        "/etc/ufw",
        "/etc/systemd/system",
    ]


def test_backup_check_mode_exits_before_runtime_archive_checks() -> None:
    tasks = load_yaml(BACKUP_TASKS)
    names = [task["name"] for task in tasks]
    exit_task = task_by_name(tasks, "End the backup role after check-mode validation")

    assert exit_task["ansible.builtin.meta"] == "end_role"
    assert exit_task["when"] == "ansible_check_mode"
    assert names.index("End the backup role after check-mode validation") < names.index(
        "Inspect the native ASL backup command"
    )


def test_backup_archives_only_existing_paths_and_protects_secret_material() -> None:
    tasks = load_yaml(BACKUP_TASKS)
    archive = task_by_name(tasks, "Create the supplemental integration archive")
    checksum = task_by_name(tasks, "Write the supplemental archive checksum")
    native = task_by_name(tasks, "Create the native ASL configuration backup")

    assert archive["community.general.archive"]["path"] == "{{ backup_existing_paths }}"
    assert archive["community.general.archive"]["mode"] == "0600"
    assert archive["no_log"] is True
    assert archive["diff"] is False
    assert checksum["ansible.builtin.copy"]["mode"] == "0600"
    assert checksum["no_log"] is True
    assert native["ansible.builtin.command"]["argv"] == [
        "asl-backup-menu",
        "backup-local",
    ]


def test_validation_writes_redacted_report_before_failure_gate() -> None:
    tasks = load_yaml(VALIDATION_TASKS)
    names = [task["name"] for task in tasks]
    write_index = names.index("Write the redacted validation report")
    fail_index = names.index("Fail after preserving validation evidence")
    write = tasks[write_index]

    assert write_index < fail_index
    assert write["ansible.builtin.template"]["mode"] == "0640"
    assert write["ansible.builtin.template"]["dest"].endswith("/latest.json")
    assert write["no_log"] is True
    assert write["diff"] is False


def test_validation_is_read_only_and_has_bounded_status_defaults() -> None:
    defaults = load_yaml(VALIDATION_DEFAULTS)
    tasks = load_yaml(VALIDATION_TASKS)
    rendered = json.dumps(tasks)

    assert defaults["validation_allowed_statuses"] == sorted(ALLOWED)
    assert "core show uptime" in rendered
    assert "rpt show registrations" in rendered
    assert "asl-node-auth-check" in rendered
    assert "asl-check-install" in rendered
    assert "ss" in rendered
    assert "journalctl" not in rendered
    for task in tasks:
        command = task.get("ansible.builtin.command")
        if command:
            assert task.get("changed_when") is False
