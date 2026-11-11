from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "roles" / "asl_web_ui"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_asl_web_ui_defaults_are_securely_disabled() -> None:
    defaults = yaml.safe_load(text(ROLE / "defaults" / "main.yml"))

    assert defaults["asl_web_ui_enabled"] is False
    assert defaults["asl_web_ui_users"] == []
    assert defaults["asl_web_ui_allow_insecure_http"] is False


def test_asl_web_ui_installs_package_and_manages_declared_users() -> None:
    rendered = text(ROLE / "tasks" / "main.yml")

    assert "asl-web-ui" in rendered
    assert "asl_web_ui_users" in rendered
    assert "getent" in rendered
    assert "groups: asl-web-ui" in rendered
    assert "append: true" in rendered
    assert "gpasswd" in rendered
    assert "asl_web_ui_stale_users" in rendered
    assert "a2enconf" in rendered


def test_asl_web_ui_requires_https_and_factory_owned_vhost() -> None:
    rendered = text(ROLE / "tasks" / "main.yml")
    settings = text(ROLE / "templates" / "99-node-factory.ini.j2")

    assert "web_tls_enabled" in rendered
    assert "web_public_enabled" in rendered
    assert "allow_insecure_http = no" in settings
    assert "apache_vhosts = external" in settings


def test_asl_web_ui_is_management_source_restricted() -> None:
    security = text(ROLE / "templates" / "asl-web-ui-node-factory-security.conf.j2")
    vhost = text(ROOT / "roles" / "allmon3" / "templates" / "allmon3-public.conf.j2")

    assert '^/asl-web-ui(?:/|$)' in security
    assert "Require local" in security
    assert "Require ip {{ cidr }}" in security
    assert '^/asl-web-ui(?:/|$)' in vhost
    assert "Require ip {{ cidr }}" in vhost


def test_asl_web_ui_suppresses_package_service_starts_in_staging() -> None:
    rendered = text(ROLE / "tasks" / "main.yml")

    assert "policy_rc_d: 101" in rendered
    assert rendered.count("Keep Asterisk stopped and disabled") >= 2
    assert rendered.index("Keep Asterisk stopped and disabled before") < rendered.index(
        "Install ASL Web UI without starting services"
    )
    assert rendered.index("Install ASL Web UI without starting services") < rendered.index(
        "Keep Asterisk stopped and disabled after"
    )


def test_apache_is_validated_before_reload() -> None:
    rendered = text(ROLE / "tasks" / "main.yml")

    assert rendered.index("Validate Apache after enabling ASL Web UI") < rendered.index(
        "Apply pending ASL Web UI changes"
    )


def test_asl_web_ui_staging_checks_asterisk_remains_inactive() -> None:
    rendered = text(ROLE / "tasks" / "main.yml")

    assert "production_services_enabled" in rendered
    assert "systemctl" in rendered
    assert "is-active" in rendered
    assert "Asterisk must remain inactive" in rendered