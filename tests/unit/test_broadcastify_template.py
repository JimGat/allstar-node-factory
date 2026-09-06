from pathlib import Path
import shlex

from jinja2 import Environment, StrictUndefined
import yaml


ROLE_DIR = Path(__file__).parents[2] / "roles" / "broadcastify"
TEMPLATE_PATH = ROLE_DIR / "templates" / "broadcastify.conf.j2"
CORE_TEMPLATE_PATH = (
    Path(__file__).parents[2]
    / "roles"
    / "asl3_core"
    / "templates"
    / "rpt-node-factory.conf.j2"
)


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_broadcastify_template_renders_required_configuration():
    environment = Environment(undefined=StrictUndefined)
    environment.filters["quote"] = shlex.quote
    template = environment.from_string(TEMPLATE_PATH.read_text(encoding="utf-8"))
    rendered = template.render(
        asl_node_number="1998",
        broadcastify_host="audio.example.invalid",
        broadcastify_port="80",
        broadcastify_mount="/example",
        broadcastify_user="source",
        vault_broadcastify_password="fixture-only-123",
        broadcastify_input_samplerate="8000",
        broadcastify_input_channels="1",
        broadcastify_output_bitrate="16k",
    )

    for expected in (
        "FIFO=/var/lib/asterisk/1998.fifo",
        "ICECAST_HOST=audio.example.invalid",
        "ICECAST_PORT=80",
        "ICECAST_MOUNT=/example",
        "ICECAST_USER=source",
        "ICECAST_PASSWORD=fixture-only-123",
        "INPUT_SAMPLERATE=8000",
        "INPUT_CHANNELS=1",
        "OUTPUT_BITRATE=16k",
    ):
        assert expected in rendered


def test_broadcastify_template_quotes_every_external_value():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    assignments = [line for line in template.splitlines() if "=" in line]
    assert len(assignments) == 9
    assert all("| quote" in line for line in assignments)


def test_broadcastify_role_enforces_secure_configuration_and_activation_order():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    render = next(
        task for task in tasks if task.get("name") == "Render Broadcastify stream configuration"
    )
    assert render["ansible.builtin.template"] == {
        "src": "broadcastify.conf.j2",
        "dest": "/etc/asterisk/broadcastify/{{ asl_node_number }}.conf",
        "owner": "root",
        "group": "asterisk",
        "mode": "0640",
    }
    assert render["no_log"] is True
    assert render["diff"] is False
    assert render["notify"] == "Restart Broadcastify"

    validation = next(
        task for task in tasks if task.get("name") == "Reject unsafe Broadcastify shell values"
    )
    assert validation["no_log"] is True
    assert "\\r\\n\\x00" in validation["ansible.builtin.assert"]["that"][0]

    flush_index = next(
        index
        for index, task in enumerate(tasks)
        if task.get("ansible.builtin.meta") == "flush_handlers"
    )
    start_index = next(
        index
        for index, task in enumerate(tasks)
        if task.get("name") == "Activate the Broadcastify service in production"
    )
    assert flush_index < start_index


def test_broadcastify_role_has_read_only_gates_and_health_probes():
    tasks = load_yaml(ROLE_DIR / "tasks" / "main.yml")
    commands = [task for task in tasks if "ansible.builtin.command" in task]
    assert commands
    assert all(task["changed_when"] is False for task in commands)

    command_argv = [task["ansible.builtin.command"].get("argv", []) for task in commands]
    assert ["dpkg-query", "-W", "-f=${Version}", "asl3"] in command_argv
    assert any(argv[:2] == ["dpkg", "--compare-versions"] for argv in command_argv)
    assert any(argv[:2] == ["systemctl", "is-active"] for argv in command_argv)
    assert any(argv and argv[0] == "journalctl" for argv in command_argv)

    binary_probe = next(
        task for task in tasks if task.get("name") == "Probe for rpt_audio_writer"
    )
    assert binary_probe["ansible.builtin.stat"]["path"] == "/usr/libexec/asl3/rpt_audio_writer"
    assert binary_probe["changed_when"] is False


def test_outstreamcmd_is_present_only_when_broadcastify_is_enabled():
    environment = Environment(undefined=StrictUndefined)
    environment.filters["bool"] = bool
    template = environment.from_string(CORE_TEMPLATE_PATH.read_text(encoding="utf-8"))
    context = {
        "asl_node_number": "1998",
        "asl_callsign": "N0CALL",
        "asl_iax_port": 4569,
        "asl_rxchannel": "Local/pseudo",
        "permanent_link_enabled": False,
        "permanent_link_initiator": "external",
        "permanent_link_peer_node": "1999",
        "private_node_routes": {},
    }

    enabled = template.render(broadcastify_enabled=True, **context)
    disabled = template.render(broadcastify_enabled=False, **context)
    expected = "outstreamcmd = /usr/libexec/asl3/rpt_audio_writer,/var/lib/asterisk/1998.fifo"

    assert expected in enabled
    assert "outstreamcmd" not in disabled


def test_broadcastify_restart_handler_is_production_gated():
    handlers = load_yaml(ROLE_DIR / "handlers" / "main.yml")
    restart = next(
        handler for handler in handlers if handler.get("name") == "Restart Broadcastify"
    )

    assert restart["ansible.builtin.service"] == {
        "name": "asl-broadcastify@{{ asl_node_number }}",
        "state": "restarted",
    }
    assert restart["become"] is True
    assert restart["when"] == "broadcastify_enabled | bool and production_services_enabled | bool"