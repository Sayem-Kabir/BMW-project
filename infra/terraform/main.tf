# Spec Section 19.5 — Terraform scaffold for local Kind + optional cloud URLs
terraform {
  required_version = ">= 1.5"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

variable "environment" {
  type    = string
  default = "local"
}

variable "public_api_url" {
  type    = string
  default = "http://127.0.0.1:8000"
}

variable "frontend_url" {
  type    = string
  default = "http://127.0.0.1:3000"
}

resource "null_resource" "helm_notes" {
  triggers = {
    env = var.environment
  }
  provisioner "local-exec" {
    command = "echo Deploy with: helm upgrade --install bmw-ai infra/helm/bmw-ai -n bmw --create-namespace"
  }
}

output "public_api_url" {
  value = var.public_api_url
}

output "frontend_url" {
  value = var.frontend_url
}

output "helm_chart" {
  value = "infra/helm/bmw-ai"
}
