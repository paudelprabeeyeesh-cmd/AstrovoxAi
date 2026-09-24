terraform {
  source = "../../modules/eks"
}

include "root" {
  path = find_in_parent_folders()
}

dependency "vpc" {
  config_path = "../vpc"
}

inputs = {
  aws_region              = "us-east-1"
  cluster_name            = "astrovox-prod"
  kubernetes_version      = "1.28"
  vpc_id                  = dependency.vpc.outputs.vpc_id
  private_subnet_ids      = dependency.vpc.outputs.private_subnet_ids
  public_subnet_ids       = dependency.vpc.outputs.public_subnet_ids
  node_instance_types     = ["m5.large", "m5.xlarge"]
  node_min_count          = 3
  node_max_count          = 20
  node_desired_count      = 5
  enable_cluster_autoscaler = true
  enable_external_dns     = true
  enable_aws_load_balancer_controller = true
  enable_cert_manager     = true
  enable_external_secrets = true
  enable_argocd           = true
  enable_argo_rollouts    = true
}
