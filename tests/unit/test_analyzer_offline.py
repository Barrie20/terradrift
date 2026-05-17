from pathlib import Path

from terradrift.analyzer import _offline_fallback_scan


def test_offline_flags_public_acl(tmp_path: Path) -> None:
    tf = tmp_path / "main.tf"
    tf.write_text(
        'resource "aws_s3_bucket" "x" { bucket = "y"\n  acl = "public-read"\n}\n'
    )
    findings = _offline_fallback_scan(tmp_path, "deadbeef")
    rules = {f.rule_id for f in findings}
    assert "CKV_AWS_20" in rules


def test_offline_flags_open_ssh(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'ingress { cidr_blocks = ["0.0.0.0/0"] }\n'
    )
    findings = _offline_fallback_scan(tmp_path, "x")
    assert any(f.rule_id == "CKV_AWS_24" for f in findings)


def test_offline_flags_hardcoded_key(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('access_key = "AKIAIOSFODNN7EXAMPLE"\n')
    findings = _offline_fallback_scan(tmp_path, "x")
    assert any(f.rule_id == "CKV_AWS_41" for f in findings)
