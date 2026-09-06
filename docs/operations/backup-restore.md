# Backup and Restore

The factory produces an ASL-native backup when `asl-backup-menu` is present and a supplemental restricted archive for integration state. A backup is incomplete until it is copied off-host and its checksum passes there.

## Create and verify

```bash
.venv/bin/ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/backup.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml
```

Expected: a readable native `ASL_*.tgz` when supported, a mode-0600 supplemental archive and checksum under `/var/backups/allstar-node-factory`, and a successful target-side checksum check.

Copy the archive and matching `.sha256` file to the approved off-host location using the authorized transfer mechanism. Run `sha256sum --check ARCHIVE.sha256` at the destination. Expected: `OK`; record only destination class, timestamp, size, and checksum in private metadata.

## Restore rehearsal

1. Select a matched archive/checksum pair and verify it before extraction. Expected: checksum reports `OK`.
2. Restore only to an isolated Debian 13 recovery target, never over the operating node. Expected: production remains untouched.
3. Inspect archive paths and owners before extraction. Expected: no path escapes the intended root.
4. Restore ASL-native configuration with the supported ASL3 utility, then restore only reviewed supplemental integration files. Expected: package-owned defaults are not blindly replaced.
5. Keep identities disabled with `production_services_enabled: false`. Expected: no registration, EchoLink login, or Broadcastify feed starts.
6. Run validation with the standard command below. Expected: staging checks pass and identity checks are `NOT_APPLICABLE`.

```bash
.venv/bin/ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/validate.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml
```

Never store raw archives, decrypted Vault content, or unredacted reports in either repository.
