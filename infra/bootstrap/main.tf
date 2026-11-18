terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "regiao" {
  type    = string
  default = "us-east-1"
}

provider "aws" {
  region = var.regiao
  default_tags {
    tags = {
      Projeto       = "agente-suporte"
      GerenciadoPor = "terraform"
    }
  }
}

data "aws_caller_identity" "atual" {}

resource "aws_s3_bucket" "estado" {
  bucket = "novabyte-tfstate-${data.aws_caller_identity.atual.account_id}"
}

resource "aws_s3_bucket_versioning" "estado" {
  bucket = aws_s3_bucket.estado.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "estado" {
  bucket = aws_s3_bucket.estado.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "estado" {
  bucket                  = aws_s3_bucket.estado.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_estado" {
  value = aws_s3_bucket.estado.bucket
}
