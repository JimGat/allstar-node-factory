# Read-Only Legacy Node Inventory Prompt

You are inventorying an authorized legacy HAMVOIP/AllStarLink node for migration to clean ASL3. Work read-only. Do not restart, reload, stop, enable, disable, install, upgrade, or edit anything. Do not display secrets, private keys, passwords, tokens, or full credential-bearing configuration.

Save raw authorized output outside both Git repositories in a mode-0700 evidence directory. Redact any operator-facing summary.

Collect and report:

1. OS, kernel, Asterisk/app_rpt, and installed package versions.
2. Public node/server identity, callsign, Portal assignment, IAX bind port, and status-posting method without passwords.
3. Node stanza behavior: channel, duplex, timers, telemetry, IDs, functions, macros, and startup macro names with secret values removed.
4. Local/private node routes and direct-client account names without credentials.
5. EchoLink callsign/node, configured ports, module state, and active login state without password.
6. Broadcastify service/unit, destination class, audio source, codec, and active state without feed password.
7. Dashboard products, local bind addresses, authentication presence, and public exposure.
8. Custom sounds, scripts, cron entries, systemd units, and file ownership/modes.
9. Listening sockets, host firewall policy, provider firewall evidence supplied by the operator, DNS, and TLS names.
10. Permanent-link peer, current link state, and which endpoint owns recovery after startup. Do not reboot either endpoint.
11. Backup utilities, archive locations, snapshot status supplied by the operator, and recovery dependencies.

For each migration-matrix row return exactly one evidence state: `captured`, `not used`, or `not present`. Mark uncertainty explicitly; do not infer a missing value. End with a redacted gap list and the exact additional read-only evidence required.
