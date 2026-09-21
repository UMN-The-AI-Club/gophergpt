output "project_name" {
  description = "Project name for the dev environment."
  value       = var.project_name
}

output "environment" {
  description = "Current Terraform environment."
  value       = var.environment
}

output "aws_region" {
  description = "AWS region for the dev environment."
  value       = var.aws_region
}