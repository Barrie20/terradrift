from pathlib import Path

from terradrift.analyzer import _offline_fallback_scan


def test_offline_flags_public_acl(tmp_path: Path) -> None:
    tf = tmp_path / "main.tf"
    tf.write_text('resource "aws_s3_bucket" "x" { bucket = "y"\n  acl = "public-read"\n}\n')
    findings = _offline_fallback_scan(tmp_path, "deadbeef")
    rules = {f.rule_id for f in findings}
    assert "CKV_AWS_20" in rules


def test_offline_flags_open_ssh(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'resource "aws_security_group" "web" {\n  ingress { cidr_blocks = ["0.0.0.0/0"] }\n}\n'
    )
    findings = _offline_fallback_scan(tmp_path, "x")
    assert any(f.rule_id == "CKV_AWS_24" for f in findings)


def test_offline_flags_hardcoded_key(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('access_key = "AKIAIOSFODNN7EXAMPLE"\n')
    findings = _offline_fallback_scan(tmp_path, "x")
    assert any(f.rule_id == "CKV_AWS_41" for f in findings)


def test_offline_does_not_flag_secure_s3_settings(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'resource "aws_s3_bucket" "secure" {\n'
        '  logging { target_bucket = "logs" }\n'
        "  server_side_encryption_configuration {}\n"
        "  versioning { enabled = true }\n"
        '  kms_key_id = "example-key"\n'
        "}\n"
    )

    findings = _offline_fallback_scan(tmp_path, "x")

    secure_rule_ids = {"CKV_AWS_18", "CKV_AWS_19", "CKV_AWS_21", "CKV_AWS_145"}
    assert secure_rule_ids.isdisjoint(f.rule_id for f in findings)
