from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def test_setup_python_cache_uses_the_actual_dependency_file() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["offline-quality-gates"]["steps"]
    setup = next(step for step in steps if step.get("uses") == "actions/setup-python@v5")

    assert setup["with"]["cache"] == "pip"
    assert setup["with"]["cache-dependency-path"] == "requirements-dev.txt"
