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
  environment             = "production"
  vpc_id                  = dependency.vpc.outputs.vpc_id
  private_subnet_ids      = dependency.vpc.outputs.private_subnet_ids
  eks_node_sg_id          = dependency.eks.outputs.node_security_group_id
  db_instance_class       = "db.r6g.large"
  db_allocated_storage    = 200
  db_max_allocated_storage = 1000
  db_engine_version       = "16.1"
  db_name                 = "astrovox"
  db_username             = "astrovox"
  multi_az                = true
  backup_retention_period = 14
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "astrovox-prod-final-snapshot"
}
