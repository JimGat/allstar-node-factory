from pathlib import Path

import jinja2
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_PATH = ROOT / "roles/permanent_link/defaults/main.yml"
TASKS_PATH = ROOT / "roles/permanent_link/tasks/main.yml"
TEMPLATE_PATH = ROOT / "roles/asl3_core/templates/rpt-node-factory.conf.j2"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def task_by_name(tasks: list[dict], name: str) -> dict:
    for task in tasks:
        if task.get("name") == name:
            return task
    raise LookupError(name)


def render(initiator: str, peer: str = "1999") -> str:
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_PATH.parent)),
        undefined=jinja2.StrictUndefined,
    )
    environment.filters["bool"] = bool
    template = environment.get_template(TEMPLATE_PATH.name)
    return template.render(
        asl_node_number="1998",
        asl_rxchannel="Radio/usb",
        asl_callsign="N0CALL",
        asl_iax_port=4569,
        broadcastify_enabled=False,
        private_node_routes={},
        permanent_link_enabled=True,
        permanent_link_initiator=initiator,
        permanent_link_peer_node=peer,
    )


def test_local_ownership_renders_the_only_startup_macro() -> None:
    rendered = render("local")

    assert "startup_macro = *8131999" in rendered
    assert rendered.count("startup_macro") == 1


def test_external_ownership_never_renders_a_local_startup_macro() -> None:
    assert "startup_macro" not in render("external")


def test_role_defaults_to_disabled_with_explicit_external_ownership() -> None:
    defaults = load_yaml(DEFAULTS_PATH)

    assert defaults == {
        "permanent_link_enabled": False,
        "permanent_link_peer_node": "",
        "permanent_link_initiator": "external",
    }


def test_role_rejects_invalid_initiator_and_local_node_as_peer() -> None:
    validation = task_by_name(
        load_yaml(TASKS_PATH), "Validate the permanent-link ownership contract"
    )["ansible.builtin.assert"]["that"]
    assertions = "\n".join(validation)

    assert "permanent_link_initiator in ['external', 'local']" in assertions
    assert "permanent_link_peer_node != asl_node_number" in assertions


@pytest.mark.parametrize("peer", ["1234", "12345", "123456"])
def test_peer_contract_accepts_only_four_to_six_numeric_digits(peer: str) -> None:
    validation = task_by_name(
        load_yaml(TASKS_PATH), "Validate the permanent-link ownership contract"
    )["ansible.builtin.assert"]["that"]
    assertions = "\n".join(validation)

    assert "^[0-9]{4,6}$" in assertions
    assert peer.isdigit() and 4 <= len(peer) <= 6


@pytest.mark.parametrize("peer", ["123", "1234567", "12a4", " 1999", "1999 "])
def test_peer_contract_rejects_values_outside_four_to_six_numeric_digits(
    peer: str,
) -> None:
    assert not (peer.isdigit() and 4 <= len(peer) <= 6)


def test_role_probes_lstats_read_only_and_counts_only_the_exact_peer() -> None:
    tasks = load_yaml(TASKS_PATH)
    probe = task_by_name(tasks, "Read the permanent-link status")
    fact = task_by_name(tasks, "Record exact permanent-link presence")
    expression = fact["ansible.builtin.set_fact"]["permanent_link_present"]

    assert probe["ansible.builtin.command"]["argv"] == [
        "asterisk",
        "-rx",
        "rpt lstats {{ asl_node_number }}",
    ]
    assert probe["changed_when"] is False
    assert "regex_findall" in expression
    assert "(?<![0-9])" in expression
    assert "(?![0-9])" in expression
    assert "length == 1" in expression


def test_external_owner_reads_the_native_custom_rpt_fragment() -> None:
    tasks = load_yaml(TASKS_PATH)
    read = task_by_name(
        tasks, "Read the managed Asterisk node fragment for external ownership"
    )

    assert read["ansible.builtin.slurp"]["src"] == (
        "/etc/asterisk/custom/rpt/node-factory.conf"
    )


def test_external_owner_asserts_the_managed_fragment_has_no_startup_macro() -> None:
    tasks = load_yaml(TASKS_PATH)
    check = task_by_name(tasks, "Assert external ownership has no local startup macro")

    assert check["when"] == [
        "permanent_link_enabled | bool",
        "permanent_link_initiator == 'external'",
    ]
    assertion = "\n".join(check["ansible.builtin.assert"]["that"])
    assert "startup_macro" in assertion
    assert "not in" in assertion
