from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_PATH = ROOT / "roles/allscan/defaults/main.yml"
TASKS_PATH = ROOT / "roles/allscan/tasks/main.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_allscan_role_uses_pinned_safe_deployment() -> None:
    defaults = load_yaml(DEFAULTS_PATH)
    serialized_tasks = TASKS_PATH.read_text(encoding="utf-8")

    assert defaults["allscan_commit"] == "0309f2ff8fc5d2baf1c1df1afc13acb59781cd97"
    assert "AllScanInstallUpdate.php" not in serialized_tasks
    assert "https://github.com/davidgsd/AllScan/archive/" in serialized_tasks
    assert "/etc/allscan" in serialized_tasks
    assert "/var/www/html/allscan" in serialized_tasks
