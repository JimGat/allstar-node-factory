# Secrets Policy

Production secrets live only in the private inventory repository as Ansible Vault ciphertext. The Vault password file is outside Git at `/home/jarvis/.config/allstar-node-factory/vault-production.key`, mode 0600, with one recovery copy in Jim's password manager.

## Allowed secret keys

The encrypted production file contains only:

- `vault_asl_node_password`
- `vault_echolink_password`
- `vault_broadcastify_password`
- `vault_ami_secret`
- `vault_allmon3_password`
- `vault_allscan_password`

Do not place passwords, tokens, private keys, raw backups, decrypted files, process environments, or unredacted logs in either repository. Secret-bearing Ansible tasks use both `no_log: true` and `diff: false`.

## Create or edit

Use `ansible-vault create` or `ansible-vault edit` with the external production Vault ID. Enter values only in the editor opened by Ansible Vault; never put a secret in shell arguments, command history, chat, or documentation.

Expected after creation: the ciphertext header begins with `$ANSIBLE_VAULT;1.2;AES256;production`, a silent `ansible-vault view ... >/dev/null` exits zero, and Git inspection shows ciphertext only.

## Rotation

1. Stop affected identity-bearing services if rotating a live external identity. Expected: no duplicate or partially authenticated session.
2. Edit the encrypted Vault file and preserve its named Vault ID. Expected: silent decryption succeeds.
3. Run check mode with the standard deployment command from the cutover runbook. Expected: no secret appears in output.
4. Apply in a controlled window, validate, and revoke the previous credential. Expected: only the new credential works.

If plaintext is ever committed, stop deployment, rotate the exposed value, remove it from reachable history through an approved incident process, and verify both repositories before resuming.
