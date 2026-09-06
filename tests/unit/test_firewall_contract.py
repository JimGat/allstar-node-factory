from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_PATH = ROOT / "roles/firewall/defaults/main.yml"
TASKS_PATH = ROOT / "roles/firewall/tasks/main.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def task_by_name(tasks: list[dict], name: str) -> dict:
    return next(task for task in tasks if task.get("name") == name)


def test_firewall_defaults_define_feature_flags() -> None:
    defaults = load_yaml(DEFAULTS_PATH)
    assert defaults == {
        "echolink_enabled": False,
        "web_public_enabled": False,
        "web_tls_enabled": False,
    }


def test_firewall_requires_non_empty_management_cidrs() -> None:
    tasks = load_yaml(TASKS_PATH)
    task = task_by_name(tasks, "Validate firewall management access")
    assertions = task["ansible.builtin.assert"]["that"]
    assert "management_cidrs is defined" in assertions
    assert "management_cidrs is sequence" in assertions
    assert "management_cidrs is not string" in assertions
    assert "management_cidrs | length > 0" in assertions


def test_firewall_installs_ufw_and_sets_default_policies() -> None:
    tasks = load_yaml(TASKS_PATH)
    install = task_by_name(tasks, "Install UFW")
    assert install["ansible.builtin.apt"]["name"] == "ufw"
    assert install["ansible.builtin.apt"]["state"] == "present"

    incoming = task_by_name(tasks, "Deny incoming traffic by default")
    assert incoming["community.general.ufw"] == {
        "default": "deny",
        "direction": "incoming",
    }
    outgoing = task_by_name(tasks, "Allow outgoing traffic by default")
    assert outgoing["community.general.ufw"] == {
        "default": "allow",
        "direction": "outgoing",
    }


def test_ssh_is_allowed_per_management_cidr_before_ufw_is_enabled() -> None:
    tasks = load_yaml(TASKS_PATH)
    ssh = task_by_name(tasks, "Allow SSH from management networks")
    assert ssh["community.general.ufw"] == {
        "rule": "allow",
        "port": "22",
        "proto": "tcp",
        "src": "{{ item }}",
    }
    assert ssh["loop"] == "{{ management_cidrs }}"

    ssh_index = tasks.index(ssh)
    enable_index = tasks.index(task_by_name(tasks, "Enable UFW"))
    assert ssh_index < enable_index


def test_public_service_rules_are_scoped_and_conditional() -> None:
    tasks = load_yaml(TASKS_PATH)

    iax = task_by_name(tasks, "Allow public AllStarLink IAX traffic")
    assert iax["community.general.ufw"] == {
        "rule": "allow",
        "port": "{{ asl_iax_port }}",
        "proto": "udp",
        "src": "0.0.0.0/0",
    }

    echolink = task_by_name(tasks, "Allow public EchoLink audio traffic")
    assert echolink["community.general.ufw"] == {
        "rule": "allow",
        "port": "{{ item }}",
        "proto": "udp",
        "src": "0.0.0.0/0",
    }
    assert echolink["loop"] == ["5198", "5199"]
    assert echolink["when"] == "echolink_enabled | bool"

    http = task_by_name(tasks, "Allow public HTTP traffic")
    assert http["community.general.ufw"]["port"] == "80"
    assert http["community.general.ufw"]["proto"] == "tcp"
    assert http["when"] == "web_public_enabled | bool"

    https = task_by_name(tasks, "Allow public HTTPS traffic")
    assert https["community.general.ufw"]["port"] == "443"
    assert https["community.general.ufw"]["proto"] == "tcp"
    assert https["when"] == [
        "web_public_enabled | bool",
        "web_tls_enabled | bool",
    ]


def test_firewall_never_opens_tcp_5038() -> None:
    serialized = TASKS_PATH.read_text(encoding="utf-8")
    assert "5038" not in serialized


def test_ufw_status_is_verbose_registered_and_read_only() -> None:
    tasks = load_yaml(TASKS_PATH)
    status = task_by_name(tasks, "Read verbose UFW status")
    assert status["ansible.builtin.command"]["cmd"] == "ufw status verbose"
    assert status["changed_when"] is False
    assert status["register"] == "firewall_ufw_status"
