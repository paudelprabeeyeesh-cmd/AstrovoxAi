terraform {
  source = "../../modules/elasticache"
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
  aws_region           = "us-east-1"
  project_name         = "astrovox"
  environment          = "production"
  vpc_id               = dependency.vpc.outputs.vpc_id
  private_subnet_ids   = dependency.vpc.outputs.private_subnet_ids
  eks_node_sg_id       = dependency.eks.outputs.node_security_group_id
  redis_node_type      = "cache.r6g.large"
  redis_num_cache_nodes = 3
  redis_engine_version = "7.1"
  multi_az             = true
  automatic_failover   = true
}
