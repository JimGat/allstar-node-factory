import base64
from pathlib import Path
import re

from jinja2 import Environment, StrictUndefined
import yaml


TEMPLATE_DIR = Path(__file__).parents[2] / "roles" / "asl3_core" / "templates"


def render_template(name, **context):
    environment = Environment(undefined=StrictUndefined)
    environment.filters["bool"] = bool
    template = environment.from_string((TEMPLATE_DIR / name).read_text())
    return template.render(**context)


def test_asl3_core_templates_render_required_configuration():
    context = {
        "asl_node_number": 1998,
        "asl_callsign": "N0CALL",
        "asl_iax_port": 4569,
        "asl_rxchannel": "Local/pseudo",
        "vault_asl_node_password": "fixture-only-123",
        "vault_ami_secret": "fixture-only-123",
        "permanent_link_enabled": False,
        "permanent_link_initiator": "disabled",
        "permanent_link_peer_node": 1999,
        "private_node_routes": {},
    }

    rpt = render_template("rpt-node-factory.conf.j2", **context)
    registrations = render_template(
        "rpt_http_registrations.conf.j2", **context
    )
    manager = render_template("manager-node-factory.conf.j2", **context)

    assert "[1998](node-main)" in rpt
    assert "rxchannel = Local/pseudo" in rpt
    assert (
        "register => 1998:fixture-only-123@register.allstarlink.org"
        in registrations
    )
    assert "bindaddr = 127.0.0.1" in manager
    assert "secret = fixture-only-123" in manager
    assert "register =>" not in rpt
    assert "startup_macro" not in rpt


def test_startup_macro_is_rendered_only_for_local_initiator():
    context = {
        "asl_node_number": 1998,
        "asl_callsign": "N0CALL",
        "asl_iax_port": 4569,
        "asl_rxchannel": "Local/pseudo",
        "permanent_link_enabled": True,
        "permanent_link_peer_node": 1999,
        "private_node_routes": {},
    }

    local = render_template(
        "rpt-node-factory.conf.j2",
        permanent_link_initiator="local",
        **context,
    )
    remote = render_template(
        "rpt-node-factory.conf.j2",
        permanent_link_initiator="remote",
        **context,
    )

    assert "startup_macro = *8131999" in local
    assert "startup_macro" not in remote


def test_repository_bootstrap_is_materialized_during_check_mode() -> None:
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    names = {
        "Download the pinned ASL3 repository package",
        "Install the ASL3 repository package",
        "Refresh the ASL3 repository package index",
    }
    bootstrap = {task["name"]: task for task in tasks if task.get("name") in names}

    assert set(bootstrap) == names
    assert all(task["check_mode"] is False for task in bootstrap.values())
    assert bootstrap["Refresh the ASL3 repository package index"][
        "ansible.builtin.apt"
    ]["update_cache"] is True


def test_hostname_default_is_version_neutral_and_managed() -> None:
    role_dir = TEMPLATE_DIR.parent
    defaults = yaml.safe_load(
        (role_dir / "defaults" / "main.yml").read_text(encoding="utf-8")
    )
    tasks = yaml.safe_load(
        (role_dir / "tasks" / "main.yml").read_text(encoding="utf-8")
    )
    hostname_task = next(
        task for task in tasks if task.get("name") == "Set the version-neutral ASL hostname"
    )
    hosts_task = next(
        task for task in tasks if task.get("name") == "Map the version-neutral ASL hostname locally"
    )

    assert defaults["asl_hostname"] == "asl-node-{{ asl_node_number }}"
    assert hostname_task["ansible.builtin.hostname"]["name"] == "{{ asl_hostname }}"
    assert hosts_task["ansible.builtin.lineinfile"]["line"] == "127.0.1.1 {{ asl_hostname }}"


def test_privilege_probe_runs_during_check_mode() -> None:
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    probe = next(
        task
        for task in tasks
        if task.get("name") == "Verify privilege escalation reaches root"
    )

    assert probe["check_mode"] is False
    assert probe["changed_when"] is False


def test_production_activation_explicitly_starts_and_enables_asterisk():
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))

    activation_tasks = [
        task
        for task in tasks
        if task.get("ansible.builtin.service", {}).get("name") == "asterisk"
        and task.get("when") == "production_services_enabled | bool"
    ]

    assert any(
        task["ansible.builtin.service"].get("state") == "started"
        and task["ansible.builtin.service"].get("enabled") is True
        for task in activation_tasks
    )


def test_duplicate_node_guard_catches_inherited_stanzas():
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    guard = next(
        task
        for task in tasks
        if task.get("name") == "Reject an unmanaged duplicate node stanza"
    )
    assertion = guard["ansible.builtin.assert"]["that"][0]

    assert "(?:\\\\([^\\\\]\\\\r\\\\n]*\\\\))?" in assertion


def test_package_install_always_suppresses_early_service_start():
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    install = next(
        task
        for task in tasks
        if task.get("name") == "Install ASL3 without activating staging services"
    )

    assert install["ansible.builtin.apt"]["policy_rc_d"] == 101


def test_ami_guard_accepts_official_loopback_configuration() -> None:
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    guard = next(
        task for task in tasks if task.get("name") == "Assert packaged AMI is bound to loopback"
    )
    environment = Environment(undefined=StrictUndefined)
    environment.filters["b64decode"] = lambda value: base64.b64decode(value).decode()
    environment.tests["regex"] = lambda value, pattern: re.search(pattern, value) is not None

    def accepted(content: str) -> bool:
        encoded = base64.b64encode(content.encode()).decode()
        context = {"asl3_core_manager_conf": {"content": encoded}}
        return all(
            environment.compile_expression(assertion)(**context)
            for assertion in guard["ansible.builtin.assert"]["that"]
        )

    safe = """[general]
enabled = yes
port = 5038
bindaddr = 127.0.0.1

[admin]
secret = fixture-only
"""
    assert accepted(safe)
    assert not accepted(safe.replace("127.0.0.1", "0.0.0.0"))
    assert not accepted(safe.replace("bindaddr = 127.0.0.1", "bindaddr = 127.0.0.1\nbindaddr = ::"))


def test_ami_guard_rejects_any_non_loopback_bind():
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    guard = next(
        task for task in tasks if task.get("name") == "Assert packaged AMI is bound to loopback"
    )
    assertions = "\n".join(guard["ansible.builtin.assert"]["that"])

    assert "is not regex" in assertions
    assert "bindaddr" in assertions
    assert "127\\\\.0\\\\.0\\\\.1" in assertions


def test_dahdi_guard_rejects_preload_and_autoload():
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    guard = next(
        task
        for task in tasks
        if task.get("name") == "Validate radioless Asterisk module defaults"
    )
    assertions = "\n".join(guard["ansible.builtin.assert"]["that"])

    assert "(?:pre)?load" in assertions
    assert "autoload" in assertions
    assert "dahdi" in assertions.lower()


def test_radioless_module_guard_accepts_official_commented_syntax() -> None:
    tasks_path = TEMPLATE_DIR.parent / "tasks" / "main.yml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    guard = next(
        task
        for task in tasks
        if task.get("name") == "Validate radioless Asterisk module defaults"
    )
    environment = Environment(undefined=StrictUndefined)
    environment.filters["b64decode"] = lambda value: base64.b64decode(value).decode()
    environment.tests["regex"] = lambda value, pattern: re.search(pattern, value) is not None

    def accepted(content: str) -> bool:
        encoded = base64.b64encode(content.encode()).decode()
        context = {"asl3_core_modules_conf": {"content": encoded}}
        return all(
            environment.compile_expression(assertion)(**context)
            for assertion in guard["ansible.builtin.assert"]["that"]
        )

    safe = """[modules]
autoload = no
noload = chan_dahdi.so ; DAHDI disabled
load = res_timing_timerfd.so ; Timerfd Timing Interface is preferred for ASL3
"""
    assert accepted(safe)
    assert not accepted(safe.replace("noload = chan_dahdi.so", "load = chan_dahdi.so"))
    assert not accepted(safe.replace("autoload = no", "autoload = yes"))


def test_restart_handler_uses_privilege_escalation():
    handlers_path = TEMPLATE_DIR.parent / "handlers" / "main.yml"
    handlers = yaml.safe_load(handlers_path.read_text(encoding="utf-8"))
    restart = next(handler for handler in handlers if handler.get("name") == "Restart asterisk")

    assert restart.get("become") is True
