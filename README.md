# AllStar Node Factory

Repeatable, security-conscious build and recovery automation for AllStarLink nodes.

The approved architecture and implementation plan are documented in:

- `docs/superpowers/specs/2026-09-03-allstar-node-factory-design.md`
- `docs/superpowers/plans/2026-09-03-vultr-hub-foundation.md`

No production inventory or credentials belong in this public repository.

## Development setup

Python 3.13 is the reviewed controller runtime.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
ansible-galaxy collection install -r requirements.yml
```

Run the baseline checks with:

```bash
python -m pytest tests/unit -q
yamllint .
```
