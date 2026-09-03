# AllStar Node Factory Design

Date: 2026-09-03
Status: Approved in principle; pending review of this written specification
Owner: Jim Gatwood

## Purpose

Build a repeatable, security-conscious way to install, migrate, validate, back up, and recover Jim's AllStarLink nodes without turning a straightforward radio system into an unnecessarily complex infrastructure platform.

The immediate deliverable is a reproducible replacement for the existing HAMVOIP cloud node on Vultr. The framework must later accommodate radioless hubs, half-duplex repeater links, repeater controllers, remote radio channel control, custom voice IDs, SkywarnPlus/NWS messaging, and SHARI Raspberry Pi mobile nodes.

## Design principles

1. Start with the real Vultr migration, not speculative abstractions.
2. Use supported ASL3 packaging and official Raspberry Pi images where practical.
3. Keep production secrets and topology out of the public repository.
4. Make deployments idempotent and safe to re-run.
5. Treat hardware calibration as measured data, not a universal default.
6. Validate service behavior after installation and after a cold reboot.
7. Preserve a rollback path until the replacement node is proven.
8. Add new node profiles only when a real node is ready to be built.
9. Keep third-party integrations isolated from the ASL3 foundation.
10. Prefer understandable operations over a large platform.

## Scope

### Initial scope

The first reference profile is a Vultr-hosted radioless hub with:

- Debian 13 x86_64
- 2 vCPUs
- 2 GB RAM
- 25-40 GB storage
- ASL3 installed from the official package repository
- Existing public AllStarLink node identity
- HTTP-based AllStarLink registration
- EchoLink
- Broadcastify
- Allmon3
- AllScan
- A permanent transceive connection with the existing dedicated DVSwitch node
- Host and Vultr firewall requirements
- Configuration backup
- Automated post-deployment validation
- Documented rollback

### Future scope

Future profiles may add:

- Minimal radioless hubs
- Half-duplex repeater links
- Repeater controllers
- Custom voice IDs
- SkywarnPlus and NWS alert/message integration
- Remote channel control over a one-wire serial interface
- SHARI Raspberry Pi mobile RF nodes
- Additional radio-specific serial adapters

### Non-goals for the initial release

- Building a custom Raspberry Pi OS image
- Running an Ansible server or Ansible agent
- GitHub Actions deployment into production
- HashiCorp Vault or another secrets server
- Packer or an immutable-image pipeline
- Fully automating physical radio calibration
- Rebuilding the separate DVSwitch node
- Implementing every future node profile before the Vultr hub is proven

## Repository architecture

### Public framework repository

Repository: `JimGat/allstar-node-factory`
Visibility: public

The public repository defines how nodes are built. It contains reusable Ansible playbooks, roles, templates, validation, documentation, prompts, and Hermes skills.

Initial layout:

    README.md
    LICENSE
    CHANGELOG.md
    ansible.cfg
    requirements.yml
    playbooks/
      vultr-hub.yml
      validate.yml
      backup.yml
    roles/
      asl3_core/
      firewall/
      permanent_link/
      echolink/
      broadcastify/
      allmon3/
      allscan/
      validation/
    inventories/
      example/
    docs/
      migration/
      operations/
      profiles/
      security/
      superpowers/specs/
    tests/
      fixtures/
      integration/
      unit/
    prompts/
    skills/

The public repository must not contain production credentials, SSH private keys, Vultr tokens, private management addresses, complete production topology, raw backups, or private voice assets.

Public examples use fictional callsigns, fake node numbers clearly labeled as examples, and documentation IP ranges.

### Private inventory repository

Repository: `JimGat/allstar-node-inventory`
Visibility: private

The private repository defines which nodes exist and their desired state.

Initial layout:

    inventory/
      hosts.yml
      group_vars/
        all.yml
      host_vars/
        cloud-hub.yml
        dvswitch-node.yml
    topology/
      permanent-links.yml
    vault/
      production.yml
    reports/
      redacted/
    docs/
      estate.md
      recovery-order.md

The private repository may contain real node numbers, callsigns, hostnames, addresses, enabled features, port selections, permanent-link relationships, NWS zones, radio models, and hardware calibration values. Secret values remain encrypted with Ansible Vault.

Full configuration backups and private keys remain outside Git. The private repository records their storage location, checksum, date, and recovery procedure.

## Execution architecture

There is no Ansible server.

Ansible runs on demand from the JARVIS VM or, for emergency recovery, Jim's authorized workstation. Managed nodes require SSH and Python but no Ansible agent or persistent management daemon.

Normal data flow:

    public framework repository
              +
    private inventory repository
              +
    local Ansible Vault key
              |
              | SSH
              v
       selected AllStarLink node

The private inventory pins a known public-framework release or commit. A deployment must not silently consume an unreviewed framework revision.

## Secret handling

Ansible Vault is the initial encrypted-secret mechanism because Jim is the sole operator.

One production vault identity is sufficient initially. The encrypted vault file is committed only to the private repository. Its decryption password is never committed.

The JARVIS VM stores the vault password outside both repositories in a mode-0600 file. Jim keeps a recovery copy in his password manager. An authorized workstation may use an interactive password prompt instead of retaining a local file.

Vault-protected values include:

- AllStarLink node passwords
- EchoLink passwords and private account data
- Broadcastify source credentials
- Asterisk Manager credentials
- AllScan administrative secrets
- Direct IAX client secrets
- Cloud/API credentials if later needed

Secret-bearing Ansible tasks use `no_log: true`. Generated target files declare explicit owners, groups, and restrictive modes. Deployment reports contain versions, state, checksums, and test results but not secret values.

Plaintext secrets necessarily exist in the local Ansible process while a deployment runs and in the protected service configuration files on the target node. They do not belong in Git, routine logs, command-line arguments, or chat.

## Installation paths

### Cloud and general-purpose Debian nodes

For Vultr and other general-purpose virtual machines, Ansible begins after the provider has supplied a clean Debian host reachable over SSH.

The initial playbook performs:

1. Preflight checks.
2. Operating-system update and required package installation.
3. ASL3 repository installation.
4. ASL3 package installation.
5. Node configuration.
6. Integration configuration.
7. Firewall configuration.
8. Service enablement.
9. Validation.
10. Backup creation.

ASL3 supports current Debian physical and virtual deployments and documents package-based installation.[1]

### Raspberry Pi nodes

Raspberry Pi and SHARI profiles begin from the official ASL3 Raspberry Pi appliance image. The operator flashes the image and completes the minimum network/SSH bootstrap. Ansible then applies post-image configuration, integrations, validation, and backup.

The project does not initially rebuild or redistribute the base Raspberry Pi image.

### Hardware calibration

Physical-node parameters are established by documented measurement and hardware testing, then stored as host-specific desired state:

- RX and TX audio levels
- COS and PTT polarity
- USB device identity
- CTCSS behavior
- Radio deviation
- Serial protocol and timing
- Allowed radio channels

Automation may restore proven values but must not invent calibration values.

## First reference profile: Vultr radioless hub

### Provisioning assumptions

Vultr provisioning itself remains an explicit operator/provider step in the initial release. The server is created as a parallel replacement so the old HAMVOIP instance remains available for inventory and rollback.

Target resources:

- Debian 13 x86_64
- 2 vCPUs
- 2 GB RAM
- 25-40 GB storage
- SSH key authentication
- Automated Vultr backups
- A snapshot before destructive changes to the old node
- A post-deployment snapshot after acceptance

### Network exposure

Required inbound access:

- SSH TCP, restricted to authorized management sources
- AllStarLink IAX2 UDP on the configured port, normally 4569
- EchoLink UDP 5198-5199
- HTTP/HTTPS only when required for Allmon3 and certificate operation

Required outbound access includes DNS, NTP, HTTP/HTTPS, EchoLink TCP 5200, EchoLink UDP 5198-5199, AllStarLink traffic, and the exact Broadcastify feed endpoint.

Asterisk Manager TCP 5038 must not be exposed publicly.

The AllStarLink Portal IAX port, host firewall, Vultr firewall, and Asterisk bind port must agree.[2][4][8]

### ASL3 registration

The existing AllStarLink node number and node password are reused. ASL3 uses HTTP-based registration by default, configured through `asl-menu` or equivalent generated configuration. The node must not register simultaneously through both HTTP and legacy IAX methods.[3]

The old and new machines must not actively register the same public node identity at the same time.

### Legacy migration boundary

The old HAMVOIP configuration is evidence and source material, not a restore archive. The migration inventories and translates required behavior into the current ASL3 configuration structure. Whole legacy configuration files are not copied over the ASL3 defaults.

Inventory includes:

- Node and server identity
- IAX bind port and codecs
- Node stanza settings
- DTMF and link functions
- Macros and startup behavior
- Telemetry and IDs
- Private/local node definitions
- Direct-client authentication
- EchoLink configuration
- Broadcastify feed process and credentials
- Allmon/Supermon/AllScan configuration
- Custom sounds, scripts, cron jobs, and services
- Current firewall rules and open sockets

ASL3 uses templated node configuration, so host-specific overrides should remain small and explicit.[7]

## Integration design

### EchoLink

The EchoLink role:

- Enables `chan_echolink` only after configuration is complete.
- Renders `/etc/asterisk/echolink.conf` from non-secret and vaulted variables.
- Configures the destination ASL node through `astnode`.
- Preserves intended gains, connection limits, and permit/deny behavior.
- Opens UDP 5198-5199.
- Allows outbound TCP 5200.
- Restarts Asterisk only when required.
- Verifies module loading, registration, socket state, and logs.

During cutover, the old EchoLink instance is stopped before the new one is enabled.[9][11][12]

### Broadcastify

The Broadcastify role uses the current ASL3 service-based method when the installed ASL3 version supports it:

- `rpt_audio_writer` writes node audio to a FIFO.
- `asl-broadcastify@NODE` streams the FIFO through ffmpeg.
- Feed credentials come from Ansible Vault.
- The service is enabled only after Asterisk and the FIFO configuration are valid.
- The old encoder is stopped before the new encoder starts.
- Validation checks the unit, logs, FIFO, and feed status.

The service-based method permits Broadcastify recovery without restarting all of Asterisk.[10]

### Allmon3

Allmon3 is installed and configured as the supported web monitoring interface. Its Asterisk Manager connection uses local or otherwise restricted access. Public access requires HTTPS and authentication; the Manager port remains private. The documented HTTPS path uses a DNS name and certificate automation.[6]

### AllScan

AllScan is a separate third-party role. It must not overwrite ASL3-owned configuration indiscriminately. The role pins a tested release or commit, documents compatibility, and can be disabled without removing or destabilizing ASL3.

AllScan acceptance testing covers application availability, node visibility, authentication, control behavior, and persistence after reboot.

### Permanent DVSwitch link

Exactly one end is authoritative for initiating the permanent connection. The preferred design is for the dedicated DVSwitch node to initiate a permanent transceive connection to the cloud hub and use a startup macro to recreate it after a DVSwitch-node reboot.

This yields:

- Cloud-hub reboot: the DVSwitch-side permanent link retries the far end.
- DVSwitch reboot: its startup macro recreates the link.
- Network interruption: permanent-link retry restores the connection.

Both ends must not be configured to initiate duplicate permanent links. Acceptance testing reboots each endpoint independently and confirms one restored connection with two-way audio and DTMF.[5]

## Error handling and rollback

### Preflight failures

The playbook stops before changes if:

- The target OS or architecture is unsupported.
- SSH privilege escalation is unavailable.
- Required inventory or vaulted variables are absent.
- The target node identity conflicts with the selected host.
- Required ports conflict with another local service.
- A backup of the existing ASL3 configuration cannot be created when one is required.

### Configuration failures

Templates are rendered to temporary paths and syntax-checked where the application supports validation. Services restart only after their configuration is complete. Handlers group restarts so a role does not repeatedly interrupt Asterisk.

A failed integration does not cause the automation to erase the base ASL3 installation. Feature roles must be independently rerunnable.

### Migration rollback

Until final acceptance:

- The old Vultr server remains present but powered off after cutover.
- Its pre-migration snapshot remains available.
- The new server has a captured configuration backup.
- DNS changes use a previously reduced TTL where applicable.
- Rollback stops the new Asterisk/EchoLink/Broadcastify services before reactivating the old server.
- Registration, EchoLink, Broadcastify, and permanent links are revalidated after rollback.

The old instance is not deleted as part of the deployment playbook.

## Validation and acceptance

### Automated checks

The validation playbook reports pass, fail, or not-applicable for:

- Supported OS and architecture
- Installed ASL3 version
- Asterisk service state
- Asterisk CLI responsiveness
- Expected listening sockets
- AllStarLink authentication and node lookup
- Portal/IAX port consistency where observable
- EchoLink module and registration state
- Broadcastify service and FIFO state
- Allmon3 service and local web response
- AllScan service and local web response
- Firewall declaration
- Asterisk Manager non-exposure
- Permanent-link state
- Backup creation
- Service enablement across reboot

The official ASL3 troubleshooting tools include `asl-node-auth-check`, `asl-node-lookup`, service inspection, and node-list verification.[4]

### Manual acceptance checks

Human or remote-node validation is required for:

- Inbound and outbound AllStarLink calls
- Two-way audio quality
- DTMF control
- EchoLink inbound and outbound calls
- EchoLink audio and announcements
- Broadcastify feed presence, quality, metadata, and delay
- Allmon3 and AllScan control behavior
- DVSwitch permanent-link recovery
- Any radio audio, signaling, or channel control

### Reboot matrix

The initial Vultr profile is not accepted until:

1. The new hub survives a cold reboot.
2. Asterisk registers correctly.
3. EchoLink returns.
4. Broadcastify returns.
5. Allmon3 and AllScan return.
6. The DVSwitch permanent link returns.
7. Two-way audio and DTMF still work.
8. A post-reboot backup succeeds.

## Testing strategy

The public repository uses the minimum useful automated test set:

- YAML and Ansible syntax checks
- `ansible-lint` and `yamllint`
- Unit tests for filters or helper scripts
- Template rendering tests with fictional fixtures
- Role idempotence checks where practical
- Disposable Debian integration testing for non-radio roles
- Secret scanning

Live network registration, EchoLink credentials, Broadcastify feeds, and physical radio functions are not exercised in public CI. They are covered by controlled deployment acceptance tests.

## Prompts and Hermes skills

The public repository stores reusable prompts and skills developed from proven procedures. Initial content focuses on:

- Legacy-node inventory
- HAMVOIP-to-ASL3 migration
- ASL3 cloud-node deployment
- Post-deployment validation
- Backup and rollback
- Incident/support-bundle collection

A skill is written only after the corresponding procedure has been exercised or sufficiently validated. Skills reference scripts and templates rather than duplicating large instructions.

## Delivery phases

### Phase 1: Design and repository foundation

- Review and commit this specification.
- Create the public GitHub repository.
- Create the private GitHub inventory repository.
- Add only the minimal repository safeguards and skeleton needed for the first profile.

### Phase 2: Discovery and backup

- Obtain authorized SSH access to the existing HAMVOIP server.
- Produce a redacted inventory and secure backup.
- Record the exact current behavior and integrations.
- Confirm the permanent-link initiator.

### Phase 3: First automation

- Implement the Vultr-hub playbook and its required roles.
- Test role rendering and idempotence in a disposable environment.
- Provision the parallel 2-vCPU Vultr instance.
- Execute a check-mode deployment before the real deployment.

### Phase 4: Cutover and proof

- Stop conflicting services on the old server.
- Activate the new ASL3 identity and integrations in controlled order.
- Run automated and manual acceptance checks.
- Run the reboot matrix.
- Capture backup, report, and snapshot.

### Phase 5: Generalize proven behavior

- Refine roles based on actual deployment findings.
- Write the first operational Hermes skill.
- Add Raspberry Pi post-image support when the first Pi/SHARI build begins.
- Add repeater and radio-control roles only when their hardware is available for proof.

## Completion criteria for the first reference build

The first reference build is complete only when:

- A clean Debian 13 Vultr instance can be configured from the two repositories.
- Re-running the playbook produces no unintended changes.
- AllStarLink registration and bidirectional linking work.
- EchoLink inbound and outbound operation works.
- Broadcastify reports online and carries intelligible node audio.
- Allmon3 and AllScan operate as intended.
- The DVSwitch permanent link recovers from independent endpoint reboots.
- A cold reboot restores all declared services.
- A configuration backup exists off the new instance.
- The old instance remains available for the agreed rollback period.
- The deployment produces a redacted report identifying the exact framework revision used.

## Sources

[1] https://allstarlink.github.io/install/debian/install — Debian Install
[2] https://allstarlink.github.io/basics/portal — AllStarLink Portal
[3] https://allstarlink.github.io/adv-topics/httpreg — HTTP-Based Registration
[4] https://allstarlink.github.io/user-guide/troubleshooting — Basic Troubleshooting Tips
[5] https://allstarlink.github.io/adv-topics/permanentnode — Permanent Node Connection
[6] https://allstarlink.github.io/allmon3/https — Securing Allmon3 with HTTPS
[7] https://allstarlink.github.io/adv-topics/conftmpl — Asterisk Templates
[8] https://allstarlink.github.io/config/iax_conf — iax.conf
[9] https://allstarlink.github.io/adv-topics/echolink — EchoLink Configuration
[10] https://allstarlink.github.io/adv-topics/broadcastify — Streaming Node Audio to Broadcastify
[11] https://allstarlink.github.io/config/echolink_conf — echolink.conf
[12] https://echolink.org/firewall_solutions.htm — EchoLink Firewall Solutions
