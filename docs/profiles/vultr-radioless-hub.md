# Vultr Radioless Hub Profile

## Target

- Debian 13 x64
- 2 vCPU, 2 GB RAM, 25-40 GB SSD
- ASL3 radioless `Local/pseudo` hub
- Optional EchoLink, Broadcastify, Allmon3, and commit-pinned AllScan
- One permanent AllStarLink connection to the separate DVSwitch node

The provider firewall and UFW must agree: management-restricted SSH, public configured IAX UDP, EchoLink UDP only when enabled, and web access only through the approved protected boundary. AMI and Allmon3 backend ports remain loopback-only.

## Inputs

Private inventory supplies host addressing, callsign, node/peer identifiers, feature flags, topology, management networks, and encrypted credentials. The public framework must be at the exact clean commit in `framework.lock.yml`.

## Configuration ownership

Private inventory is the single source of truth for the node number and other durable settings. Change `asl_node_number` in inventory and rerun the factory; the RPT, HTTP registration, EchoLink attachment, backup naming, validation, and related templates regenerate from that value. Do not make a durable node-number change only in `asl-menu`.

Factory-owned Asterisk content is rendered into ASL3's native `/etc/asterisk/custom/` include tree wherever the package provides a custom seam. Package-owned files retain only narrowly scoped settings or include hooks where ASL3 has no native seam. Rerunning an ASL configuration tool must be followed by a factory check/apply run; the run preserves custom fragments, repairs required hooks, and fails if a future package stops loading the expected custom paths.

## ASL Web UI interoperability

ASL3 on Debian 13 offers the `asl-web-ui` package at `https://<node>/asl-web-ui/`. The official manual says the Web UI works on the same files as `asl-menu`, `node-setup`, and text editors, reads files fresh, previews every change, stores the last 50 snapshots under `/var/lib/asl-web-ui/snapshots`, and records its audit trail in `/var/lib/asl-web-ui/audit.jsonl`. See the [ASL Web UI manual](https://allstarlink.github.io/web-ui/), [installation](https://allstarlink.github.io/web-ui/install/), [node editor](https://allstarlink.github.io/web-ui/nodes/), and [manual configuration editor](https://allstarlink.github.io/web-ui/config-edit/).

The Web UI is not a second source of truth. Private inventory and factory templates remain authoritative for durable node identity, HTTP registration, IAX port, channel type, RPT behavior, EchoLink, AMI, permanent links, firewall policy, and managed dashboards. Continue to put factory-owned features in ASL3's native `/etc/asterisk/custom/` files whenever an include seam exists. The Web UI's own Customizations page also uses that directory, which makes the seam native but does not transfer ownership of factory files to the UI.

Use this reconciliation workflow:

1. Use the Web UI's **Review and save** diff to inspect the exact files and lines it proposes to change.
2. For a factory-owned setting, update private inventory and the relevant template or narrowly scoped hook. Run the factory check/apply sequence and verify the resulting Web UI view. A Web UI-only edit is temporary drift and is not a completed change.
3. For measured hardware values or a setting the factory does not yet model, the Web UI may make the initial change. Capture its diff and audit entry, add the proven value to private inventory/templates, then run factory check/apply before declaring it durable.
4. Do not use the Web UI alone to rename/remove a managed node, switch registration methods, change the IAX port, replace the managed certificate/vhost, or alter a production identity. Those changes require inventory, template, firewall, validation, and rollback updates as one reviewed change.
5. After any `asl-menu`, Web UI, or manual edit, run factory check/apply. Expected: declared values remain, native include hooks still load, and unmanaged duplicate node stanzas are absent.

Before enabling `asl-web-ui` on a production profile, install it with identities disabled, add only the intended Linux account to the `asl-web-ui` group, expose `/asl-web-ui/` through the managed trusted-HTTPS vhost, and test node discovery plus a harmless reviewed edit/reconciliation cycle. The factory remains responsible for Certbot and Apache policy; do not use the Web UI HTTPS page to replace the managed certificate configuration.

## Deploy

```bash
.venv/bin/ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/vultr-hub.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml
```

Expected in staging: backups and configuration are present, web initialization is protected, and public identities remain inactive because `production_services_enabled` is false.

## Validate

Use `playbooks/validate.yml` with the same inventory, limit, Vault ID, topology, and Vault arguments. Expected: a redacted report at `/var/lib/allstar-node-factory/reports/latest.json`; no raw stdout, journals, environments, or secrets are serialized.

Production acceptance additionally requires inbound/outbound linking, two-way audio, DTMF, EchoLink behavior, Broadcastify quality, dashboard control, full reboot recovery, independent DVSwitch reboot recovery, and an off-host checksum proof.
