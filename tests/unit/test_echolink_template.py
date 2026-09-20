from pathlib import Path
import re

from jinja2 import Environment, StrictUndefined
import yaml


ROLE_DIR = Path(__file__).parents[2] / "roles" / "echolink"
TEMPLATE_PATH = ROLE_DIR / "templates" / "echolink.conf.j2"


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_echolink_template_renders_required_configuration():
    environment = Environment(undefined=StrictUndefined)
    template = environment.from_string(TEMPLATE_PATH.read_text(encoding="utf-8"))
    rendered = template.render(
        echolink_call="N0CALL-L",
        vault_echolink_password="fixture-only-123",
        echolink_name="Example Operator",
        echolink_qth="Example City",
        echolink_email="example@example.invalid",
        echolink_node="000001",
        echolink_astnode="1998",
        echolink_lat=0,
        echolink_lon=0,
        echolink_freq=0,
        echolink_tone=0,
        echolink_power=0,
        echolink_height=0,
        echolink_gain=0,
        echolink_dir=0,
    )

    for expected in (
        "[el0]",
        "call = N0CALL-L",
        "pwd = fixture-only-123",
        "name = Example Operator",
        "qth = Example City",
        "email = example@example.invalid",
        "node = 000001",
        "astnode = 1998",
        "context = radio-secure",
        "lat = 0",
        "lon = 0",
        "freq = 0",
        "tone = 0",
        "power = 0",
        "height = 0",
        "gain = 0",
        "dir = 0",
    ):
        assert expected in rendered

    assert rendered.count("fixture-only-123") == 1


def test_echolink_role_protects_secrets_and_reconciles_module_state():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    render = next(task for task in tasks if task.get("name") == "Render EchoLink configuration")

    assert render["ansible.builtin.template"] == {
        "src": "echolink.conf.j2",
        "dest": "/etc/asterisk/custom/echolink.conf",
        "owner": "root",
        "group": "asterisk",
        "mode": "0640",
    }
    assert render["no_log"] is True
    assert render["diff"] is False

    module_tasks = [
        task
        for task in tasks
        if "ansible.builtin.lineinfile" in task
        and task["ansible.builtin.lineinfile"].get("path") == "/etc/asterisk/modules.conf"
    ]
    assert len(module_tasks) == 2
    assert {task["ansible.builtin.lineinfile"]["line"] for task in module_tasks} == {
        "load = chan_echolink.so",
        "noload = chan_echolink.so",
    }
    assert all(task.get("notify") == "Restart asterisk" for task in module_tasks)


def test_echolink_health_probes_are_read_only_and_publish_only_booleans():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    commands = {
        task["ansible.builtin.command"]["cmd"]: task
        for task in tasks
        if "ansible.builtin.command" in task
    }

    assert set(commands) == {
        "asterisk -rx 'module show like chan_echolink.so'",
        "ss -lunp",
        "journalctl -u asterisk --since '-5 minutes' --no-pager",
    }
    assert all(task["changed_when"] is False for task in commands.values())
    assert commands["journalctl -u asterisk --since '-5 minutes' --no-pager"]["no_log"] is True

    facts = next(
        task["ansible.builtin.set_fact"]
        for task in tasks
        if task.get("name") == "Publish EchoLink health facts"
    )
    assert facts
    assert all(value.strip().endswith("| bool }}") for value in facts.values())


def test_echolink_error_fact_detects_both_log_orderings():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    facts = next(
        task["ansible.builtin.set_fact"]
        for task in tasks
        if task.get("name") == "Publish EchoLink health facts"
    )
    expression = facts["echolink_recent_errors_detected"]
    match = re.search(r"is regex\('([^']+)'\)", expression)
    assert match is not None
    pattern = re.compile(match.group(1))

    assert pattern.search("chan_echolink.so failed to load")
    assert pattern.search("ERROR: unable to load chan_echolink.so")
    assert pattern.search("NOTICE: chan_echolink.so loaded") is None


def test_echolink_identity_requires_nonblank_strings():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    validation = next(
        task
        for task in tasks
        if task.get("name") == "Validate EchoLink identity configuration"
    )
    assertions = validation["ansible.builtin.assert"]["that"]

    for name in (
        "echolink_call",
        "echolink_name",
        "echolink_qth",
        "echolink_email",
        "echolink_node",
        "echolink_astnode",
        "vault_echolink_password",
    ):
        assert f"{name} is string" in assertions
        assert f"{name} | trim | length > 0" in assertions


def test_handlers_are_flushed_before_health_probes():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    flush_index = next(
        index
        for index, task in enumerate(tasks)
        if task.get("ansible.builtin.meta") == "flush_handlers"
    )
    first_probe_index = next(
        index for index, task in enumerate(tasks) if "ansible.builtin.command" in task
    )

    assert flush_index < first_probe_index


def test_udp_health_requires_asterisk_to_own_both_ports():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    facts = next(
        task["ansible.builtin.set_fact"]
        for task in tasks
        if task.get("name") == "Publish EchoLink health facts"
    )
    expression = facts["echolink_udp_ports_ready"]
    patterns = [
        pattern.replace("\\\\", "\\")
        for pattern in re.findall(r"is regex\('([^']+)'\)", expression)
    ]
    assert len(patterns) == 2

    unrelated = (
        'UNCONN 0 0 0.0.0.0:5198 0.0.0.0:* users:(("other",pid=1))\n'
        'UNCONN 0 0 0.0.0.0:5199 0.0.0.0:* users:(("other",pid=1))'
    )
    owned = (
        'UNCONN 0 0 0.0.0.0:5198 0.0.0.0:* users:(("asterisk",pid=2))\n'
        'UNCONN 0 0 0.0.0.0:5199 0.0.0.0:* users:(("asterisk",pid=2))'
    )

    assert not all(re.search(pattern, unrelated) for pattern in patterns)
    assert all(re.search(pattern, owned) for pattern in patterns)
