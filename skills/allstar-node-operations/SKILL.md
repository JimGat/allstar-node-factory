---
name: allstar-node-operations
description: Operate repeatable ASL3 node builds and recovery.
version: 0.1.0
author: Jim Gatwood, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [AllStarLink, ASL3, Ansible, Operations]
    related_skills: []
---

# AllStar Node Operations

## When to Use

Use for staging, validating, backing up, cutting over, or recovering a node managed by the public node-factory framework and private encrypted inventory.

## Prerequisites

- The public checkout is clean and exactly matches the private framework lock. Check: the pin validator exits zero.
- The private inventory and named Vault decrypt successfully. Check: Vault view exits zero without printing plaintext.
- Provider backups and narrowly scoped firewall rules are active. Check: provider evidence and host policy agree.
- The old node and rollback artifacts remain available. Check: snapshot and backup metadata are recorded privately.

## How to Run

Run the explicit playbook from the public framework with the private inventory, target limit, named Vault identity, topology file, and encrypted variable file. Begin with check mode. Check: no secret or unexpected deletion appears in output.

Use the deployment entry point for configuration, the validation entry point for read-only health evidence, and the backup entry point for native plus supplemental archives. Check: each command targets only the intended inventory host.

## Procedure

1. Keep production activation false and run check mode. Check: identity-bearing services remain inactive.
2. Apply staging configuration and initialize optional web software through the protected path. Check: local health is `PASS` and public access remains closed.
3. Run validation and backup. Check: the redacted report has bounded statuses and the checksum succeeds.
4. During an approved window, stop old Asterisk, EchoLink, and Broadcastify identities before enabling the new host. Check: no identity is duplicated.
5. Run two-way link/audio, DTMF, dashboard, feed, and reboot tests. Check: every acceptance row is recorded.
6. On a material failure, stop new identities and start the old node. Check: legacy service and permanent-link behavior return.
7. Copy backups off-host and verify at destination. Check: destination checksum reports success.

## Pitfalls

- Never copy a legacy Asterisk tree wholesale onto ASL3.
- Never activate the same public identity on old and new servers together.
- A registration or green dashboard is not proof of two-way audio.
- Never expose AMI or dashboard backends directly to the Internet.
- A target-local archive is not a completed backup.
- Do not declare migration complete without the independent peer reboot test.

## Verification

Confirm a clean pinned framework, bounded firewall, unique registration, inbound/outbound links, two-way audio, DTMF, EchoLink, Broadcastify, authenticated dashboards, permanent-link recovery, host and peer reboot recovery, redacted reports, and a verified off-host backup. Completion criterion: every applicable check is `PASS`; no required check is deferred or inferred.
