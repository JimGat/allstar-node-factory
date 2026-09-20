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
