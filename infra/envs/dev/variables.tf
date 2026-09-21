variable "aws_region" {
  description = "AWS region for the dev environment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for tagging resources."
  type        = string
  default     = "university-chatbot"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}