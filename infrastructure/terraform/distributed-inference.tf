terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

variable "cluster_name" {
  default = "astrovox-distributed"
}

variable "node_instance_type" {
  default = "p4d.24xlarge"
}

variable "min_nodes" {
  default = 2
}

variable "max_nodes" {
  default = 10
}

variable "desired_nodes" {
  default = 3
}

resource "aws_eks_cluster" "distributed" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.29"

  vpc_config {
    subnet_ids = [aws_subnet.private.id, aws_subnet.private_2.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
  ]
}

resource "aws_eks_node_group" "distributed_gpu" {
  cluster_name    = aws_eks_cluster.distributed.name
  node_group_name = "distributed-gpu-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = [aws_subnet.private.id, aws_subnet.private_2.id]
  instance_types  = [var.node_instance_type]
  capacity_type   = "ON_DEMAND"

  scaling_config {
    desired_size = var.desired_nodes
    max_size     = var.max_nodes
    min_size     = var.min_nodes
  }

  labels = {
    workload = "distributed-inference"
    accelerator = "nvidia-a100"
  }

  taint {
    key    = "nvidia.com/gpu"
    value  = "true"
    effect = "NO_SCHEDULE"
  }
}

resource "aws_autoscaling_policy" "distributed_scale_up" {
  name                   = "distributed-scale-up"
  autoscaling_group_name = aws_autoscaling_group.distributed.name
  adjustment_type        = "ChangeInCapacity"
  scaling_adjustment     = 2
  cooldown               = 300
}

resource "aws_autoscaling_policy" "distributed_scale_down" {
  name                   = "distributed-scale-down"
  autoscaling_group_name = aws_autoscaling_group.distributed.name
  adjustment_type        = "ChangeInCapacity"
  scaling_adjustment     = -1
  cooldown               = 600
}

resource "aws_autoscaling_group" "distributed" {
  name                = "${var.cluster_name}-asg"
  max_size            = var.max_nodes
  min_size            = var.min_nodes
  desired_capacity    = var.desired_nodes
  vpc_zone_identifier = [aws_subnet.private.id, aws_subnet.private_2.id]
  launch_template {
    id      = aws_launch_template.distributed.id
    version = "$Latest"
  }
}

resource "aws_launch_template" "distributed" {
  name_prefix   = "distributed-gpu-"
  image_id      = data.aws_ami.eks_optimized.id
  instance_type = var.node_instance_type

  user_data = base64encode(data.template_file.gpu_bootstrap.rendered)

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "distributed-gpu-node"
      Component = "distributed-inference"
    }
  }
}

output "cluster_endpoint" {
  value = aws_eks_cluster.distributed.endpoint
}

output "cluster_name" {
  value = aws_eks_cluster.distributed.name
}
