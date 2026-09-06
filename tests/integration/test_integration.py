import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

import pytest
import testinfra

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "allstar-node-factory-test:debian13"


def run(*args: str, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={**os.environ, "ANSIBLE_NOCOLOR": "1"},
    )


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = run("docker", "info", check=False, timeout=30)
    return result.returncode == 0


def test_debian13_offline_roles_are_idempotent_and_redacted() -> None:
    if not docker_available():
        pytest.skip("Docker daemon is unavailable")

    run(
        "docker",
        "build",
        "--file",
        "tests/integration/Dockerfile",
        "--tag",
        IMAGE,
        ".",
        timeout=600,
    )
    container = f"allstar-node-factory-{uuid.uuid4().hex[:10]}"
    run(
        "docker",
        "run",
        "--detach",
        "--privileged",
        "--name",
        container,
        "--tmpfs",
        "/run",
        "--tmpfs",
        "/run/lock",
        IMAGE,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            ready = run(
                "docker",
                "exec",
                container,
                "systemctl",
                "is-system-running",
                check=False,
                timeout=10,
            )
            if ready.stdout.strip() in {"running", "degraded"}:
                break
            time.sleep(0.5)
        else:
            pytest.fail("Disposable Debian 13 systemd target did not become ready")

        command = (
            "docker",
            "exec",
            container,
            "/opt/node-factory-venv/bin/ansible-playbook",
            "-i",
            "tests/integration/inventory.yml",
            "tests/integration/test.yml",
        )
        first = run(*command, timeout=300)
        second = run(*command, timeout=300)
        assert first.returncode == 0, first.stdout + first.stderr
        assert second.returncode == 0, second.stdout + second.stderr
        assert re.search(r"changed=0\s+unreachable=0\s+failed=0", second.stdout)

        host = testinfra.get_host(f"docker://{container}")
        assert host.file("/etc/asterisk/node-factory").mode == 0o750
        registration = host.file("/etc/asterisk/rpt_http_registrations.conf")
        assert registration.mode == 0o640
        assert host.file("/var/backups/allstar-node-factory").mode == 0o700
        report_file = host.file(
            "/var/lib/allstar-node-factory/reports/latest.json"
        )
        report_text = report_file.content_string
        report = json.loads(report_text)
        assert report["node"] == "1998"
        assert report["overall"] == "PASS"
        assert "fixture-only-123" not in report_text
    finally:
        run("docker", "rm", "--force", container, check=False, timeout=60)
