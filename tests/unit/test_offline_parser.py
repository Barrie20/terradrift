from pathlib import Path

from terradrift.offline import parse_hcl_blocks, scan_directory


def test_parser_keeps_nested_blocks_and_ignores_comment_braces() -> None:
    text = """
resource "aws_instance" "web" {
  # A comment with a closing brace }
  metadata_options {
    http_tokens = "optional"
  }
}
resource "aws_db_instance" "database" {
  storage_encrypted = false
}
"""

    blocks = parse_hcl_blocks(text)

    assert [block.resource_address for block in blocks] == [
        "aws_instance.web",
        "aws_db_instance.database",
    ]
    assert "metadata_options" in blocks[0].text


def test_findings_use_stable_resource_addresses(tmp_path: Path) -> None:
    terraform = tmp_path / "main.tf"
    terraform.write_text(
        'resource "aws_s3_bucket" "public" {\n  acl = "public-read"\n}\n',
        encoding="utf-8",
    )

    first = scan_directory(tmp_path, "one")
    terraform.write_text(
        '\n\nresource "aws_s3_bucket" "public" {\n  acl = "public-read"\n}\n',
        encoding="utf-8",
    )
    second = scan_directory(tmp_path, "two")

    first_public = next(finding for finding in first if finding.rule_id == "CKV_AWS_20")
    second_public = next(finding for finding in second if finding.rule_id == "CKV_AWS_20")
    assert first_public.resource_address == second_public.resource_address == "aws_s3_bucket.public"
    assert first_public.line_start != second_public.line_start


def test_s3_missing_controls_are_reported_per_resource(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'resource "aws_s3_bucket" "plain" {\n  bucket = "plain"\n}\n',
        encoding="utf-8",
    )

    findings = scan_directory(tmp_path, "one")
    rules = {finding.rule_id for finding in findings}

    assert {"CKV_AWS_18", "CKV_AWS_19", "CKV_AWS_21"} <= rules
    assert {finding.resource_address for finding in findings} == {"aws_s3_bucket.plain"}


def test_separate_s3_control_resources_prevent_missing_findings(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        """
resource "aws_s3_bucket" "secure" {
  bucket = "secure"
  tags = { Name = "secure" }
}
resource "aws_s3_bucket_logging" "secure" {
  bucket = aws_s3_bucket.secure.id
  target_bucket = aws_s3_bucket.secure.id
}
resource "aws_s3_bucket_versioning" "secure" {
  bucket = aws_s3_bucket.secure.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "secure" {
  bucket = aws_s3_bucket.secure.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}
""",
        encoding="utf-8",
    )

    findings = scan_directory(tmp_path, "one")
    secure_rules = {"CKV_AWS_18", "CKV_AWS_19", "CKV_AWS_21"}

    assert secure_rules.isdisjoint(
        finding.rule_id
        for finding in findings
        if finding.resource_address == "aws_s3_bucket.secure"
    )
