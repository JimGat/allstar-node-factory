from pathlib import Path

from jinja2 import Environment, StrictUndefined
import yaml


ROLE_DIR = Path(__file__).parents[2] / "roles" / "allmon3"


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def render_template(name, **context):
    environment = Environment(undefined=StrictUndefined)
    template = environment.from_string(
        (ROLE_DIR / "templates" / name).read_text(encoding="utf-8")
    )
    return template.render(**context)


def test_allmon3_node_template_renders_fictional_fixture_exactly():
    rendered = render_template(
        "allmon3.ini.j2",
        asl_node_number="1998",
        allmon3_ami_host="127.0.0.1",
        allmon3_ami_port=5038,
        allmon3_ami_user="node-factory",
        vault_ami_secret="fixture-only-123",
    )

    assert rendered.strip() == """[1998]
host = 127.0.0.1
port = 5038
user = node-factory
pass = fixture-only-123"""


def test_allmon3_backend_templates_are_loopback_only_and_restricted():
    web = render_template(
        "web.ini.j2",
        allmon3_http_bind_addr="127.0.0.1",
        allmon3_http_port=16080,
        allmon3_ws_bind_addr="127.0.0.1",
        allmon3_ws_port_start=16700,
    )
    restrictions = render_template(
        "user-restrictions.j2",
        allmon3_username="operator",
        asl_node_number="1998",
    )

    for expected in (
        "HTTP_BIND_ADDR = 127.0.0.1",
        "HTTP_PORT = 16080",
        "WS_BIND_ADDR = 127.0.0.1",
        "WS_PORT_START = 16700",
    ):
        assert expected in web
    assert restrictions.strip() == "operator | 1998"


def test_allmon3_web_template_preserves_required_package_sections():
    web = render_template(
        "web.ini.j2",
        allmon3_http_bind_addr="127.0.0.1",
        allmon3_http_port=16080,
        allmon3_ws_bind_addr="127.0.0.1",
        allmon3_ws_port_start=16700,
    )

    for section in ("[web]", "[syscmds]", "[node-overrides]", "[voter-titles]"):
        assert section in web


def test_allmon3_role_protects_secrets_and_reconciles_user_by_digest():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    secret_tasks = {
        task["name"]: task
        for task in tasks
        if task["name"] in {
            "Validate Allmon3 configuration",
            "Render the Allmon3 node configuration",
            "Compute the Allmon3 user credential digest",
            "Read the installed Allmon3 user credential digest",
            "Manage the Allmon3 login",
            "Write the Allmon3 user credential digest",
        }
    }
    assert len(secret_tasks) == 6
    assert all(task["no_log"] is True for task in secret_tasks.values())
    assert all(task["diff"] is False for task in secret_tasks.values())

    digest = secret_tasks["Compute the Allmon3 user credential digest"]
    digest_expression = digest["ansible.builtin.set_fact"]["allmon3_user_digest"]
    assert "allmon3_username" in digest_expression
    assert "vault_allmon3_password" in digest_expression
    assert "\\x00" in digest_expression
    assert "hash('sha256')" in digest_expression

    login = secret_tasks["Manage the Allmon3 login"]
    assert "ansible.builtin.expect" in login
    guarded_change = (
        "allmon3_enabled | bool "
        "and (allmon3_user_digest_changed | default(false) | bool)"
    )
    assert login["when"] == guarded_change
    assert login["notify"] == "Reload allmon3"

    sentinel = secret_tasks["Write the Allmon3 user credential digest"]
    assert sentinel["ansible.builtin.copy"]["dest"] == (
        "/var/lib/allstar-node-factory/allmon3-user.sha256"
    )
    assert sentinel["ansible.builtin.copy"]["mode"] == "0600"
    assert sentinel["when"] == guarded_change


def test_check_mode_exits_before_allmon3_runtime_service_checks():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    exit_task = next(
        task
        for task in tasks
        if task.get("name")
        == "End the Allmon3 role after check-mode configuration validation"
    )
    apache = next(
        task for task in tasks if task.get("name") == "Validate the Apache configuration"
    )
    service = next(
        task for task in tasks if task.get("name") == "Enable and start Allmon3"
    )

    assert exit_task["ansible.builtin.meta"] == "end_role"
    assert exit_task["when"] == "ansible_check_mode"
    assert tasks.index(exit_task) < tasks.index(apache) < tasks.index(service)


def test_allmon3_role_has_mandatory_validation_and_no_public_backend_listeners():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")

    restriction = next(
        task for task in tasks if task.get("name") == "Render mandatory Allmon3 user restrictions"
    )
    assert restriction["ansible.builtin.template"] == {
        "src": "user-restrictions.j2",
        "dest": "/etc/allmon3/user-restrictions",
        "owner": "allmon3",
        "group": "allmon3",
        "mode": "0660",
    }

    configtest = next(
        task for task in tasks if task.get("name") == "Validate the Apache configuration"
    )
    assert configtest["ansible.builtin.command"]["argv"] == ["apache2ctl", "configtest"]
    assert configtest["changed_when"] is False
    assert configtest["when"] == "allmon3_enabled | bool"

    uris = [task for task in tasks if "ansible.builtin.uri" in task]
    assert {task["ansible.builtin.uri"]["url"] for task in uris} == {
        "http://127.0.0.1:16080/node/listall",
        "http://127.0.0.1/allmon3/",
    }
    assert all(task["when"] == "allmon3_enabled | bool" for task in uris)

    listener_probe = next(
        task for task in tasks if task.get("name") == "Read local TCP listeners"
    )
    assert listener_probe["changed_when"] is False
    listener_assertion = next(
        task for task in tasks if task.get("name") == "Assert Allmon3 backends are loopback-only"
    )
    expression = listener_assertion["ansible.builtin.assert"]["that"][0]
    for port in (5038, 16080, 16700, 16701):
        assert str(port) in expression
    assert "127" in expression
    assert "::1" in expression


def test_allmon3_handler_does_not_run_in_check_mode():
    handlers = load_yaml(ROLE_DIR / "handlers" / "main.yml")
    reload_handler = next(
        handler for handler in handlers if handler.get("name") == "Reload allmon3"
    )

    condition = str(reload_handler["when"])
    assert "allmon3_enabled" in condition
    assert "not ansible_check_mode" in condition


def test_allmon3_handler_restarts_only_when_enabled():
    handlers = load_yaml(ROLE_DIR / "handlers" / "main.yml")
    reload_handler = next(
        handler for handler in handlers if handler.get("name") == "Reload allmon3"
    )
    assert reload_handler["ansible.builtin.service"] == {
        "name": "allmon3",
        "state": "restarted",
    }
    assert reload_handler["when"] == [
        "allmon3_enabled | bool",
        "not ansible_check_mode",
    ]


def test_disabled_role_never_references_undefined_digest_state():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    for name in ("Manage the Allmon3 login", "Write the Allmon3 user credential digest"):
        task = next(task for task in tasks if task.get("name") == name)
        condition = str(task["when"])
        assert "allmon3_enabled" in condition
        assert "default(false)" in condition


def test_username_rotation_removes_old_account_before_creating_new_account():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    delete = next(
        task for task in tasks if task.get("name") == "Remove the previously managed Allmon3 login"
    )
    restriction = next(
        task for task in tasks if task.get("name") == "Render mandatory Allmon3 user restrictions"
    )
    login = next(task for task in tasks if task.get("name") == "Manage the Allmon3 login")
    username_sentinel = next(
        task for task in tasks if task.get("name") == "Write the managed Allmon3 username"
    )

    assert delete["ansible.builtin.command"]["argv"] == [
        "allmon3-passwd",
        "--delete",
        "{{ allmon3_previous_username }}",
    ]
    assert tasks.index(delete) < tasks.index(restriction) < tasks.index(login)
    assert username_sentinel["ansible.builtin.copy"]["mode"] == "0600"


def test_disabled_role_stops_and_disables_allmon3_when_installed():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    facts = next(
        task for task in tasks if task.get("name") == "Inspect services when Allmon3 is disabled"
    )
    disabled = next(
        task for task in tasks if task.get("name") == "Stop and disable Allmon3 when disabled"
    )
    assert "ansible.builtin.service_facts" in facts
    assert tasks.index(facts) < tasks.index(disabled)
    assert disabled["ansible.builtin.service"] == {
        "name": "allmon3",
        "state": "stopped",
        "enabled": False,
    }
    assert disabled["when"] == [
        "not (allmon3_enabled | bool)",
        "'allmon3.service' in ansible_facts.services",
    ]
