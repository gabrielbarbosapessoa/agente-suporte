terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "s3" {
    bucket       = "novabyte-tfstate-438298963869"
    key          = "agente-suporte/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
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
