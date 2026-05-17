# Intentionally insecure sample module — used by `make demo`.
# DO NOT use in production. The whole point is for TerraDrift to flag it.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = "us-east-1"
  # ❌ Hardcoded credentials — never do this in real life.
  access_key = "AKIAIOSFODNN7EXAMPLE"
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}

# ❌ Public-read S3 bucket — like leaving your front door wide open.
resource "aws_s3_bucket" "public" {
  bucket = "terradrift-demo-public"
  acl    = "public-read"
}

# ❌ Security group with 0.0.0.0/0 on SSH — like leaving the back door
# unlocked too. Real example: this is how most cryptojacking starts.
resource "aws_security_group" "open_ssh" {
  name = "open-ssh"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
