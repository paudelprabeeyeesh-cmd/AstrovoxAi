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
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs"
  type        = list(string)
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS nodes"
  type        = list(string)
  default     = ["t3.large", "t3.xlarge"]
}

variable "node_min_count" {
  description = "Minimum node count"
  type        = number
  default     = 2
}

variable "node_max_count" {
  description = "Maximum node count"
  type        = number
  default     = 10
}

variable "node_desired_count" {
  description = "Desired node count"
  type        = number
  default     = 3
}

variable "enable_cluster_autoscaler" {
  description = "Enable cluster autoscaler"
  type        = bool
  default     = true
}

variable "enable_external_dns" {
  description = "Enable external DNS"
  type        = bool
  default     = true
}

variable "enable_aws_load_balancer_controller" {
  description = "Enable AWS Load Balancer Controller"
  type        = bool
  default     = true
}

variable "enable_cert_manager" {
  description = "Enable cert-manager"
  type        = bool
  default     = true
}

variable "enable_external_secrets" {
  description = "Enable External Secrets Operator"
  type        = bool
  default     = true
}

variable "enable_argocd" {
  description = "Enable ArgoCD"
  type        = bool
  default     = true
}

variable "enable_argo_rollouts" {
  description = "Enable Argo Rollouts"
  type        = bool
  default     = true
}

data "aws_iam_policy_document" "eks_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "eks_cluster_role" {
  name               = "${var.cluster_name}-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_assume_role.json
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "eks_service_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
}

data "aws_iam_policy_document" "node_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "eks_node_role" {
  name               = "${var.cluster_name}-node-role"
  assume_role_policy = data.aws_iam_policy_document.node_assume_role.json
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = var.kubernetes_version
  role_arn = aws_iam_role.eks_cluster_role.arn

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  enabled_cluster_log_types = ["api", "audit", "app", "controllerManager"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
  ]

  tags = {
    Name = var.cluster_name
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = var.private_subnet_ids
  instance_types  = var.node_instance_types

  scaling_config {
    desired_size = var.node_desired_count
    max_size     = var.node_max_count
    min_size     = var.node_min_count
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.ecr_readonly,
  ]

  tags = {
    Name = "${var.cluster_name}-nodes"
  }
}

resource "aws_security_group" "eks_cluster_sg" {
  name_prefix = "${var.cluster_name}-cluster-sg"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-cluster-sg"
  }
}

resource "aws_security_group_rule" "eks_cluster_ingress" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  security_group_id        = aws_security_group.eks_cluster_sg.id
}

resource "helm_release" "external_dns" {
  count          = var.enable_external_dns ? 1 : 0
  name           = "external-dns"
  repository     = "https://kubernetes-sigs.github.io/external-dns/"
  chart          = "external-dns"
  namespace      = "kube-system"
  version        = "1.13.0"
  force_update   = true
  recreate_pods  = false
  wait           = true
  timeout        = 300

  set {
    name  = "provider"
    value = "aws"
  }

  set {
    name  = "aws.zoneType"
    value = "public"
  }

  set {
    name  = "policy"
    value = "sync"
  }

  set {
    name  = "registry"
    value = "txt"
  }

  set {
    name  = "txtOwnerId"
    value = var.cluster_name
  }

  set {
    name  = "domainFilters[0]"
    value = "astrovox.ai"
  }

  depends_on = [aws_eks_cluster.main]
}

resource "helm_release" "aws_load_balancer_controller" {
  count          = var.enable_aws_load_balancer_controller ? 1 : 0
  name           = "aws-load-balancer-controller"
  repository     = "https://aws.github.io/eks-charts"
  chart          = "aws-load-balancer-controller"
  namespace      = "kube-system"
  version        = "1.6.0"
  force_update   = true
  recreate_pods  = false
  wait           = true
  timeout        = 300

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "false"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  depends_on = [aws_eks_cluster.main]
}

resource "helm_release" "cert_manager" {
  count          = var.enable_cert_manager ? 1 : 0
  name           = "cert-manager"
  repository     = "https://charts.jetstack.io"
  chart          = "cert-manager"
  namespace      = "cert-manager"
  version        = "v1.13.0"
  force_update   = true
  recreate_pods  = false
  wait           = true
  timeout        = 300

  set {
    name  = "installCRDs"
    value = "true"
  }

  depends_on = [aws_eks_cluster.main]
}

resource "helm_release" "external_secrets" {
  count          = var.enable_external_secrets ? 1 : 0
  name           = "external-secrets"
  repository     = "https://charts.external-secrets.io"
  chart          = "external-secrets"
  namespace      = "external-secrets"
  version        = "0.9.0"
  force_update   = true
  recreate_pods  = false
  wait           = true
  timeout        = 300

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = aws_iam_role.external_secrets_role.arn
  }

  depends_on = [aws_eks_cluster.main]
}

resource "aws_iam_role" "external_secrets_role" {
  name = "${var.cluster_name}-external-secrets-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/oidc.eks.${var.aws_region}.amazonaws.com/id/${aws_eks_cluster.main.identity[0].oidc[0].issuer}"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:external-secrets:external-secrets"
            "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "external_secrets_policy" {
  role       = aws_iam_role.external_secrets_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

resource "helm_release" "argocd" {
  count          = var.enable_argocd ? 1 : 0
  name           = "argocd"
  repository     = "https://argoproj.github.io/argo-helm"
  chart          = "argo-cd"
  namespace      = "argocd"
  version        = "5.4.0"
  force_update   = true
  recreate_pods  = false
  wait           = true
  timeout        = 300

  set {
    name  = "server.service.type"
    value = "LoadBalancer"
  }

  set {
    name  = "server.extraArgs[0]"
    value = "--insecure"
  }

  depends_on = [aws_eks_cluster.main]
}

resource "helm_release" "argo_rollouts" {
  count          = var.enable_argo_rollouts ? 1 : 0
  name           = "argo-rollouts"
  repository     = "https://argoproj.github.io/argo-helm"
  chart          = "argo-rollouts"
  namespace      = "argo-rollouts"
  version        = "2.29.0"
  force_update   = true
  recreate_pods  = false
  wait           = true
  timeout        = 300

  set {
    name  = "dashboard.service.type"
    value = "LoadBalancer"
  }

  depends_on = [aws_eks_cluster.main]
}

resource "helm_release" "cluster_autoscaler" {
  count          = var.enable_cluster_autoscaler ? 1 : 0
  name           = "cluster-autoscaler"
  repository     = "https://kubernetes.github.io/autoscaler"
  chart          = "cluster-autoscaler"
  namespace      = "kube-system"
  version        = "9.29.0"
  force_update   = true
  recreate_pods  = false
  wait           = true
  timeout        = 300

  set {
    name  = "autoDiscovery.clusterName"
    value = var.cluster_name
  }

  set {
    name  = "awsRegion"
    value = var.aws_region
  }

  set {
    name  = "rbac.serviceAccount.create"
    value = "false"
  }

  set {
    name  = "rbac.serviceAccount.name"
    value = "cluster-autoscaler"
  }

  depends_on = [aws_eks_cluster.main]
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

output "node_security_group_id" {
  description = "Node security group ID"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}
