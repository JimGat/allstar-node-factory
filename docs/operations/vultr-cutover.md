# Vultr Radioless Hub Cutover

This is the operator runbook for blue/green replacement. Do not delete the old server during staging, cutover, or the rollback-retention period.

## Preconditions

- New host is Debian 13 amd64 with the reviewed framework commit checked out cleanly.
- Private inventory pins that exact commit.
- Provider backup and firewall are enabled.
- Raw legacy evidence and snapshots are outside Git.
- `production_services_enabled: false` is committed in private inventory.
- The old server is still operating and unchanged.

## Stage

Run check mode first:

```bash
.venv/bin/ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/vultr-hub.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml \
  --check --diff
```

Expected: no secret values, unexpected deletions, or preflight failures. Identity-bearing services remain inactive.

Apply the staged configuration by removing only `--check --diff` from that exact command. Expected: configuration, protected web tools, firewall, and backup exist while Asterisk registration, EchoLink login, and Broadcastify transmission remain inactive.

Initialize AllScan only through the protected management path. Create the first Superuser and set Public Permission to None. Expected: the database exists and AllScan validation changes from `INIT_REQUIRED` to `PASS`.

## Validate staging

```bash
.venv/bin/ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/validate.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml
```

Expected: non-production checks are `PASS`; identity checks are `NOT_APPLICABLE`; AllScan is `PASS`.

## Controlled activation

1. Take a fresh snapshot and final backup of the old node. Expected: artifact identifiers and checksums are recorded privately.
2. Stop old Asterisk, EchoLink, and Broadcastify processes. Expected: the old node has no registration, EchoLink login, or feed connection.
3. Change only private inventory to `production_services_enabled: true`.
4. Run the deployment command:

```bash
.venv/bin/ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/vultr-hub.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml
```

Expected: one HTTP registration, one EchoLink login, one Broadcastify feed, and exactly one permanent DVSwitch link.

## Functional acceptance

Verify inbound and outbound AllStarLink connections, two-way audio, DTMF, telemetry, EchoLink inbound/outbound behavior, Broadcastify presence and quality, Allmon3 control, AllScan control, and the DVSwitch link. Expected: every item is recorded `PASS` in a redacted private report.

Run the reboot matrix in order: cloud-host cold reboot, Asterisk-only restart, bounded network interruption, DVSwitch-node reboot, audio/DTMF retest, and final backup. Expected: services and the permanent link recover after every applicable test. If the DVSwitch reboot cannot be performed, acceptance is incomplete.

## Rollback

If a material acceptance check fails:

1. Stop the new Asterisk, EchoLink, and Broadcastify identity-bearing services. Expected: the new node no longer registers or transmits.
2. Set `production_services_enabled: false` on the new inventory. Expected: the fail-safe state is recorded.
3. Restore or start the old server. Expected: old Asterisk registration, EchoLink login, Broadcastify feed, and DVSwitch link return.
4. Re-run inbound/outbound audio and DTMF tests. Expected: legacy service is functional.
5. Preserve the new host for diagnosis; do not delete either server. Expected: both rollback paths remain available.
