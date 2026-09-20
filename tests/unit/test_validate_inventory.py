from pathlib import Path
import importlib.util
import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_inventory", ROOT / "scripts" / "validate_inventory.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load(name: str) -> dict:
    return yaml.safe_load((ROOT / "tests/fixtures/inventory" / name).read_text())


def test_valid_inventory_has_no_errors() -> None:
    assert MODULE.validate(load("valid.yml")) == []


def test_missing_secret_reference_is_rejected() -> None:
    errors = MODULE.validate(load("missing-secret.yml"))
    assert "vault_asl_node_password is required" in errors


def test_activation_requires_explicit_boolean() -> None:
    data = load("valid.yml")
    data.pop("production_services_enabled")
    assert "production_services_enabled must be true or false" in MODULE.validate(data)


def test_feature_flags_reject_string_booleans() -> None:
    data = load("valid.yml")
    data["allscan_enabled"] = "true"
    assert "allscan_enabled must be true or false" in MODULE.validate(data)


def test_management_cidrs_reject_non_strings() -> None:
    data = load("valid.yml")
    data["management_cidrs"] = [1234]
    assert "management_cidrs contains invalid CIDR: 1234" in MODULE.validate(data)


def test_allscan_password_must_be_a_bounded_string() -> None:
    data = load("valid.yml")
    data["vault_allscan_password"] = 123456
    assert "vault_allscan_password must be 6-16 characters" in MODULE.validate(data)
