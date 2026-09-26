# AstrovoxAI Cloud Infrastructure Deployment
# This file references all infrastructure modules

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Project     = "astrovoxai"
      Owner       = "astrovox-devops"
    }
  }
}

# Call modules
module "vpc" {
  source = "./terraform/modules/vpc"
}

module "rds" {
  source = "./terraform/modules/rds"
}

module "elasticache" {
  source = "./terraform/modules/elasticache"
}

module "s3" {
  source = "./terraform/modules/s3"
}

module "cloudfront" {
  source = "./terraform/modules/cloudfront"
}

module "alb" {
  source = "./terraform/modules/alb"
}

module "eks" {
  source = "./terraform/modules/eks"
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "database_endpoint" {
  value = module.rds.endpoint
}

output "redis_endpoint" {
  value = module.elasticache.endpoint
}

output "s3_bucket" {
  value = module.s3.bucket_name
}

output "cloudfront_domain" {
  value = module.cloudfront.domain_name
}

output "alb_dns_name" {
  value = module.alb.dns_name
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}
