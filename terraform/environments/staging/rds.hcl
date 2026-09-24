terraform {
  source = "../../modules/rds"
}

include "root" {
  path = find_in_parent_folders()
}

dependency "vpc" {
  config_path = "../vpc"
}

dependency "eks" {
  config_path = "../eks"
}

inputs = {
  aws_region              = "us-east-1"
  project_name            = "astrovox"
  environment             = "staging"
  vpc_id                  = dependency.vpc.outputs.vpc_id
  private_subnet_ids      = dependency.vpc.outputs.private_subnet_ids
  eks_node_sg_id          = dependency.eks.outputs.node_security_group_id
  db_instance_class       = "db.t3.large"
  db_allocated_storage    = 50
  db_max_allocated_storage = 100
  db_engine_version       = "16.1"
  db_name                 = "astrovox"
  db_username             = "astrovox"
  multi_az                = false
  backup_retention_period = 3
  deletion_protection     = false
  skip_final_snapshot     = true
}
