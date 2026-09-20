#!/usr/bin/env python3
"""Validate the public/private AllStar node inventory contract."""

from __future__ import annotations

import argparse
import ipaddress
from pathlib import Path
import sys
from typing import Any

import yaml

REQUIRED_ALWAYS = (
    "asl_node_number",
    "asl_callsign",
    "asl_iax_port",
    "asl_rxchannel",
    "management_cidrs",
    "vault_asl_node_password",
    "vault_ami_secret",
)
FEATURE_SECRETS = {
    "echolink_enabled": ("vault_echolink_password",),
    "broadcastify_enabled": ("vault_broadcastify_password",),
    "allmon3_enabled": ("vault_allmon3_password",),
    "allscan_enabled": ("vault_allscan_password",),
}
VALID_INITIATORS = {"external", "local"}


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate(data: dict[str, Any]) -> list[str]:
    """Return contract errors; an empty list means the inventory is valid."""
    if not isinstance(data, dict):
        return ["inventory must be a YAML mapping"]

    errors: list[str] = []
    for key in REQUIRED_ALWAYS:
        if key not in data or _missing(data.get(key)):
            errors.append(f"{key} is required")

    node = data.get("asl_node_number")
    if node is not None and (
        not isinstance(node, str) or not node.isdigit() or not 4 <= len(node) <= 6
    ):
        errors.append("asl_node_number must be a 4-6 digit string")

    port = data.get("asl_iax_port")
    if port is not None and (
        isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535
    ):
        errors.append("asl_iax_port must be an integer from 1 to 65535")

    cidrs = data.get("management_cidrs")
    if cidrs is not None:
        if not isinstance(cidrs, list) or not cidrs:
            errors.append("management_cidrs must be a non-empty list")
        else:
            for cidr in cidrs:
                if not isinstance(cidr, str):
                    errors.append(f"management_cidrs contains invalid CIDR: {cidr!r}")
                    continue
                try:
                    ipaddress.ip_network(cidr, strict=False)
                except (TypeError, ValueError):
                    errors.append(f"management_cidrs contains invalid CIDR: {cidr!r}")

    activation = data.get("production_services_enabled")
    if not isinstance(activation, bool):
        errors.append("production_services_enabled must be true or false")

    feature_flags = (*FEATURE_SECRETS, "permanent_link_enabled")
    for flag in feature_flags:
        if flag in data and not isinstance(data[flag], bool):
            errors.append(f"{flag} must be true or false")

    for flag, secret_names in FEATURE_SECRETS.items():
        if data.get(flag) is True:
            for secret_name in secret_names:
                if secret_name not in data or _missing(data.get(secret_name)):
                    errors.append(f"{secret_name} is required")

    if data.get("allscan_enabled") is True:
        password = data.get("vault_allscan_password")
        if not isinstance(password, str) or not 6 <= len(password) <= 16:
            errors.append("vault_allscan_password must be 6-16 characters")

    if data.get("permanent_link_enabled") is True:
        peer = data.get("permanent_link_peer_node")
        if _missing(peer):
            errors.append("permanent_link_peer_node is required")
        elif not isinstance(peer, str) or not peer.isdigit() or not 4 <= len(peer) <= 6:
            errors.append("permanent_link_peer_node must be a 4-6 digit string")
        if data.get("permanent_link_initiator") not in VALID_INITIATORS:
            errors.append("permanent_link_initiator must be external or local")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args(argv)

    try:
        data = yaml.safe_load(args.inventory.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print(f"unable to load inventory: {exc}", file=sys.stderr)
        return 1

    errors = validate(data)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("inventory contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
