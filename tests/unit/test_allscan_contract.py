from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_PATH = ROOT / "roles/allscan/defaults/main.yml"
TASKS_PATH = ROOT / "roles/allscan/tasks/main.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def task_by_name(tasks: list[dict], name: str) -> dict:
    for task in tasks:
        if task.get("name") == name:
            return task
        for section in ("block", "always", "rescue"):
            nested = task.get(section, [])
            if nested:
                try:
                    return task_by_name(nested, name)
                except LookupError:
                    pass
    raise LookupError(name)


def test_allscan_role_uses_pinned_safe_deployment() -> None:
    defaults = load_yaml(DEFAULTS_PATH)
    serialized_tasks = TASKS_PATH.read_text(encoding="utf-8")

    assert defaults["allscan_commit"] == "0309f2ff8fc5d2baf1c1df1afc13acb59781cd97"
    assert "AllScanInstallUpdate.php" not in serialized_tasks
    assert "https://github.com/davidgsd/AllScan/archive/" in serialized_tasks
    assert "/etc/allscan" in serialized_tasks
    assert "/var/www/html/allscan" in serialized_tasks


def test_allscan_public_web_requires_tls_and_the_restricted_allmon_vhost() -> None:
    tasks = load_yaml(TASKS_PATH)
    validation = task_by_name(tasks, "Validate AllScan deployment settings and first-run gate")
    assertions = "\n".join(validation["ansible.builtin.assert"]["that"])

    assert "not (web_public_enabled" in assertions
    assert "web_tls_enabled" in assertions
    assert "allmon3_enabled" in assertions


def test_allscan_check_mode_exits_before_temporary_archive_workspace() -> None:
    tasks = load_yaml(TASKS_PATH)
    deploy = task_by_name(tasks, "Deploy optional AllScan")
    names = [task["name"] for task in deploy["block"]]
    exit_task = task_by_name(
        tasks,
        "End the AllScan role after check-mode configuration validation",
    )

    assert exit_task["ansible.builtin.meta"] == "end_role"
    assert exit_task["when"] == "ansible_check_mode"
    assert names.index("Preserve existing user INI files in memory") < names.index(
        "End the AllScan role after check-mode configuration validation"
    )
    assert names.index(
        "End the AllScan role after check-mode configuration validation"
    ) < names.index("Create the AllScan deployment workspace")


def test_allscan_replaces_stale_application_only_after_verified_unpack() -> None:
    tasks = load_yaml(TASKS_PATH)
    install = task_by_name(tasks, "Install the reviewed AllScan archive")
    names = [task["name"] for task in install["block"]]

    assert names.index("Unpack the pinned AllScan archive") < names.index(
        "Discover stale AllScan application entries"
    )
    assert names.index("Discover stale AllScan application entries") < names.index(
        "Remove stale AllScan application entries"
    )
    assert names.index("Remove stale AllScan application entries") < names.index(
        "Synchronize pinned AllScan application files"
    )

    cleanup = task_by_name(tasks, "Remove stale AllScan application entries")
    assert cleanup["ansible.builtin.file"]["state"] == "absent"
    assert cleanup["loop"] == "{{ allscan_stale_application_entries.files }}"


def test_allscan_preserves_database_and_blocks_sensitive_http_paths() -> None:
    tasks_text = TASKS_PATH.read_text(encoding="utf-8")
    policy = (ROLE_DIR := ROOT / "roles/allscan").joinpath(
        "templates/allscan-security.conf.j2"
    ).read_text(encoding="utf-8")

    assert "/etc/allscan/allscan.db" in tasks_text
    assert "state: absent" not in "\n".join(
        line for line in tasks_text.splitlines() if "allscan.db" in line
    )
    assert "_tools" in policy
    for suffix in ("ini", "db", "bak"):
        assert suffix in policy
    assert "Require all denied" in policy


def test_allscan_database_remains_private_but_writable_by_apache() -> None:
    tasks = load_yaml(TASKS_PATH)
    directory = task_by_name(tasks, "Create the persistent AllScan configuration directory")
    database = task_by_name(
        tasks,
        "Set private writable permissions on the persistent AllScan database",
    )

    assert directory["ansible.builtin.file"]["owner"] == "root"
    assert directory["ansible.builtin.file"]["group"] == "{{ allscan_web_group }}"
    assert directory["ansible.builtin.file"]["mode"] == "0770"
    assert database["ansible.builtin.file"] == {
        "path": "/etc/allscan/allscan.db",
        "owner": "root",
        "group": "{{ allscan_web_group }}",
        "mode": "0660",
    }


def test_allscan_health_has_only_documented_states() -> None:
    tasks = load_yaml(TASKS_PATH)
    health = task_by_name(tasks, "Record the local AllScan health result")
    expression = health["ansible.builtin.set_fact"]["allscan_local_health"]

    assert "'PASS'" in expression
    assert "'INIT_REQUIRED'" in expression
    assert "'FAIL'" in expression
