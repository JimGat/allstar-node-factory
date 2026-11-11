from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "roles" / "asl3_core"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_factory_requires_key_only_ssh_before_local_pam_passwords() -> None:
    config = text(CORE / "templates" / "00-node-factory-ssh.conf.j2")

    assert "AuthenticationMethods publickey" in config
    assert "PubkeyAuthentication yes" in config
    assert "PasswordAuthentication no" in config
    assert "KbdInteractiveAuthentication no" in config
    assert "PermitRootLogin prohibit-password" in config
    assert "UsePAM yes" in config


def test_ssh_hardening_is_validated_and_reloaded() -> None:
    tasks = text(CORE / "tasks" / "main.yml")
    handlers = text(CORE / "handlers" / "main.yml")

    assert "/etc/ssh/sshd_config.d/00-node-factory.conf" in tasks
    assert "sshd -t" in tasks
    assert "sshd -T" in tasks
    assert "sshd -T -C" in tasks
    assert "asl_web_ui_users" in tasks
    assert "management_cidrs" in tasks
    assert "passwordauthentication no" in tasks
    assert "authenticationmethods publickey" in tasks
    assert "IPv4 /32 or IPv6 /128 host routes" in tasks
    assert "Reload ssh" in handlers
