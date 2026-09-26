output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.inference.endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.inference.name
}

output "kubeconfig" {
  description = "Kubeconfig for inference cluster"
  value       = aws_eks_cluster.inference.endpoint
  sensitive   = true
}

output "autoscaling_group_name" {
  description = "ASG name for inference GPU nodes"
  value       = aws_autoscaling_group.inference.name
}

output "node_instance_type" {
  description = "EC2 instance type for inference nodes"
  value       = var.gpu_instance_type
}
