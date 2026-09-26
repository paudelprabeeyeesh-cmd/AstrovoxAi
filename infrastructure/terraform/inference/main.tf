terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  default = "us-west-2"
}

variable "inference_cluster_name" {
  default = "astrovox-inference"
}

variable "gpu_instance_type" {
  default = "p4d.24xlarge"
}

variable "min_capacity" {
  default = 1
}

variable "max_capacity" {
  default = 8
}

resource "aws_eks_cluster" "inference" {
  name     = var.inference_cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.29"

  vpc_config {
    subnet_ids = [aws_subnet.private.id, aws_subnet.private_2.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
  ]

  tags = {
    Component = "inference-engine"
  }
}

resource "aws_eks_node_group" "gpu" {
  cluster_name    = aws_eks_cluster.inference.name
  node_group_name = "gpu-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = [aws_subnet.private.id, aws_subnet.private_2.id]
  instance_types  = [var.gpu_instance_type]
  capacity_type   = "ON_DEMAND"

  scaling_config {
    desired_size = var.min_capacity
    max_size     = var.max_capacity
    min_size     = 1
  }

  labels = {
    workload = "inference"
    accelerator = "nvidia-a100"
  }

  taint {
    key    = "nvidia.com/gpu"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]

  tags = {
    Component = "inference-engine"
  }
}

resource "aws_launch_template" "inference" {
  name_prefix   = "inference-gpu-"
  image_id      = data.aws_ami.eks_optimized.id
  instance_type = var.gpu_instance_type

  user_data = base64encode(data.template_file.gpu_bootstrap.rendered)

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "inference-gpu-node"
    }
  }

  tags = {
    Component = "inference-engine"
  }
}

data "template_file" "gpu_bootstrap" {
  template = file("${path.module}/user-data/gpu-bootstrap.sh")
}

resource "aws_autoscaling_policy" "inference_scale_up" {
  name                   = "inference-scale-up"
  autoscaling_group_name = aws_autoscaling_group.inference.name
  adjustment_type        = "ChangeInCapacity"
  scaling_adjustment     = 2
  cooldown               = 300
}

resource "aws_autoscaling_policy" "inference_scale_down" {
  name                   = "inference-scale-down"
  autoscaling_group_name = aws_autoscaling_group.inference.name
  adjustment_type        = "ChangeInCapacity"
  scaling_adjustment     = -1
  cooldown               = 600
}

resource "aws_autoscaling_group" "inference" {
  name                = "astrovox-inference-asg"
  max_size            = var.max_capacity
  min_size            = var.min_capacity
  desired_capacity    = var.min_capacity
  vpc_zone_identifier = [aws_subnet.private.id, aws_subnet.private_2.id]
  launch_template {
    id      = aws_launch_template.inference.id
    version = "$Latest"
  }

  tag {
    key                 = "Component"
    value               = "inference-engine"
    propagate_at_launch = true
  }
}
