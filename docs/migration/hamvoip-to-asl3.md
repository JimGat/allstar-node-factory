# HAMVOIP to ASL3 Migration Matrix

Build a clean Debian ASL3 host beside the legacy node. Do not copy the legacy `/etc/asterisk` tree wholesale. Translate intended behavior into stock ASL3 configuration and managed node-factory fragments.

Store raw evidence outside both Git repositories in a mode-0700 directory. The `Verified` column must be changed to `captured`, `not used`, or `not present`; no row may remain blank before inventory is populated.

| Legacy evidence | ASL3 destination | Secret | Activation gate | Verified |
|---|---|---|---|---|
| node/server identity and portal assignment | private host inventory and ASL3 HTTP registration | node password | old Asterisk stopped | pending |
| ports/codecs and IAX bind address | `asl_iax_port`, Portal record, firewall role | no | provider and host firewall agree | pending |
| node stanza and channel type | managed `rpt-node-factory.conf` using `Local/pseudo` | no | duplicate stanza check passes | pending |
| DTMF/functions/macros | reviewed ASL3 template includes | possibly | behavior mapped and peer tested | pending |
| telemetry/IDs and custom recordings | ASL3 templates and approved sound directory | possibly | callsign and ID reviewed | pending |
| local/private nodes and routes | `private_node_routes` | possibly | route ownership documented | pending |
| direct clients and IAX users | dedicated managed include | yes | credentials rotated and access bounded | pending |
| EchoLink identity and behavior | EchoLink role and Vault | yes | old EchoLink login stopped | pending |
| Broadcastify feed configuration | Broadcastify role and Vault | yes | old feed process stopped | pending |
| Allmon3 and AllScan web tools | loopback services and protected frontend | yes | admin initialized privately | pending |
| custom sounds and scripts | explicitly reviewed supplemental files | possibly | owner, mode, and caller verified | pending |
| cron/systemd jobs | reviewed native systemd units and timers | possibly | no duplicate scheduler | pending |
| sockets/firewall and DNS/TLS | provider firewall, UFW, and protected web path | no | listener matrix passes | pending |
| permanent-link ownership and startup macro | topology inventory and permanent-link role | no | exactly one initiator | pending |

## Evidence rules

1. Capture package versions, listeners, service state, and redacted configuration from the old node read-only. Expected: every matrix row has evidence or an explicit absence.
2. Compare startup macros and active link state at both ends without rebooting. Expected: one endpoint is declared the initiator.
3. Translate one functional layer at a time; do not copy HAMVOIP configuration wholesale. Expected: ASL3 defaults remain intact unless a documented requirement overrides them.
4. Keep `production_services_enabled: false` during staging. Expected: no duplicate AllStarLink, EchoLink, or Broadcastify identity appears.
5. Record acceptance and rollback evidence in the private repository without raw secrets or logs. Expected: every matrix row is closed before cutover.
