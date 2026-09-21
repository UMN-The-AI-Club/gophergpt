module "networking" {
  source = "../../modules/networking"

  project_name = var.project_name
  environment  = var.environment
}

module "iam" {
  source = "../../modules/iam"

  project_name = var.project_name
  environment  = var.environment
}

module "database" {
  source = "../../modules/database"

  project_name = var.project_name
  environment  = var.environment
}

module "backend" {
  source = "../../modules/backend"

  project_name = var.project_name
  environment  = var.environment
}

module "frontend" {
  source = "../../modules/frontend"

  project_name = var.project_name
  environment  = var.environment
}