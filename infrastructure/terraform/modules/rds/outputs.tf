output "endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "replica_endpoints" {
  value = aws_db_instance.postgres_replica[*].endpoint
}

output "password" {
  value = random_password.db_password.result
  sensitive = true
}
