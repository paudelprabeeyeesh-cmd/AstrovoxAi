variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "inference_cluster_name" {
  description = "EKS cluster name for inference"
  type        = string
  default     = "astrovox-inference"
}

variable "gpu_instance_type" {
  description = "EC2 instance type for GPU inference nodes"
  type        = string
  default     = "p4d.24xlarge"
}

variable "min_capacity" {
  description = "Minimum number of inference nodes"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of inference nodes"
  type        = number
  default     = 8
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}
