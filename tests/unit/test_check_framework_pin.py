from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_framework_pin", ROOT / "scripts" / "check_framework_pin.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

COMMIT = "0123456789abcdef0123456789abcdef01234567"
LOCK = {
    "repository": "https://example.invalid/fictional/framework.git",
    "ref": "refs/tags/fictional-v1",
    "commit": COMMIT,
}


def test_clean_checkout_at_exact_commit_passes(capsys) -> None:
    assert MODULE.validate_pin(LOCK, COMMIT, False) == []
    assert capsys.readouterr().out == ""


def test_dirty_checkout_fails_without_printing_repository(capsys) -> None:
    assert MODULE.validate_pin(LOCK, COMMIT, True)
    captured = capsys.readouterr()
    assert LOCK["repository"] not in captured.out
    assert LOCK["repository"] not in captured.err


def test_short_commit_fails_without_printing_repository(capsys) -> None:
    lock = {**LOCK, "commit": COMMIT[:12]}
    assert MODULE.validate_pin(lock, COMMIT, False)
    captured = capsys.readouterr()
    assert LOCK["repository"] not in captured.out
    assert LOCK["repository"] not in captured.err


def test_mismatched_head_fails_without_printing_repository(capsys) -> None:
    head = "fedcba9876543210fedcba9876543210fedcba98"
    assert MODULE.validate_pin(LOCK, head, False)
    captured = capsys.readouterr()
    assert LOCK["repository"] not in captured.out
    assert LOCK["repository"] not in captured.err
