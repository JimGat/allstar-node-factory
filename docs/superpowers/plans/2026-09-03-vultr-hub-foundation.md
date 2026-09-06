# Vultr ASL3 Hub Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, test, publish, and use a repeatable Ansible framework that migrates the existing HAMVOIP Vultr hub to a parallel Debian 13 ASL3 hub with EchoLink, Broadcastify, Allmon3, AllScan, backup, validation, and recovery of its permanent DVSwitch link.

**Architecture:** The public repository contains idempotent Ansible roles, fictional fixtures, CI, documentation, and an operations skill. A sibling private repository contains real node inventory and an Ansible Vault file; local Ansible joins both repositories at runtime and deploys over SSH. Production service activation is a separate cutover flag so a fully configured green node cannot duplicate the old node's AllStarLink, EchoLink, or Broadcastify identities before the operator gate.

**Tech Stack:** Ansible Core 2.20, Jinja2, community.general, Python 3.12+, pytest, pytest-testinfra, ansible-lint, yamllint, Gitleaks, GitHub Actions, Debian 13, current repository-supplied ASL3/Asterisk, UFW, Apache/PHP, systemd.

## Global Constraints

- The initial target is Debian 13 x86_64 with 2 vCPUs, 2 GB RAM, 25-40 GB storage, SSH-key access, Vultr automated backups, and no desktop environment.
- Vultr provisioning, provider firewall creation, automated-backup selection, and snapshots remain explicit operator actions in this release.
- Build the replacement in parallel; do not delete or overwrite the old HAMVOIP server.
- Never run the old and new AllStarLink, EchoLink, or Broadcastify production identities concurrently.
- Translate HAMVOIP behavior into ASL3; never copy legacy Asterisk configuration files wholesale.
- Use ASL3's official Debian 13 package repository and the `asl3` package.[1]
- Use HTTP registration in `/etc/asterisk/rpt_http_registrations.conf`; do not also configure IAX registration.[2]
- Keep all production credentials, addresses, topology, backups, and private keys out of the public repository.
- Store the sole production Vault password outside Git at `/home/jarvis/.config/allstar-node-factory/vault-production.key`, mode `0600`, with a recovery copy in Jim's password manager.
- Secret-bearing tasks use both `no_log: true` and `diff: false`; generated secret files declare explicit owner, group, and restrictive mode.
- The public framework never provisions or modifies Vultr through an API in this release.
- The separate DVSwitch node is not rebuilt by this plan.
- The preferred permanent-link initiator is the DVSwitch node; inventory must explicitly declare `external` or `local`, and the cloud hub must not create a second initiating link.
- Public CI never uses live node credentials, EchoLink, Broadcastify, or a real AllStarLink identity.
- All production writes require an explicit `--limit cloud-hub`; all playbook examples include that limit.
- Do not push implementation directly to `main`; execute on `feat/vultr-hub-foundation`, open a PR, and merge only after Jim explicitly approves release/promotion.

---

## File Map

### Public repository

- `.github/workflows/ci.yml` — offline lint, unit, render, and secret-scan gates.
- `.gitignore` — excludes Python state, local inventories, Vault keys, backups, reports, and decrypted files.
- `.python-version` — reviewed controller Python version.
- `.ansible-lint` — production lint profile and local exclusions.
- `.pre-commit-config.yaml` — pinned local policy checks, including Gitleaks.
- `.gitleaks.toml` — Vault-aware leak-detection policy.
- `.yamllint.yml` — YAML conventions shared by local and CI checks.
- `LICENSE` — MIT license for reusable automation and documentation.
- `CHANGELOG.md` — release history.
- `ansible.cfg` — repository-local Ansible defaults without production inventory paths.
- `requirements.yml` — collection dependency on `community.general`.
- `requirements-dev.txt` — exact reviewed development/test dependencies.
- `playbooks/vultr-hub.yml` — staged configure/activate deployment entry point.
- `playbooks/validate.yml` — read-only health and acceptance evidence collection.
- `playbooks/backup.yml` — encrypted-content-aware target-side configuration backup.
- `roles/asl3_core/` — OS gate, ASL repository/package installation, radioless node configuration, and HTTP registration.
- `roles/firewall/` — UFW policy and explicitly declared inbound rules.
- `roles/echolink/` — EchoLink config/module activation and health checks.
- `roles/broadcastify/` — ASL3 modern FIFO/service configuration and health checks.
- `roles/allmon3/` — supported package, AMI configuration, web user, and local health checks.
- `roles/allscan/` — commit-pinned third-party web application deployment without running its interactive installer.
- `roles/permanent_link/` — exactly-one-initiator configuration and assertions.
- `roles/validation/` — non-secret JSON report generation and pass/fail assertions.
- `roles/backup/` — target-side archive, checksum, retention, and manifest.
- `inventories/example/` — fictional public inventory using documentation IP space and a fake callsign.
- `tests/unit/` — static contract and renderer tests.
- `tests/integration/` — disposable Debian role tests that do not register or stream.
- `scripts/check_no_secrets.py` — repository-specific leak detector.
- `scripts/check_framework_pin.py` — refuses deployment from a dirty or unlocked public framework checkout.
- `scripts/validate_inventory.py` — public/private variable-contract validator.
- `docs/migration/hamvoip-to-asl3.md` — legacy evidence capture and translation matrix.
- `docs/operations/vultr-cutover.md` — blue/green cutover and rollback commands.
- `docs/operations/backup-restore.md` — backup custody, restore, and checksum procedure.
- `docs/profiles/vultr-radioless-hub.md` — profile inputs, outputs, and acceptance criteria.
- `docs/security/secrets.md` — Vault boundary and redaction rules.
- `prompts/inventory-legacy-node.md` — repeatable evidence-collection prompt.
- `skills/allstar-node-operations/SKILL.md` — project-local operator procedure.

### Private repository

- `inventory/hosts.yml` — real SSH target aliases and connection variables.
- `inventory/group_vars/all.yml` — estate-wide non-secret defaults.
- `inventory/host_vars/cloud-hub.yml` — real non-secret desired state for the new hub.
- `inventory/host_vars/dvswitch-node.yml` — real peer identity and whether it is managed externally.
- `topology/permanent-links.yml` — authoritative link ownership declaration.
- `vault/production.yml` — Ansible-Vault-encrypted credentials only.
- `reports/redacted/.gitkeep` — destination for deliberately redacted acceptance summaries.
- `docs/estate.md` — actual estate and backup-location metadata.
- `docs/recovery-order.md` — private recovery order.

---

### Task 1: Establish the Repository Quality Baseline

**Files:**
- Create: `.gitignore`
- Create: `.python-version`
- Create: `.ansible-lint`
- Create: `.yamllint.yml`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `ansible.cfg`
- Create: `requirements.yml`
- Create: `requirements-dev.txt`
- Create: `tests/unit/test_repository_contract.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the approved design specification.
- Produces: a reproducible local test environment and the path conventions every later task uses.

- [ ] **Step 1: Create the implementation branch**

Run:

```bash
git switch -c feat/vultr-hub-foundation
```

Expected: `git branch --show-current` prints `feat/vultr-hub-foundation`.

- [ ] **Step 2: Write the failing repository-contract test**

Create `tests/unit/test_repository_contract.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = {
    ".gitignore",
    ".python-version",
    ".ansible-lint",
    ".yamllint.yml",
    "LICENSE",
    "CHANGELOG.md",
    "ansible.cfg",
    "requirements.yml",
    "requirements-dev.txt",
}


def test_required_repository_files_exist() -> None:
    missing = sorted(path for path in REQUIRED if not (ROOT / path).exists())
    assert missing == []


def test_ansible_cfg_never_names_private_inventory() -> None:
    text = (ROOT / "ansible.cfg").read_text(encoding="utf-8")
    assert "allstar-node-inventory" not in text
    assert "vault-production.key" not in text
```

- [ ] **Step 3: Run the test and verify the expected failure**

Run:

```bash
python3 -m pytest tests/unit/test_repository_contract.py -q
```

Expected: failure listing the missing baseline files.

- [ ] **Step 4: Add the baseline files**

Create `ansible.cfg`:

```ini
[defaults]
roles_path = ./roles
host_key_checking = True
retry_files_enabled = False
interpreter_python = auto_silent
deprecation_warnings = True
stdout_callback = default
display_args_to_stdout = False

[privilege_escalation]
become = True
become_method = sudo
```

Create `requirements.yml`:

```yaml
---
collections:
  - name: community.general
    version: "13.3.0"
```

Create `requirements-dev.txt`:

```text
ansible-core==2.20.8
ansible-lint==26.8.0
yamllint==1.38.0
pytest==9.1.1
pytest-testinfra==10.2.2
pre-commit==4.6.2
```

Create `.yamllint.yml`:

```yaml
---
extends: default
rules:
  line-length:
    max: 120
  truthy:
    allowed-values: ["true", "false"]
```

Create `.python-version` containing `3.13`, and `.ansible-lint`:

```yaml
---
profile: production
exclude_paths:
  - .venv/
  - .cache/
```

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
*.retry
.vault-password
vault-production.key
inventories/production/
reports/
backups/
*.tar.gz
*.decrypted.yml
```

Create `CHANGELOG.md` with an `Unreleased` section, add the MIT license naming `Jim Gatwood`, and update `README.md` with setup commands:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
ansible-galaxy collection install -r requirements.yml
```

- [ ] **Step 5: Run baseline validation**

Run:

```bash
python3 -m pytest tests/unit/test_repository_contract.py -q
yamllint .
```

Expected: all commands exit `0`.

- [ ] **Step 6: Commit**

```bash
git add .gitignore .python-version .ansible-lint .yamllint.yml LICENSE CHANGELOG.md README.md ansible.cfg requirements.yml requirements-dev.txt tests/unit/test_repository_contract.py
git commit -m "chore: establish Ansible repository baseline"
```

---

### Task 2: Define and Enforce the Inventory Contract

**Files:**
- Create: `scripts/validate_inventory.py`
- Create: `scripts/check_framework_pin.py`
- Create: `tests/fixtures/inventory/valid.yml`
- Create: `tests/fixtures/inventory/missing-secret.yml`
- Create: `tests/unit/test_validate_inventory.py`
- Create: `tests/unit/test_check_framework_pin.py`
- Create: `inventories/example/hosts.yml`
- Create: `inventories/example/group_vars/all.yml`
- Create: `inventories/example/host_vars/example-cloud-hub.yml`

**Interfaces:**
- Consumes: YAML dictionaries loaded from public examples or the private inventory repository, plus private `framework.lock.yml` metadata.
- Produces: `validate(data: dict) -> list[str]` for inventory and `validate_pin(lock: dict, head: str, dirty: bool) -> list[str]` for framework identity; an empty list means the relevant contract is satisfied.

- [ ] **Step 1: Write failing validator tests**

Create `tests/unit/test_validate_inventory.py`:

```python
from pathlib import Path
import importlib.util
import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_inventory", ROOT / "scripts" / "validate_inventory.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load(name: str) -> dict:
    return yaml.safe_load((ROOT / "tests/fixtures/inventory" / name).read_text())


def test_valid_inventory_has_no_errors() -> None:
    assert MODULE.validate(load("valid.yml")) == []


def test_missing_secret_reference_is_rejected() -> None:
    errors = MODULE.validate(load("missing-secret.yml"))
    assert "vault_asl_node_password is required" in errors


def test_activation_requires_explicit_boolean() -> None:
    data = load("valid.yml")
    data.pop("production_services_enabled")
    assert "production_services_enabled must be true or false" in MODULE.validate(data)
```

Create `tests/unit/test_check_framework_pin.py` with cases proving that a clean checkout at the exact 40-character SHA passes, while a dirty tree, short SHA, or mismatched HEAD fails without printing repository contents.

- [ ] **Step 2: Add complete fictional fixtures**

`tests/fixtures/inventory/valid.yml` must contain:

```yaml
asl_node_number: "1998"
asl_callsign: "N0CALL"
asl_iax_port: 4569
asl_rxchannel: "Local/pseudo"
production_services_enabled: false
management_cidrs: ["192.0.2.0/24"]
echolink_enabled: true
echolink_call: "N0CALL-L"
echolink_node: "000001"
echolink_astnode: "1998"
broadcastify_enabled: true
allmon3_enabled: true
allscan_enabled: true
permanent_link_enabled: true
permanent_link_peer_node: "1999"
permanent_link_initiator: "external"
vault_asl_node_password: "fixture-only-123"
vault_echolink_password: "fixture-only-123"
vault_broadcastify_password: "fixture-only-123"
vault_ami_secret: "fixture-only-123"
vault_allmon3_password: "fixture-only-123"
vault_allscan_password: "fixture-only-123"
```

`missing-secret.yml` is identical except that `vault_asl_node_password` is omitted.

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
python3 -m pytest tests/unit/test_validate_inventory.py -q
python3 -m pytest tests/unit/test_check_framework_pin.py -q
```

Expected: import failures because both validator scripts do not exist.

- [ ] **Step 4: Implement the validator**

Create `scripts/validate_inventory.py` with `yaml.safe_load`, a `validate(data)` function, and a CLI. The validator must check:

```python
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
```

It must reject non-numeric 4-6 digit ASL node numbers, non-integer ports outside `1..65535`, empty management CIDRs, non-boolean `production_services_enabled`, permanent links without a peer, initiators outside `external|local`, and an enabled AllScan password outside its upstream 6-16 character range. CLI usage is:

```bash
python3 scripts/validate_inventory.py tests/fixtures/inventory/valid.yml
```

It prints one error per line to stderr and exits `1`, or prints `inventory contract: OK` and exits `0`.

Implement `scripts/check_framework_pin.py` so its CLI accepts `--framework` and `--lock`, reads `repository`, `ref`, and `commit`, requires a full lowercase 40-character hexadecimal commit, runs `git rev-parse HEAD` plus `git status --porcelain`, and exits nonzero if HEAD differs or the tree is dirty. It prints only the expected/actual SHAs and cleanliness state.

- [ ] **Step 5: Create the fictional public inventory**

Use `example-cloud-hub`, `ansible_host: 192.0.2.10`, callsign `N0CALL`, nodes `1998` and `1999`, and fixture-only secrets. Every file begins with a comment that it must never be used for production.

- [ ] **Step 6: Run tests and CLI verification**

```bash
python3 -m pytest tests/unit/test_validate_inventory.py -q
python3 -m pytest tests/unit/test_check_framework_pin.py -q
python3 scripts/validate_inventory.py tests/fixtures/inventory/valid.yml
python3 scripts/validate_inventory.py tests/fixtures/inventory/missing-secret.yml && exit 1 || test $? -eq 1
```

Expected: tests pass, valid fixture exits `0`, invalid fixture exits `1`.

- [ ] **Step 7: Commit**

```bash
git add scripts/validate_inventory.py scripts/check_framework_pin.py tests/fixtures tests/unit/test_validate_inventory.py tests/unit/test_check_framework_pin.py inventories/example
git commit -m "feat: define Vultr hub inventory contract"
```

---

### Task 3: Implement the ASL3 Core Role

**Files:**
- Create: `roles/asl3_core/defaults/main.yml`
- Create: `roles/asl3_core/handlers/main.yml`
- Create: `roles/asl3_core/tasks/main.yml`
- Create: `roles/asl3_core/templates/rpt-node-factory.conf.j2`
- Create: `roles/asl3_core/templates/rpt_http_registrations.conf.j2`
- Create: `roles/asl3_core/templates/manager-node-factory.conf.j2`
- Create: `tests/unit/test_asl3_core_templates.py`

**Interfaces:**
- Consumes: `asl_node_number`, `asl_callsign`, `asl_iax_port`, `asl_rxchannel`, `vault_asl_node_password`, `vault_ami_secret`, and `production_services_enabled`.
- Produces: installed `asl3`, a radioless node stanza, HTTP registration, a loopback-only AMI account, and handler `Restart asterisk`.

ASL3 supports Debian 13 and installs through its repository package followed by `apt install asl3`.[1][13] Node-specific `rpt.conf` settings inherit from the ASL3 `[node-main]` template, so the managed fragment stays deliberately small.[10]

- [ ] **Step 1: Write failing template tests**

The test renders all three Jinja templates with `jinja2.Environment(undefined=StrictUndefined)` and asserts:

```python
assert "[1998](node-main)" in rpt
assert "rxchannel = Local/pseudo" in rpt
assert "register => 1998:fixture-only-123@register.allstarlink.org" in registrations
assert "bindaddr = 127.0.0.1" in manager
assert "secret = fixture-only-123" in manager
assert "register =>" not in rpt
```

It must also render `startup_macro = *8131999` only when `permanent_link_initiator == "local"`.

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m pytest tests/unit/test_asl3_core_templates.py -q
```

Expected: failure because the role templates do not exist.

- [ ] **Step 3: Implement preflight and package installation**

`tasks/main.yml` must:

1. assert `ansible_distribution == 'Debian'`, major version `13`, architecture `x86_64|amd64`, `ansible_become` works, and every Task 2 required variable exists;
2. install `ca-certificates`, `curl`, `gnupg`, `sudo`, `ufw`, and `python3`;
3. download `https://repo.allstarlink.org/public/asl-apt-repos.deb13_all.deb` to `/var/cache/apt/archives/asl-apt-repos.deb13_all.deb` with the reviewed SHA-256 `22ae4334fc8780f105c33c0017ff4e2663198d3b52d977db48949a5a732889d5`[16];
4. install that `.deb` with `ansible.builtin.apt: deb=...`;
5. update the apt cache and install `asl3`;
6. create `/etc/asterisk/node-factory` owned by `root:asterisk` mode `0750`;
7. assert the package defaults require `bridge_softmix.so`, `chan_bridge_media.so`, and `chan_iax2.so`, load `res_timing_timerfd.so`, and do not load DAHDI for the `Local/pseudo` hub;
8. back up `/etc/asterisk` to the backup role before replacing any registration file if `node_factory_require_prechange_backup` is true.

Use `changed_when` only when command output cannot express state; do not mark read-only probes changed.

- [ ] **Step 4: Render the node fragment**

`rpt-node-factory.conf.j2` contains exactly:

```ini
; Managed by allstar-node-factory. Local edits will be replaced.
[{{ asl_node_number }}](node-main)
rxchannel = {{ asl_rxchannel }}
duplex = 2
idrecording = |i{{ asl_callsign }}
statpost_url = http://stats.allstarlink.org/uhandler
nodes = node-factory-nodes
{% if permanent_link_enabled | bool and permanent_link_initiator == 'local' %}
startup_macro = *813{{ permanent_link_peer_node }}
{% endif %}

[node-factory-nodes]
{{ asl_node_number }} = radio@127.0.0.1:{{ asl_iax_port }}/{{ asl_node_number }},NONE
{% for node, route in private_node_routes | default({}) | dictsort %}
{{ node }} = {{ route }}
{% endfor %}
```

Add one managed `#include /etc/asterisk/node-factory/rpt-node-factory.conf` line to `/etc/asterisk/rpt.conf`. Assert before insertion that the desired `[NODE]` stanza does not already exist outside `/etc/asterisk/node-factory`; fail with a migration message rather than creating duplicate stanzas.

- [ ] **Step 5: Render HTTP registration and AMI configuration**

`rpt_http_registrations.conf.j2` contains:

```ini
[general]
register_interval = 180

[registrations]
register => {{ asl_node_number }}:{{ vault_asl_node_password }}@register.allstarlink.org
```

ASL3 uses this file by default and warns against simultaneous HTTP and IAX registration.[2] Template it mode `0640`, owner `root`, group `asterisk`, with `no_log: true` and `diff: false`. Assert that active `register =>` lines are absent from `/etc/asterisk/iax.conf`; use a section-aware edit to set its `[general]` `bindport` to `asl_iax_port`, preserving the packaged `[radio]` peer and codec policy.

`manager-node-factory.conf.j2` contains:

```ini
[node-factory]
secret = {{ vault_ami_secret }}
deny = 0.0.0.0/0.0.0.0
permit = 127.0.0.1/255.255.255.255
read = all
write = all
```

Insert one `#include /etc/asterisk/node-factory/manager-node-factory.conf` line into `/etc/asterisk/manager.conf`; template the fragment mode `0640`, owner `root`, group `asterisk`, with `no_log: true` and `diff: false`. Assert the packaged `[general]` section binds AMI to `127.0.0.1` before enabling either dashboard.

- [ ] **Step 6: Add safe handlers and activation behavior**

Notify one `Restart asterisk` handler from all config changes. The handler runs only when `production_services_enabled | bool`; otherwise it prints that activation is deferred. Always enable Asterisk for boot only after production activation.

- [ ] **Step 7: Run template and syntax tests**

```bash
python3 -m pytest tests/unit/test_asl3_core_templates.py -q
ansible-lint roles/asl3_core
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add roles/asl3_core tests/unit/test_asl3_core_templates.py
git commit -m "feat: add ASL3 radioless hub core role"
```

---

### Task 4: Implement the Host Firewall Role

**Files:**
- Create: `roles/firewall/defaults/main.yml`
- Create: `roles/firewall/tasks/main.yml`
- Create: `tests/unit/test_firewall_contract.py`

**Interfaces:**
- Consumes: `management_cidrs`, `asl_iax_port`, feature flags, `web_public_enabled`, and `web_tls_enabled`.
- Produces: default-deny UFW inbound policy, required allow rules, and no public AMI rule.

- [ ] **Step 1: Write the failing static contract test**

The test loads `roles/firewall/tasks/main.yml` as YAML and checks the serialized content contains `community.general.ufw`, `default`, `deny`, `management_cidrs`, `asl_iax_port`, `5198`, and `5199`, and does not contain `5038`.

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_firewall_contract.py -q
```

Expected: missing role file.

- [ ] **Step 3: Implement the UFW policy in lockout-safe order**

The role must:

1. assert `management_cidrs` is a non-empty list;
2. install `ufw`;
3. set default incoming deny and outgoing allow;
4. allow TCP 22 from each management CIDR before enabling UFW;
5. allow UDP `asl_iax_port` from `0.0.0.0/0`;
6. allow UDP 5198 and 5199 only when EchoLink is enabled;
7. allow TCP 80 only when `web_public_enabled` is true;
8. allow TCP 443 only when both `web_public_enabled` and `web_tls_enabled` are true;
9. enable UFW;
10. run `ufw status verbose` with `changed_when: false` and register it for validation.

Do not create an inbound rule for TCP 5038. Outbound remains allowed in this initial release so DNS, NTP, package repositories, AllStarLink, EchoLink TCP 5200, and the assigned Broadcastify endpoint can function.

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/unit/test_firewall_contract.py -q
ansible-lint roles/firewall
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add roles/firewall tests/unit/test_firewall_contract.py
git commit -m "feat: add lockout-safe Vultr host firewall"
```

---

### Task 5: Implement the EchoLink Role

**Files:**
- Create: `roles/echolink/defaults/main.yml`
- Create: `roles/echolink/handlers/main.yml`
- Create: `roles/echolink/tasks/main.yml`
- Create: `roles/echolink/templates/echolink.conf.j2`
- Create: `tests/unit/test_echolink_template.py`

**Interfaces:**
- Consumes: `echolink_*`, `vault_echolink_password`, `production_services_enabled`.
- Produces: protected `/etc/asterisk/echolink.conf`, a deliberate module load setting, and EchoLink health facts.

ASL3 ships `chan_echolink` disabled; enabling it requires changing `modules.conf`, rendering `echolink.conf`, opening UDP 5198-5199, and restarting Asterisk.[3]

- [ ] **Step 1: Write the failing template test**

Render with fictional values and assert all required fields are present and the plaintext password appears exactly once:

```python
for expected in (
    "[el0]", "call = N0CALL-L", "pwd = fixture-only-123",
    "name = Example Operator", "qth = Example City", "email = example@example.invalid",
    "node = 000001", "astnode = 1998",
):
    assert expected in rendered
```

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_echolink_template.py -q
```

- [ ] **Step 3: Implement protected configuration rendering**

The template must render `[el0]` with `call`, `pwd`, `name`, `qth`, `email`, `node`, `astnode`, `context = radio-secure`, `lat`, `lon`, `freq`, `tone`, `power`, `height`, `gain`, and `dir`. Task defaults use neutral numeric values and require identity fields when enabled. Write it `root:asterisk`, mode `0640`, with `no_log: true` and `diff: false`.

- [ ] **Step 4: Implement module activation and deferred service start**

Use `ansible.builtin.lineinfile` to replace the stock `noload = chan_echolink.so` line with `load = chan_echolink.so` only when both `echolink_enabled` and `production_services_enabled` are true. In staging, keep or restore `noload = chan_echolink.so`. Notify the shared Asterisk restart handler.

Health probes run:

```bash
asterisk -rx 'module show like chan_echolink.so'
ss -lunp
journalctl -u asterisk --since '-5 minutes' --no-pager
```

They use `changed_when: false`, redact logs from normal output, and expose only boolean facts to the validation role.

- [ ] **Step 5: Test and commit**

```bash
python3 -m pytest tests/unit/test_echolink_template.py -q
ansible-lint roles/echolink
git add roles/echolink tests/unit/test_echolink_template.py
git commit -m "feat: add staged EchoLink configuration role"
```

---

### Task 6: Implement the Broadcastify Role

**Files:**
- Create: `roles/broadcastify/defaults/main.yml`
- Create: `roles/broadcastify/tasks/main.yml`
- Create: `roles/broadcastify/templates/broadcastify.conf.j2`
- Create: `tests/unit/test_broadcastify_template.py`

**Interfaces:**
- Consumes: node number, Broadcastify endpoint/metadata variables, `vault_broadcastify_password`, and `production_services_enabled`.
- Produces: `/etc/asterisk/broadcastify/NODE.conf`, `outstreamcmd` in the managed node fragment, and enabled `asl-broadcastify@NODE` only at cutover.

The modern supported path requires `asl3` version `3.18.2-2` or later, uses `rpt_audio_writer` plus a FIFO, and runs a templated `asl-broadcastify@NODE` service so streaming can recover without restarting Asterisk.[4]

- [ ] **Step 1: Write the failing template test**

Assert the rendered file contains:

```text
FIFO=/var/lib/asterisk/1998.fifo
ICECAST_HOST=audio.example.invalid
ICECAST_PORT=80
ICECAST_MOUNT=/example
ICECAST_USER=source
ICECAST_PASSWORD=fixture-only-123
INPUT_SAMPLERATE=8000
INPUT_CHANNELS=1
OUTPUT_BITRATE=16k
```

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_broadcastify_template.py -q
```

- [ ] **Step 3: Implement version and binary gates**

Collect `dpkg-query -W -f='${Version}' asl3`, assert it is not older than `3.18.2-2` using `dpkg --compare-versions`, and assert `/usr/libexec/asl3/rpt_audio_writer` exists. Install `ffmpeg`. All probes are read-only and `changed_when: false`.

- [ ] **Step 4: Render protected stream configuration**

Create `/etc/asterisk/broadcastify` mode `0750`, render `NODE.conf` mode `0640`, owner `root`, group `asterisk`, and mark the task with `no_log: true` and `diff: false`. Treat the file as a sourced shell environment: render every external string through Ansible's `quote` filter and reject newline or NUL characters before rendering. Add this line to the managed node stanza when enabled:

```ini
outstreamcmd = /usr/libexec/asl3/rpt_audio_writer,/var/lib/asterisk/{{ asl_node_number }}.fifo
```

- [ ] **Step 5: Stage or activate the systemd unit**

When `production_services_enabled` is false, stop and disable `asl-broadcastify@NODE` but retain configuration. When true, enable and start it after Asterisk has restarted. Validate the unit, FIFO path, and last five minutes of journal output without returning feed credentials.

- [ ] **Step 6: Test and commit**

```bash
python3 -m pytest tests/unit/test_broadcastify_template.py -q
ansible-lint roles/broadcastify
git add roles/broadcastify tests/unit/test_broadcastify_template.py
git commit -m "feat: add modern Broadcastify streaming role"
```

---

### Task 7: Implement the Allmon3 Role

**Files:**
- Create: `roles/allmon3/defaults/main.yml`
- Create: `roles/allmon3/handlers/main.yml`
- Create: `roles/allmon3/tasks/main.yml`
- Create: `roles/allmon3/templates/allmon3.ini.j2`
- Create: `roles/allmon3/templates/web.ini.j2`
- Create: `roles/allmon3/templates/user-restrictions.j2`
- Create: `tests/unit/test_allmon3_template.py`

**Interfaces:**
- Consumes: node number, loopback AMI user/secret, `allmon3_username`, `vault_allmon3_password`, and web-exposure flags.
- Produces: supported `allmon3` package, loopback connection configuration, authenticated web user, and local HTTP health result.

Allmon3 is installed as the `allmon3` package on Debian 13.[5] Its node configuration is `/etc/allmon3/allmon3.ini` and changes require restarting `allmon3`.[6]

- [ ] **Step 1: Write the failing template test**

Assert fictional rendering equals:

```ini
[1998]
host = 127.0.0.1
port = 5038
user = node-factory
pass = fixture-only-123
```

Also assert `web.ini` binds the WebSocket listeners to `127.0.0.1` and the restriction file limits the configured user to the local node.

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_allmon3_template.py -q
```

- [ ] **Step 3: Install and configure Allmon3**

Install `allmon3`, `apache2`, and `python3-pexpect`. Render `/etc/allmon3/allmon3.ini` owner `allmon3:allmon3`, mode `0660`, with `no_log: true` and `diff: false`. Render `/etc/allmon3/web.ini` with `HTTP_PORT = 16080`, `WS_PORT_START = 16700`, and `WS_BIND_ADDR = 127.0.0.1`. Keep AMI and all Allmon3 backend listeners on loopback only; expose only the Apache frontend.

- [ ] **Step 4: Manage the Allmon3 login idempotently**

Compute a controller-side SHA-256 digest of `allmon3_username + NUL + vault_allmon3_password`. Compare it to `/var/lib/allstar-node-factory/allmon3-user.sha256`. When absent or changed, run `ansible.builtin.expect` against `allmon3-passwd USER`, answering the password and confirmation prompts, with `no_log: true`; then write the digest sentinel mode `0600`. Notify `Reload allmon3`.

Render `/etc/allmon3/user-restrictions` as `allmon3_username | asl_node_number`, owner `allmon3:allmon3`, mode `0660`; a missing user entry otherwise grants that user command access to every configured node.[12]

- [ ] **Step 5: Enable and validate**

Enable/start `allmon3` and Apache when its feature flag is true. Run `apache2ctl configtest`, query `http://127.0.0.1:16080/node/listall`, and use `ansible.builtin.uri` against `http://127.0.0.1/allmon3/`; accept only `200` or an expected authenticated redirect. Assert TCP 5038, 16080, 16700, and 16701 are not listening on non-loopback addresses.

- [ ] **Step 6: Test and commit**

```bash
python3 -m pytest tests/unit/test_allmon3_template.py -q
ansible-lint roles/allmon3
git add roles/allmon3 tests/unit/test_allmon3_template.py
git commit -m "feat: add authenticated Allmon3 role"
```

---

### Task 8: Implement the Commit-Pinned AllScan Role

**Files:**
- Create: `roles/allscan/defaults/main.yml`
- Create: `roles/allscan/handlers/main.yml`
- Create: `roles/allscan/tasks/main.yml`
- Create: `roles/allscan/templates/allscan-security.conf.j2`
- Create: `tests/unit/test_allscan_contract.py`

**Interfaces:**
- Consumes: `allscan_enabled`, `allscan_commit`, `allscan_web_root`, and `allscan_web_group`.
- Produces: pinned application files at `/var/www/html/allscan`, persistent `/etc/allscan`, and an explicit first-run-admin acceptance gate.

The upstream README supports ASL3 and lists PHP, SQLite, curl, unzip, Avahi, and `asl3-tts` dependencies.[8] Its installer follows the moving `main` branch and asks interactive questions, including an optional OS upgrade, so automation must not execute it unattended.[9]

AllScan remains a third-party project outside the AllStarLink project's support boundary.[11] Upstream does not publish an explicit Debian 13/PHP 8.4 compatibility matrix.[8][9] Keep it isolated as an optional role, prove it in the disposable Debian 13 integration test and the staged Vultr build, and never let an AllScan failure undo or destabilize the core ASL3 node.

- [ ] **Step 1: Write the failing contract test**

The test loads role defaults/tasks and asserts:

```python
assert defaults["allscan_commit"] == "0309f2ff8fc5d2baf1c1df1afc13acb59781cd97"
assert "AllScanInstallUpdate.php" not in serialized_tasks
assert "https://github.com/davidgsd/AllScan/archive/" in serialized_tasks
assert "/etc/allscan" in serialized_tasks
assert "/var/www/html/allscan" in serialized_tasks
```

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_allscan_contract.py -q
```

- [ ] **Step 3: Implement pinned deployment**

Set `allscan_commit` to the reviewed commit `0309f2ff8fc5d2baf1c1df1afc13acb59781cd97` and `allscan_archive_sha256` to `bad4e2992ba8778e75e6c8cf4df3d1f2f80b23a6511dc7a73edefa8f220c7840`.[15][17] Install `apache2`, `libapache2-mod-php`, `php`, `php-sqlite3`, `php-curl`, and `asl3-update-nodelist`. Do not install or enable Avahi or optional AllScan DTMF/TTS helpers on the VPS. Download the commit tarball from:

```text
https://github.com/davidgsd/AllScan/archive/0309f2ff8fc5d2baf1c1df1afc13acb59781cd97.tar.gz
```

Verify the archive against `allscan_archive_sha256`, unpack to a temporary directory, synchronize application code into `/var/www/html/allscan` without deleting user `.ini` files, and set directories `root:www-data 0775`, files `root:www-data 0664`. Create `/etc/allscan` as `root:www-data 0770`; never replace `allscan.db` if present, and tighten it to `root:www-data 0640` after creation. Explicitly enable and start `asl3-update-astdb.timer`, run its oneshot service once, and verify `/var/www/html/allscan/astdb.txt` resolves to a non-empty `/var/lib/asterisk/astdb.txt`.

Render and enable an Apache configuration that denies all HTTP access to `/allscan/_tools/` and denies direct download of `.ini`, `.db`, and `.bak` files. Run `apache2ctl configtest` before reloading Apache.

- [ ] **Step 4: Implement first-run and health gates**

Use `uri` against `http://127.0.0.1/allscan/`. Record one of:

- `PASS` — HTTP success and database exists;
- `INIT_REQUIRED` — HTTP success but `/etc/allscan/allscan.db` is absent;
- `FAIL` — no expected local HTTP response.

Do not write directly to the undocumented SQLite schema. The cutover runbook requires Jim to create the first Superuser over the protected management path, set **Public Permission** to **None**, and then rerun validation. Keep `web_public_enabled: false` until those steps pass; the upstream default is read-only but still reveals live node and favorites data.

- [ ] **Step 5: Test and commit**

```bash
python3 -m pytest tests/unit/test_allscan_contract.py -q
ansible-lint roles/allscan
git add roles/allscan tests/unit/test_allscan_contract.py
git commit -m "feat: add commit-pinned AllScan role"
```

---

### Task 9: Enforce Exactly-One Permanent-Link Initiator

**Files:**
- Create: `roles/permanent_link/defaults/main.yml`
- Create: `roles/permanent_link/tasks/main.yml`
- Create: `tests/unit/test_permanent_link_contract.py`

**Interfaces:**
- Consumes: `permanent_link_enabled`, `permanent_link_peer_node`, `permanent_link_initiator`.
- Produces: either a local `startup_macro = *813PEER` or an explicit external-owner assertion, never both.

Permanent links retry through network loss and far-end reboot, but a near-end reboot requires `startup_macro`; `*813NODE` creates a permanent transceive link.[7]

- [ ] **Step 1: Write failing tests for both ownership modes**

Render the ASL3 node template twice and assert:

```python
assert "startup_macro = *8131999" in render(initiator="local")
assert "startup_macro" not in render(initiator="external")
```

Load role tasks and assert they reject any initiator outside `external|local` and a peer equal to the local node.

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_permanent_link_contract.py -q
```

- [ ] **Step 3: Implement role assertions and validation facts**

When enabled, assert peer is a 4-6 digit numeric string, differs from local node, and ownership is explicit. `local` sets the template fact that adds `startup_macro`; `external` asserts no startup macro is present in the cloud's managed fragment. Read `asterisk -rx 'rpt lstats NODE'` and set `permanent_link_present` only when the exact peer appears once.

- [ ] **Step 4: Test and commit**

```bash
python3 -m pytest tests/unit/test_permanent_link_contract.py -q
ansible-lint roles/permanent_link
git add roles/permanent_link roles/asl3_core/templates/rpt-node-factory.conf.j2 tests/unit/test_permanent_link_contract.py
git commit -m "feat: enforce permanent-link ownership"
```

---

### Task 10: Add Backup and Redacted Validation Roles

**Files:**
- Create: `roles/backup/defaults/main.yml`
- Create: `roles/backup/tasks/main.yml`
- Create: `roles/validation/defaults/main.yml`
- Create: `roles/validation/tasks/main.yml`
- Create: `roles/validation/templates/report.json.j2`
- Create: `tests/unit/test_validation_report.py`

**Interfaces:**
- Consumes: feature flags, service facts, backup root, node number, and health results from prior roles.
- Produces: mode-0600 target archive, SHA-256 checksum, retention metadata, and a redacted JSON report with `PASS|FAIL|NOT_APPLICABLE|INIT_REQUIRED` statuses.

- [ ] **Step 1: Write the failing report test**

Render a report with fixture secrets in the input context and assert:

```python
report = json.loads(rendered)
assert report["node"] == "1998"
assert report["checks"]["asterisk"] == "PASS"
assert "fixture-only-123" not in rendered
assert set(report["checks"].values()) <= {
    "PASS", "FAIL", "NOT_APPLICABLE", "INIT_REQUIRED"
}
```

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_validation_report.py -q
```

- [ ] **Step 3: Implement secure target-side backups**

When `asl-backup-menu` is installed, run its noninteractive `backup-local` action and verify that it creates a readable `ASL_*.tgz` in `/var/asl-backups`.[18] Then create `/var/backups/allstar-node-factory` mode `0700`. Use `community.general.archive` to create a supplemental timestamped mode-`0600` archive containing only existing paths from:

```yaml
backup_paths:
  - /etc/asterisk
  - /etc/allmon3
  - /etc/allscan
  - /etc/ufw
  - /etc/systemd/system
```

Write a `.sha256` file mode `0600`, retain the newest five archives, and never fetch archives into either Git repository. Return only archive path, timestamp, byte size, and checksum to the report. Mark archive creation `no_log: true` because it packages secrets.

- [ ] **Step 4: Implement validation checks**

Collect and normalize:

- supported OS/architecture;
- installed ASL3 version;
- `asl-check-install` completes without a fatal finding;
- `asl-node-auth-check` output contains no `Error:` lines when production identity is active;
- Asterisk enabled/active and `asterisk -rx 'core show uptime'` success;
- expected IAX/EchoLink/web sockets;
- no non-loopback TCP 5038 listener;
- `rpt show registrations` output contains the local node exactly once when active;
- EchoLink module state;
- Broadcastify service/FIFO state;
- Allmon3 local HTTP state;
- AllScan local HTTP/database state;
- UFW active and expected rules present;
- permanent peer appears exactly once;
- newest backup checksum file exists.

The JSON template receives booleans/status strings only. Never serialize stdout from Asterisk, journals, process environments, or rendered secret files.

- [ ] **Step 5: Fail only after writing the report**

Write `/var/lib/allstar-node-factory/reports/latest.json` mode `0640`. Fetch a redacted copy only when `validation_fetch_dir` is explicitly set outside the public repository. After writing, fail the play if any required check is `FAIL`; allow `INIT_REQUIRED` only for AllScan before its manual first-run gate.

- [ ] **Step 6: Test and commit**

```bash
python3 -m pytest tests/unit/test_validation_report.py -q
ansible-lint roles/backup roles/validation
git add roles/backup roles/validation tests/unit/test_validation_report.py
git commit -m "feat: add secure backups and redacted validation"
```

---

### Task 11: Compose the Deployment, Validation, and Backup Playbooks

**Files:**
- Replace: `playbooks/vultr-hub.yml`
- Replace: `playbooks/validate.yml`
- Replace: `playbooks/backup.yml`
- Create: `tests/unit/test_playbook_composition.py`

**Interfaces:**
- Consumes: all role contracts and an explicit inventory path supplied with `-i`.
- Produces: three safe, limitable operator entry points.

- [ ] **Step 1: Write failing composition tests**

Parse each playbook as YAML. Assert `vultr-hub.yml` has roles in this order:

```python
EXPECTED = [
    "backup", "asl3_core", "permanent_link", "echolink",
    "broadcastify", "allmon3", "allscan", "firewall", "validation",
]
```

Assert `validate.yml` contains only `validation`, `backup.yml` contains only `backup`, and every play has `become: true` and `hosts: allstar_nodes`.

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_playbook_composition.py -q
```

Expected: failure because Task 1 playbook stubs do not match.

- [ ] **Step 3: Replace `vultr-hub.yml`**

The playbook gathers facts, uses `serial: 1`, sets `any_errors_fatal: true`, validates `production_services_enabled` explicitly, and imports the roles in the tested order. Add tags `backup`, `core`, `links`, `echolink`, `broadcastify`, `web`, `firewall`, and `validate`.

- [ ] **Step 4: Replace read-only and backup entry points**

`validate.yml` runs only `validation` and never restarts a service. `backup.yml` runs only `backup`. Both use `serial: 1`, `become: true`, and `hosts: allstar_nodes`.

- [ ] **Step 5: Run full offline checks**

```bash
python3 -m pytest tests/unit -q
yamllint .
ansible-lint
ansible-playbook --syntax-check -i inventories/example/hosts.yml playbooks/vultr-hub.yml
ansible-playbook --syntax-check -i inventories/example/hosts.yml playbooks/validate.yml
ansible-playbook --syntax-check -i inventories/example/hosts.yml playbooks/backup.yml
```

Expected: all commands exit `0`.

- [ ] **Step 6: Commit**

```bash
git add playbooks tests/unit/test_playbook_composition.py
git commit -m "feat: compose staged Vultr hub playbooks"
```

---

### Task 12: Add Disposable Debian Integration Tests

**Files:**
- Create: `tests/integration/Dockerfile`
- Create: `tests/integration/inventory.yml`
- Create: `tests/integration/test.yml`
- Create: `tests/integration/test_integration.py`

**Interfaces:**
- Consumes: public fictional inventory and roles that can run without live radio-network credentials.
- Produces: a disposable Debian 13 proof for filesystem permissions, template placement, idempotence, and secret-free reporting.

- [ ] **Step 1: Write a failing pytest wrapper**

The test skips only when Docker is unavailable. It builds `allstar-node-factory-test:debian13`, runs the integration playbook twice, asserts the second recap has `changed=0`, and then uses testinfra to check expected directories and modes. It never enables production services and never contacts AllStarLink, EchoLink, or Broadcastify.

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/integration/test_integration.py -q
```

Expected: failure because the Dockerfile/playbook are absent.

- [ ] **Step 3: Build the disposable target**

Use `debian:13-slim`, install `systemd`, `python3`, `sudo`, `ca-certificates`, and `openssh-server`, create an `ansible` sudo user, and run with the minimum capabilities needed by systemd. The integration playbook uses test-only variables and tags that exercise templates/directories while skipping ASL package download and external service activation via `node_factory_offline_test: true`.

- [ ] **Step 4: Verify idempotence and permissions**

The test must assert:

```python
assert host.file("/etc/asterisk/node-factory").mode == 0o750
assert host.file("/etc/asterisk/node-factory/rpt_http_registrations.conf").mode == 0o640
assert host.file("/var/backups/allstar-node-factory").mode == 0o700
assert "fixture-only-123" not in fetched_report
```

- [ ] **Step 5: Run and commit**

```bash
python3 -m pytest tests/integration/test_integration.py -q
git add tests/integration
git commit -m "test: add Debian 13 role integration coverage"
```

---

### Task 13: Add Documentation, Migration Prompt, and Operations Skill

**Files:**
- Create: `docs/migration/hamvoip-to-asl3.md`
- Create: `docs/operations/vultr-cutover.md`
- Create: `docs/operations/backup-restore.md`
- Create: `docs/profiles/vultr-radioless-hub.md`
- Create: `docs/security/secrets.md`
- Create: `prompts/inventory-legacy-node.md`
- Create: `skills/allstar-node-operations/SKILL.md`
- Create: `tests/unit/test_operations_docs.py`

**Interfaces:**
- Consumes: all implemented commands and variable names.
- Produces: an exact evidence-capture, deployment, cutover, rollback, and incident procedure usable by Jim or JARVIS.

- [ ] **Step 1: Write failing documentation-contract tests**

The test must verify every playbook command contains both the private inventory path and `--limit cloud-hub`, every deployment command includes the production Vault ID, and rollback docs name all three identity-bearing services:

```python
required = (
    "--limit cloud-hub",
    "--vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key",
    "--extra-vars @../allstar-node-inventory/topology/permanent-links.yml",
    "--extra-vars @../allstar-node-inventory/vault/production.yml",
    "playbooks/vultr-hub.yml",
    "playbooks/validate.yml",
    "playbooks/backup.yml",
)
```

It must scan the skill frontmatter for name, description no longer than 60 characters, version, author `Jim Gatwood, Hermes Agent`, license, platforms `[linux]`, tags, and non-empty body.

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_operations_docs.py -q
```

- [ ] **Step 3: Write the migration matrix**

`hamvoip-to-asl3.md` uses a table with columns `Legacy evidence`, `ASL3 destination`, `Secret`, `Activation gate`, and `Verified`. It enumerates node/server identity, ports/codecs, node stanza, DTMF/functions/macros, telemetry/IDs, local/private nodes, direct clients, EchoLink, Broadcastify, web tools, custom sounds, cron/systemd, sockets/firewall, and permanent-link ownership. It explicitly prohibits copying full HAMVOIP files.

- [ ] **Step 4: Write exact operator commands**

All docs use:

```bash
ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/vultr-hub.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml
```

Staging sets `production_services_enabled: false`; cutover changes only that variable to `true` after the old Asterisk, EchoLink, and Broadcastify processes are stopped. Rollback reverses the order: stop the new identity-bearing services, power on the old server, verify registrations/feed/link, and leave the new server available for diagnosis.

- [ ] **Step 5: Write the project-local skill**

Use this frontmatter:

```yaml
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
```

The body contains `When to Use`, `Prerequisites`, `How to Run`, `Procedure`, `Pitfalls`, and `Verification`. Every procedure step ends with a checkable criterion; it never embeds a production identifier or machine-local secret.

- [ ] **Step 6: Test and commit**

```bash
python3 -m pytest tests/unit/test_operations_docs.py -q
git add docs/migration docs/operations docs/profiles docs/security prompts skills tests/unit/test_operations_docs.py
git commit -m "docs: add Vultr migration and operations runbooks"
```

---

### Task 14: Add Secret Scanning and GitHub CI

**Files:**
- Create: `scripts/check_no_secrets.py`
- Create: `tests/unit/test_check_no_secrets.py`
- Create: `.pre-commit-config.yaml`
- Create: `.gitleaks.toml`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: tracked repository files.
- Produces: local and GitHub gates that fail on private keys, Vault passwords, non-example credentials, private inventory paths, or malformed Ansible content.

- [ ] **Step 1: Write failing scanner tests**

Test a temporary clean tree and files containing:

```text
-----BEGIN OPENSSH PRIVATE KEY-----
ANSIBLE_VAULT_PASSWORD=realvalue
ICECAST_PASSWORD=not-a-fixture
192.168.50.5
```

The scanner must reject each and allow `fixture-only-123`, `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, and proper `$ANSIBLE_VAULT;1.2;AES256;production` ciphertext.

- [ ] **Step 2: Run and confirm failure**

```bash
python3 -m pytest tests/unit/test_check_no_secrets.py -q
```

- [ ] **Step 3: Implement the scanner**

Walk tracked-text extensions, skip `.git`, `.venv`, and the approved design/plan source lists, report `path:line:rule` without echoing the matched value, and exit nonzero on any violation. Add an allowlist for documentation ranges and fixture-only literals only.

- [ ] **Step 4: Add CI**

Pin the Gitleaks pre-commit hook to `v8.30.1`. Configure `.gitleaks.toml` to allow proper Ansible Vault ciphertext while continuing to reject plaintext passwords, private keys, tokens, and credentials. Retain the purpose-built Python scanner as a second policy layer for project-specific forbidden topology and inventory patterns.

The workflow triggers on pull requests and branch pushes. It checks out code, sets up Python 3.13, installs `requirements-dev.txt` and `requirements.yml`, then runs:

```bash
python3 scripts/check_no_secrets.py .
pre-commit run --all-files
yamllint .
ansible-lint
python3 -m pytest tests/unit -q
ansible-playbook --syntax-check -i inventories/example/hosts.yml playbooks/vultr-hub.yml
```

Do not add deployment credentials, SSH, live integration tests, or production environments to GitHub Actions.

- [ ] **Step 5: Run the full local gate**

```bash
python3 scripts/check_no_secrets.py .
pre-commit run --all-files
yamllint .
ansible-lint
python3 -m pytest tests/unit -q
python3 -m pytest tests/integration/test_integration.py -q
ansible-playbook --syntax-check -i inventories/example/hosts.yml playbooks/vultr-hub.yml
git diff --check
```

Expected: all available gates pass; integration may report `SKIPPED` only when Docker is unavailable, with the reason printed.

- [ ] **Step 6: Commit**

```bash
git add scripts/check_no_secrets.py tests/unit/test_check_no_secrets.py .pre-commit-config.yaml .gitleaks.toml .github/workflows/ci.yml
git commit -m "ci: enforce Ansible and secret-safety gates"
```

---

### Task 15: Create and Verify the GitHub Repositories

**Files:**
- Modify: local Git remote configuration.
- Create in private repository: `.gitignore`, `README.md`, `inventory/hosts.yml`, `inventory/group_vars/`, `inventory/host_vars/`, `topology/`, `vault/`, `reports/redacted/`, and `docs/`
- Create in private repository: `framework.lock.yml`

**Interfaces:**
- Consumes: verified GitHub authentication and the tested public branch.
- Produces: public `JimGat/allstar-node-factory`, private `JimGat/allstar-node-inventory`, pushed feature branch, and a public pull request.

- [ ] **Step 1: Verify auth and remote state before mutation**

```bash
gh auth status
git status --short
git remote -v
gh repo view JimGat/allstar-node-factory --json nameWithOwner,visibility,url 2>/dev/null || true
gh repo view JimGat/allstar-node-inventory --json nameWithOwner,visibility,url 2>/dev/null || true
```

Expected: authenticated as the intended owner, clean feature branch, and no conflicting repositories/remotes.

- [ ] **Step 2: Create or connect the public repository**

If absent, create it as public with the approved design commit as the initial `main`; then push only the implementation feature branch:

```bash
gh repo create JimGat/allstar-node-factory --public --source=. --remote=origin
git push -u origin main
git push -u origin feat/vultr-hub-foundation
```

If it already exists, fetch/prune, inspect branch history, and connect without overwriting:

```bash
git remote add origin git@github.com:JimGat/allstar-node-factory.git
git fetch --all --prune
git branch -a -vv
git log --oneline --decorate --graph --all -n 30
```

- [ ] **Step 3: Create the private repository scaffold**

Create `/home/jarvis/allstar-node-inventory`, initialize `main`, add a private-repo README and `.gitignore` that excludes plaintext vault files, keys, raw backups, and unredacted reports. Add directories named in the file map. Do not add actual secrets yet. Commit, then:

Create `framework.lock.yml` with exactly these keys:

```yaml
repository: git@github.com:JimGat/allstar-node-factory.git
ref: main
commit: 8959fafbb94ae93fd9acc922b32bdb97eb74ba02
```

Use the full current public `HEAD` returned by `git rev-parse HEAD`; the shown commit is the plan baseline and must be replaced if implementation commits advance the reviewed framework before deployment. The lock is non-secret and is updated only after review.

```bash
gh repo create JimGat/allstar-node-inventory --private --source=. --remote=origin --push
```

- [ ] **Step 4: Open and verify the public PR**

```bash
gh pr create \
  --base main \
  --head feat/vultr-hub-foundation \
  --title "feat: add repeatable Vultr ASL3 hub build" \
  --body "Implements the approved Vultr hub foundation with staged activation, offline tests, backups, validation, and migration runbooks."
gh pr view --json number,url,state,headRefName,baseRefName,statusCheckRollup
```

Expected: an open PR from `feat/vultr-hub-foundation` to `main`; do not merge yet.

- [ ] **Step 5: Verify both external side effects**

```bash
gh repo view JimGat/allstar-node-factory --json nameWithOwner,visibility,url,defaultBranchRef
gh repo view JimGat/allstar-node-inventory --json nameWithOwner,visibility,url,defaultBranchRef
git ls-remote --heads origin
```

Expected: public/private visibility is correct and remote heads match local commits.

---

### Task 16: Populate the Private Inventory and Vault from Real Evidence

**Files:**
- Create in private repository: `inventory/hosts.yml`
- Create in private repository: `inventory/host_vars/cloud-hub.yml`
- Create in private repository: `inventory/host_vars/dvswitch-node.yml`
- Create in private repository: `topology/permanent-links.yml`
- Create in private repository: `vault/production.yml`
- Create in private repository: `docs/estate.md`
- Create in private repository: `docs/recovery-order.md`

**Interfaces:**
- Consumes: authorized read-only SSH access to the old HAMVOIP node, the new Debian 13 host address, portal values, feed values, and the external Vault password file.
- Produces: a validated, encrypted desired-state inventory with no raw legacy backup in Git.

- [ ] **Step 1: Create and protect the external Vault password**

```bash
install -d -m 700 /home/jarvis/.config/allstar-node-factory
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > /home/jarvis/.config/allstar-node-factory/vault-production.key
chmod 600 /home/jarvis/.config/allstar-node-factory/vault-production.key
stat -c '%a %n' /home/jarvis/.config/allstar-node-factory/vault-production.key
```

Expected: mode `600`. Jim stores a recovery copy in his password manager before proceeding.

- [ ] **Step 2: Capture legacy evidence read-only**

Follow `prompts/inventory-legacy-node.md`. Save raw command output and configuration archives outside both repositories in a mode-`0700` working directory. Populate the migration matrix with values for node identity, IAX port, functions/macros, EchoLink, Broadcastify, web tools, permanent-link behavior, custom files, services, firewall, and listening sockets. Redact reports before any commit.

Completion criterion: every matrix row says `captured`, `not used`, or `not present`; none are blank.

- [ ] **Step 3: Determine permanent-link ownership empirically**

Inspect startup macros and active links on both ends. Reboot neither node yet. Set exactly one of:

```yaml
permanent_link_initiator: external
```

or:

```yaml
permanent_link_initiator: local
```

Record why in `topology/permanent-links.yml`. Completion criterion: there is one declared initiator and no second startup macro planned.

- [ ] **Step 4: Populate non-secret desired state**

Write real node numbers, callsign, ports, SSH alias, feature flags, metadata, and topology to `inventory/group_vars/`, `inventory/host_vars/`, and `topology/`. Keep `production_services_enabled: false` for staging. Run the public validator against the assembled variable set and correct every error.

- [ ] **Step 5: Create the encrypted vault interactively**

Run:

```bash
ansible-vault create \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  vault/production.yml
```

The decrypted YAML contains exactly the keys `vault_asl_node_password`,
`vault_echolink_password`, `vault_broadcastify_password`, `vault_ami_secret`,
`vault_allmon3_password`, and `vault_allscan_password`. Assign authorized
existing credentials to the first three and newly generated high-entropy
values to `vault_ami_secret` and `vault_allmon3_password`. Generate
`vault_allscan_password` as an independent random value exactly 16 characters
long because upstream AllScan accepts only 6-16 characters.[14] Values
are entered only in the editor opened by `ansible-vault create`, never in chat
or a shell argument. Verify ciphertext without displaying plaintext:

```bash
head -n 1 vault/production.yml
ansible-vault view --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key vault/production.yml >/dev/null
```

Expected: first line starts `$ANSIBLE_VAULT;1.2;AES256;production`; view exits `0`.

- [ ] **Step 6: Scan and commit the private repository**

Run the public secret scanner with private-mode rules that allow Vault ciphertext but reject plaintext keys and private keys. Review `git diff --cached` manually. Commit only desired state and encrypted ciphertext:

```bash
git add inventory topology vault/production.yml framework.lock.yml reports/redacted/.gitkeep docs .gitignore README.md
git commit -m "chore: add encrypted production node inventory"
git push origin main
```

Read back the private GitHub repository file list and visibility before claiming success.

---

### Task 17: Stage the New Vultr Hub Without Activating Identities

**Files:**
- Modify in private repository: `inventory/host_vars/cloud-hub.yml`
- Create outside Git: preflight and staging execution logs with secrets redacted.

**Interfaces:**
- Consumes: a clean operator-created Debian 13 Vultr server, private inventory, encrypted vault, and the reviewed public framework commit.
- Produces: fully configured green server with production identities disabled and a successful staged validation report.

- [ ] **Step 1: Complete provider-side prerequisites**

In Vultr, create the parallel Debian 13 x64 instance with 2 vCPUs, 2 GB RAM, 25-40 GB SSD, SSH key, automated backups, and the provider firewall matching the documented ports. Restrict SSH to authorized management sources. Do not alter the old server.

Completion criterion: SSH works with the intended non-root sudo user, automated backups show enabled, and the old server remains unchanged.

- [ ] **Step 2: Pin the reviewed public commit in private metadata**

Write the exact public commit SHA, repository URL, and reviewed branch or release tag to `framework.lock.yml`, and record the same SHA in `docs/estate.md`. Check out that SHA, require a clean tree, and run:

```bash
python3 scripts/check_framework_pin.py \
  --framework /home/jarvis/allstar-node-factory \
  --lock /home/jarvis/allstar-node-inventory/framework.lock.yml
```

Completion criterion: the checker exits `0` and `git rev-parse HEAD` equals the locked full SHA.

- [ ] **Step 3: Run check mode and inspect the diff**

```bash
ansible-playbook \
  -i ../allstar-node-inventory/inventory/hosts.yml \
  playbooks/vultr-hub.yml \
  --limit cloud-hub \
  --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key \
  --extra-vars @../allstar-node-inventory/topology/permanent-links.yml \
  --extra-vars @../allstar-node-inventory/vault/production.yml \
  --check --diff
```

Expected: no host/OS/preflight failures, no unexpected deletion, and no secret appears in output. Any task that cannot safely support check mode must report skipped with an explicit reason.

- [ ] **Step 4: Apply staged configuration**

Run the same command without `--check --diff` while `production_services_enabled: false`.

Completion criterion: ASL3, web apps, configs, firewall, and backups are present; Asterisk HTTP registration, EchoLink module, and Broadcastify unit remain inactive.

- [ ] **Step 5: Initialize AllScan over the protected management path**

Open the local/protected AllScan URL, create the first admin account using `vault_allscan_password`, and set **Public Permission** to **None**. Do not expose the site publicly merely to complete initialization.

Completion criterion: `/etc/allscan/allscan.db` exists, admin login works, and validation changes AllScan from `INIT_REQUIRED` to `PASS`.

- [ ] **Step 6: Run staged validation and backup**

```bash
ansible-playbook -i ../allstar-node-inventory/inventory/hosts.yml playbooks/validate.yml --limit cloud-hub --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key --extra-vars @../allstar-node-inventory/topology/permanent-links.yml --extra-vars @../allstar-node-inventory/vault/production.yml
ansible-playbook -i ../allstar-node-inventory/inventory/hosts.yml playbooks/backup.yml --limit cloud-hub --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key --extra-vars @../allstar-node-inventory/topology/permanent-links.yml --extra-vars @../allstar-node-inventory/vault/production.yml
```

Expected: all non-production checks `PASS`, identity checks `NOT_APPLICABLE`, AllScan `PASS`, and backup checksum verification succeeds.

---

### Task 18: Execute Controlled Cutover, Reboot Matrix, and Rollback Proof

**Files:**
- Modify in private repository: `inventory/host_vars/cloud-hub.yml`
- Create in private repository: `reports/redacted/cutover-YYYY-MM-DD.md`
- Modify in private repository: `docs/estate.md`

**Interfaces:**
- Consumes: successful Task 17 staging, approved maintenance window, portal access, old/new server controls, and access to the separate DVSwitch node.
- Produces: accepted production ASL3 hub or a completed rollback with the old hub restored.

- [ ] **Step 1: Take final rollback artifacts**

Take a fresh old-server Vultr snapshot, capture an off-repository raw configuration archive, and record checksum/location in private docs. Run a final new-server backup. Completion criterion: both artifact checksums and snapshot IDs are recorded privately.

- [ ] **Step 2: Stop duplicate identities on the old server**

During the approved window, stop old Asterisk/EchoLink and Broadcastify feed processes, then verify the old host no longer has active node registration, EchoLink login, or feed connection. Do not delete the server; leave it ready to power off.

- [ ] **Step 3: Activate only the new server**

Set `production_services_enabled: true` in private inventory and run:

```bash
ansible-playbook -i ../allstar-node-inventory/inventory/hosts.yml playbooks/vultr-hub.yml --limit cloud-hub --vault-id production@/home/jarvis/.config/allstar-node-factory/vault-production.key --extra-vars @../allstar-node-inventory/topology/permanent-links.yml --extra-vars @../allstar-node-inventory/vault/production.yml
```

Completion criterion: HTTP registration appears once, EchoLink logs in once, Broadcastify service is active, and no old identity is active.

- [ ] **Step 4: Run functional acceptance**

Verify inbound/outbound AllStarLink calls, two-way audio, DTMF, EchoLink inbound/outbound calls and announcements, Broadcastify presence/quality/metadata/delay, Allmon3 controls, AllScan controls, and exactly one DVSwitch link. Record pass/fail without secrets.

- [ ] **Step 5: Run the reboot matrix**

In order:

1. cold reboot the new cloud hub and verify all services plus the link;
2. restart only Asterisk and verify recovery;
3. interrupt/recover network connectivity and verify permanent-link retry;
4. reboot only the DVSwitch node and verify its startup-macro behavior;
5. verify two-way audio and DTMF again;
6. run a post-reboot backup and checksum verification.

If the current DVSwitch node cannot be safely rebooted in the maintenance window, acceptance remains explicitly incomplete; do not mark the migration finished.

- [ ] **Step 6: Exercise the documented rollback decision path**

Before deleting nothing, perform a tabletop/read-only rollback proof: confirm the commands, snapshot, backup, portal values, and old-server start procedure are all available. If any production acceptance check fails materially, execute rollback: stop new Asterisk/EchoLink/Broadcastify, restore/start the old server, then verify registration, EchoLink, Broadcastify, and DVSwitch link.

- [ ] **Step 7: Close acceptance without deleting the old node**

When every check passes, power off the old server and retain it plus its snapshot for the agreed rollback period. Copy the native and supplemental backup archives plus checksum files to the approved off-host backup location outside both repositories, run `sha256sum -c` there, and record only the destination class, archive timestamp, size, and checksum in private estate metadata. Capture a post-configuration snapshot of the new server. Write the redacted report and update estate metadata.

- [ ] **Step 8: Final framework verification and release decision**

Run all local tests, review the public PR, verify GitHub CI, and present results to Jim. Merge the PR and tag `v0.1.0` only after Jim explicitly authorizes the release. Verify the tag, release URL, default branch, and both repository visibilities after mutation.

---

## Plan Self-Review Results

- **Spec coverage:** The plan covers the public/private split, local Ansible execution, Vault, ASL3 package installation, radioless node config, EchoLink, Broadcastify, Allmon3, AllScan, host firewall, permanent link, backup, validation, documentation, CI, blue/green cutover, reboot matrix, rollback, and post-acceptance snapshot.
- **Decomposed future scope:** Raspberry Pi/SHARI, repeater links/controllers, serial radio control, custom voice IDs, SkywarnPlus/NWS, and custom image building remain separate future specs and plans.
- **Activation safety:** `production_services_enabled` is mandatory and false during staging; the old and new identities cannot be active by default.
- **AllScan uncertainty contained:** The role pins reviewed code and avoids undocumented database writes or unattended execution of the interactive installer.
- **No provider automation:** Vultr instance, firewall, backup, and snapshot operations remain explicit operator steps.
- **No implementation placeholders:** Real production values are entered only during the private-inventory task and are never represented in the public repository or this plan.

## Sources

[1] https://allstarlink.github.io/install/debian/install — ASL3 Debian Installation
[2] https://allstarlink.github.io/adv-topics/httpreg — ASL3 HTTP-Based Registration
[3] https://allstarlink.github.io/adv-topics/echolink — ASL3 EchoLink Configuration
[4] https://allstarlink.github.io/adv-topics/broadcastify — ASL3 Broadcastify Streaming
[5] https://allstarlink.github.io/allmon3/install — Allmon3 Installation
[6] https://allstarlink.github.io/allmon3/config — Allmon3 Configuration
[7] https://allstarlink.github.io/adv-topics/permanentnode — ASL3 Permanent Node Connection
[8] https://raw.githubusercontent.com/davidgsd/AllScan/main/README.md — AllScan README
[9] https://raw.githubusercontent.com/davidgsd/AllScan/main/AllScanInstallUpdate.php — AllScan Installer/Updater
[10] https://allstarlink.github.io/adv-topics/conftmpl — ASL3 Configuration Templates
[11] https://allstarlink.github.io/user-guide/troubleshooting — ASL3 Troubleshooting and Third-Party Support Policy
[12] https://allstarlink.github.io/allmon3/usermgmt — Allmon3 User Management
[13] https://repo.allstarlink.org/public/dists/trixie/main/binary-amd64/Packages — ASL3 Debian 13 Package Index
[14] https://raw.githubusercontent.com/davidgsd/AllScan/main/include/UserModel.php — AllScan Authentication Model
[15] https://api.github.com/repos/davidgsd/AllScan/commits/main — AllScan Main Commit Metadata
[16] https://repo.allstarlink.org/public/asl-apt-repos.deb13_all.deb — ASL3 Debian 13 Repository Bootstrap Package
[17] https://github.com/davidgsd/AllScan/archive/0309f2ff8fc5d2baf1c1df1afc13acb59781cd97.tar.gz — Pinned AllScan Source Archive
[18] https://allstarlink.github.io/mans/asl-backup-menu — ASL3 Backup Utility
